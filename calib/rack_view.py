#!/usr/bin/env python3
"""Live rack placement view (Nov 6): the rack's front face and right face against the L-jig fit-test targets, in mm,
and which way to push, until both are within --tol mm (the fit test's rule is 2 mm).

    .venv/bin/python -I calib/rack_view.py --target N          # N, X3 or Y3; q quits
    .venv/bin/python -I calib/rack_view.py --target N --ref N04-R0_R0
Same measure as tools/jig_fit.py (mat edges and rack outline on the board plane, lifted with the rack height and the
lens height), with the board homography taken from the plate-N fit frame (media/still/fit_N.png): valid only while the
camera is untouched since that frame (check: calib/mat_view.py or the runner's drift check). Mean of the last 5 frames.
Front face = the rack face toward the robot, as cm from the mat's front edge. Right face = the rack face toward the right
wall, as cm from the mat's left edge. Also the rack's turn against the mat's front edge, from its far rim.

--ref (Nov 7): the trial runner's own rack check against that block reference (centroid 2 px, turn 1 deg; shown OK at
0.6 and 0.5 of those), drawn on the image: the reference's rack outline in green, the rack now in magenta (both the
runner's yellow mask), and an arrow showing the push, with the push in mm along the mat (away from / toward the robot,
toward the right / camera wall). The arrow follows the rack's top face (ECC translation of the image over the reference's
rack region above row 430), not the mask centroid: the rack runs off the image's bottom edge, so the centroid moves only
about half as far as the rack in image y (Nov 7: centroid 1.0 px with the top face 2 px off, and the clean view failing
on the rack's edges). The mm come from that shift brought down to the mat at the rack's top-face height with the mat
frame of the reference image (camera and mat unmoved since it, which the runner's mat and drift checks verify): a guide,
about +-10 %. Also the runner's clean-view and light checks against the reference (no drift warp). WITHIN TARGET = the
rack check OK (at 0.6 / 0.5), top face within --face-px, clean view and light pass. Text sits in a panel below the image,
wrapped. On quit: results/rig/rack_view_last.json and the last view as rack_view_last.png.
"""
import argparse
import collections
import datetime as dt
import json
import sys
from pathlib import Path

import cv2
import numpy as np

GTC = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(GTC / "calib"), str(GTC / "tools")]

import capture  # noqa: E402
import charuco as C  # noqa: E402
import jig_fit as J  # noqa: E402
import live  # noqa: E402

GREEN, MAGENTA, CYAN, YELLOW = (0, 255, 0), (255, 0, 255), (0, 255, 255), (255, 255, 0)


def mat_geometry(gray, Hinv, board_centre, board_t, H, N_uv):
    """Mat frame from the mat edges seen in this frame -> (ground(p_img, z) on the board plane in cm, origin, n, d)."""
    front_img, right_img = J.mat_front_points(gray), J.mat_right_points(gray)
    N = None

    def ground(p_img, z):
        pl = J.to_plane(Hinv, p_img)
        return pl if N is None else J.lift(pl, N, H, board_t, z)
    for _ in range(3):
        origin, n, d = J.mat_frame(ground(front_img, 0.0), ground(right_img, 0.0))
        u_axis = n if np.dot(board_centre - origin, n) > 0 else -n
        N = origin + u_axis * N_uv[0] + d * N_uv[1]
    return ground, origin, n, d


def measure(rgb, Hinv, board_centre, h_rack, board_t, mat_len, H, N_uv):
    """jig_fit.analyse with a fixed board homography, plus the rim's turn (deg) against the mat's front edge."""
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    m = J.yellow_mask(rgb)
    if m.sum() < 5000:
        return None
    face_img, rim_img = J.rack_right_outline(rgb, m), J.rack_far_rim(rgb, m)
    ground, origin, n, d = mat_geometry(gray, Hinv, board_centre, board_t, H, N_uv)
    rim = J.mat_uv(ground(rim_img, h_rack), origin, n, d, board_centre)
    sel = face_img[:, 1] >= np.quantile(face_img[:, 1], 0.6)
    low = J.mat_uv(ground(J.inliers(face_img[sel]), 0.0), origin, n, d, board_centre)
    c, dr = J.fit_line(J.inliers(rim))                         # rim runs along u (toward the back wall)
    turn = float(np.degrees(np.arctan2(dr[1], dr[0])))
    turn = (turn + 90) % 180 - 90
    return {"front_u_cm": float(np.median(low[:, 0])), "right_from_left_cm": float(mat_len - np.median(rim[:, 1])),
            "rim_turn_deg": turn}


def push_mm(geo, c_now, c_ref, z_cm):
    """Move that brings the rack's centre from c_now to c_ref (image px), in mm along the mat:
    (+ away from the robot / - toward it, + toward the camera wall / - toward the right wall)."""
    ground, origin, n, d, bc = geo
    uv = J.mat_uv(ground(np.array([c_now, c_ref], float), z_cm), origin, n, d, bc)
    du, dv = 10.0 * (uv[1] - uv[0])
    return float(du), float(dv)


def push_words(du, dv, min_mm=0.2):
    parts = []
    if abs(du) >= min_mm:
        parts.append(f"{abs(du):.1f} mm {'AWAY FROM' if du > 0 else 'TOWARD'} the robot")
    if abs(dv) >= min_mm:
        parts.append(f"{abs(dv):.1f} mm toward the {'CAMERA' if dv > 0 else 'RIGHT'} wall")
    return " and ".join(parts) if parts else "less than 0.2 mm"


def blur_gray(rgb):
    return cv2.GaussianBlur(cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32), (0, 0), 1.5)


def face_shift(g0, rgb, roi):
    """Translation (px) of the rack's top-face region now against the reference, or None."""
    W = np.eye(2, 3, dtype=np.float32)
    try:
        _, W = cv2.findTransformECC(g0, blur_gray(rgb), W, cv2.MOTION_TRANSLATION,
                                    (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 100, 1e-5), roi, 5)
    except cv2.error:
        return None
    return W[:, 2].astype(float)


def outline(m):
    cnt, _ = cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    return cnt


def draw_text(img, text, org, color, scale=0.5):
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), 3, cv2.LINE_AA)
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale, color, 1, cv2.LINE_AA)


def draw_push(img, c_now, c_ref, ok, label):
    """Arrow from the rack's centre now toward the reference centre (lengthened to be seen), with the push label."""
    p0 = tuple(int(round(x)) for x in c_now)
    cv2.circle(img, tuple(int(round(x)) for x in c_ref), 4, GREEN, -1)
    cv2.circle(img, p0, 4, MAGENTA, -1)
    if ok:
        draw_text(img, "OK", (p0[0] + 8, p0[1] - 8), GREEN, 0.7)
        return
    v = np.asarray(c_ref, float) - np.asarray(c_now, float)
    L = float(np.hypot(*v))
    if L < 1e-6:
        return
    p1 = np.asarray(c_now, float) + v / L * min(150.0, 40.0 + 12.0 * L)
    p1 = tuple(int(round(x)) for x in p1)
    cv2.arrowedLine(img, p0, p1, (0, 0, 0), 6, cv2.LINE_AA, tipLength=0.3)
    cv2.arrowedLine(img, p0, p1, CYAN, 3, cv2.LINE_AA, tipLength=0.3)
    h, w = img.shape[:2]
    mid = (np.asarray(p0, float) + np.asarray(p1, float)) / 2
    side = np.array([v[1], -v[0]]) / L                             # perpendicular, on the upper side of the arrow
    if side[1] > 0:
        side = -side
    org = mid + side * 22 - np.array([45.0, 0.0])
    draw_text(img, label, (int(min(max(org[0], 4), w - 130)), int(min(max(org[1], 16), h - 6))), CYAN, 0.6)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", default="N", choices=sorted(J.TARGET))
    ap.add_argument("--source", default="camera:front")
    ap.add_argument("--tol", type=float, default=1.0, help="mm shown as OK (the fit-test rule is 2 mm)")
    ap.add_argument("--h-rack", type=float, default=7.85)
    ap.add_argument("--board-t", type=float, default=0.5)
    ap.add_argument("--mat-len", type=float, default=45.72)
    ap.add_argument("--board-frame", default="media/still/fit_N.png")
    ap.add_argument("--ref", help="also show the runner's rack check against this block reference (2 px / 1 deg)")
    ap.add_argument("--face-px", type=float, default=1.0, help="top-face shift shown as OK (px), with --ref")
    ap.add_argument("--headless-frames", type=int)
    a = ap.parse_args(argv)
    det = C.Detector().detect(capture.load_rgb(GTC / a.board_frame))
    if det is None or len(det["ids"]) < 12:
        raise SystemExit(f"STOP: board not seen in {a.board_frame}")
    _, Hinv = J.board_h(det)
    board_centre = det["obj"][:, :2].mean(axis=0) * 100.0
    H = J.LENS_ABOVE_FOAM - J.MAT_T
    N_uv = (J.LENS_U_FROM_FLOOR_FRONT - J.MAT_FRONT_FROM_FLOOR_FRONT,
            a.mat_len + (J.MAT_LEFT_FROM_LEFT_WALL - J.LENS_FROM_LEFT_WALL))
    tu, tl = J.TARGET[a.target]
    src = capture.open_source(a.source)
    hist = collections.deque(maxlen=5)
    rhist = collections.deque(maxlen=5)
    ref_m = ref_cnt = geo = None
    if a.ref:
        sys.path.insert(0, str(GTC / "real"))
        import trial_runner as T
        ref_rgb = capture.load_rgb(GTC / "media" / "real" / "refs" / a.ref / "ref_front_median.png")
        ref_m = T.yellow_mask(ref_rgb, T.CHECKS["yellow_hsv_lo"], T.CHECKS["yellow_hsv_hi"])
        ref_cnt = outline(ref_m)
        rdir = GTC / "media" / "real" / "refs" / a.ref
        ref_sd = np.load(rdir / "ref_front_sd.npy").astype(np.float32)
        ref_ign = cv2.imread(str(rdir / "ignore_mask.png"), cv2.IMREAD_GRAYSCALE) > 0
        face_roi = cv2.dilate(ref_m.astype(np.uint8), np.ones((11, 11), np.uint8))
        face_roi[430:] = 0                                      # top face and holes; away from the image's bottom edge
        face_g0 = blur_gray(ref_rgb)
        face_anchor = np.argwhere(face_roi > 0).mean(axis=0)[::-1]
        thist = collections.deque(maxlen=5)
        try:
            geo = (*mat_geometry(cv2.cvtColor(ref_rgb, cv2.COLOR_RGB2GRAY), Hinv, board_centre, a.board_t, H, N_uv),
                   board_centre)
        except Exception as e:  # noqa: BLE001  (no mm then; the px check still runs)
            print(f"note: no mat frame from the reference ({e}); the push is shown in px only")
    st = {"rec": None, "lines": [], "view": None}

    def step():
        f = src.read()
        try:
            r = measure(f, Hinv, board_centre, a.h_rack, a.board_t, a.mat_len, H, N_uv)
        except Exception:  # noqa: BLE001  (hands over the rack or the mat edges)
            r = None
        if r:
            hist.append(r)
        out = f.copy()
        if ref_m is None:
            cv2.drawContours(out, outline(J.yellow_mask(f)), -1, MAGENTA, 1)
        else:
            cm = T.yellow_mask(f, T.CHECKS["yellow_hsv_lo"], T.CHECKS["yellow_hsv_hi"])
            cv2.drawContours(out, ref_cnt, -1, GREEN, 3)
            cv2.drawContours(out, outline(cm), -1, MAGENTA, 1)          # lined up: magenta inside the green line
        lines, ok, ref_rec = [], False, {}
        if len(hist) >= 3 and r is not None:
            fu = 10 * (np.mean([h["front_u_cm"] for h in hist]) - tu)
            rl = 10 * (np.mean([h["right_from_left_cm"] for h in hist]) - tl)
            turn = float(np.mean([h["rim_turn_deg"] for h in hist]))
            ok = abs(fu) <= a.tol and abs(rl) <= a.tol
            mm_lines = [(f"{'OK ' if abs(fu) <= a.tol else '   '}front face {fu:+.1f} mm"
                         + ("" if abs(fu) <= a.tol else f": push the rack {'TOWARD' if fu > 0 else 'AWAY FROM'} the robot"),
                         GREEN if abs(fu) <= a.tol else YELLOW),
                        (f"{'OK ' if abs(rl) <= a.tol else '   '}right face {rl:+.1f} mm"
                         + ("" if abs(rl) <= a.tol else f": push the rack toward the {'RIGHT' if rl < 0 else 'LEFT (camera)'} wall"),
                         GREEN if abs(rl) <= a.tol else YELLOW),
                        f"rim turn {turn:+.2f} deg against the mat's front edge (fit test: about the same at every plate)"]
            lines = mm_lines
            if ref_m is not None:                               # information only: the reference check decides
                lines = [f"front face {fu:+.1f} mm, right face {rl:+.1f} mm, rim turn {turn:+.2f} deg"]
        else:
            fu = rl = turn = None
            lines = ["mm vs the target: rack or mat edges not seen (hands in the way?)"]
        if ref_m is not None:
            mm_part = lines
            rp = T.rack_pose(ref_m, cm, T.CHECKS)
            if rp.get("rot_deg") is not None:
                c0, c1 = (np.argwhere(m_).mean(axis=0)[::-1] for m_ in (ref_m, cm))
                rhist.append((c1[0] - c0[0], c1[1] - c0[1], rp["rot_deg"], c0, c1))
            else:
                rhist.clear()
            fs = face_shift(face_g0, f, face_roi)
            if fs is not None:
                thist.append(fs)
            else:
                thist.clear()
            cvw, light, _ = T.clean_view(ref_rgb, ref_sd, ref_ign, f, T.CHECKS, None)
            if len(rhist) >= 3 and len(thist) >= 3:
                dx, dy, rot = (float(np.mean([h[i] for h in rhist])) for i in range(3))
                err = float(np.hypot(dx, dy))
                tx, ty = np.mean(thist, axis=0)
                terr = float(np.hypot(tx, ty))
                ok_px, ok_rot = err <= T.CHECKS["rack_px"] * 0.6, abs(rot) <= T.CHECKS["rack_deg"] * 0.5
                ok_face, ok_clean, ok_light = terr <= a.face_px, bool(cvw["pass"]), bool(light["pass"])
                ok = ok_px and ok_rot and ok_face and ok_clean and ok_light
                c_ref, c_now = face_anchor, face_anchor + np.array([tx, ty])
                du = dv = None
                if geo is not None:
                    du, dv = push_mm(geo, c_now, c_ref, a.h_rack)
                    words = push_words(du, dv)
                    label = f"push {np.hypot(du, dv):.1f} mm"
                else:
                    words, label = f"image x {-tx:+.1f} px, y {-ty:+.1f} px", f"push {terr:.1f} px"
                draw_push(out, c_now, c_ref, ok_face, label)
                lines = [(f"{'OK ' if ok_face else '   '}top face vs reference {a.ref}: x {tx:+.1f}, y {ty:+.1f} px "
                          f"(OK at {a.face_px:.1f})", GREEN if ok_face else YELLOW)]
                if not ok_face:
                    lines.append((f"PUSH about {words} (cyan arrow)", CYAN))
                big = cvw["blobs"][0]["area"] if cvw["blobs"] else 0
                lines += [(f"{'OK ' if ok_px and ok_rot else '   '}runner rack check: shift {err:.1f} px (OK at "
                           f"{T.CHECKS['rack_px'] * 0.6:.1f}; trial check {T.CHECKS['rack_px']:.1f}), turn {rot:+.2f} deg "
                           f"(OK at {T.CHECKS['rack_deg'] * 0.5:.1f}; trial check {T.CHECKS['rack_deg']:.1f})"
                           + ("" if ok_rot else ": turn it slightly and watch the turn go toward 0"),
                           GREEN if ok_px and ok_rot else YELLOW),
                          (f"{'OK ' if ok_clean else '   '}clean view: " + ("no changed blob" if ok_clean else
                           f"{len(cvw['blobs'])} changed blob(s), largest {big} px (trial check: none >= "
                           f"{T.CHECKS['clean_min_area_px']} px)"), GREEN if ok_clean else YELLOW),
                          (f"{'OK ' if ok_light else '   '}light {light['ratio']:.3f} (trial check 1 +- "
                           f"{T.CHECKS['light_tol']:.2f})", GREEN if ok_light else YELLOW),
                          "green = reference outline, magenta = now: line them up",
                          f"plate {a.target}, information only (the reference checks above decide):"] + mm_part
                ref_rec = {"ref": a.ref, "shift_px": round(err, 2), "image_dx_px": round(dx, 2), "image_dy_px": round(dy, 2),
                           "turn_deg": round(rot, 3), "top_face_dx_px": round(float(tx), 2), "top_face_dy_px": round(float(ty), 2),
                           "push_away_from_robot_mm": None if du is None else round(du, 2),
                           "push_toward_camera_wall_mm": None if dv is None else round(dv, 2),
                           "clean_view_pass": ok_clean, "clean_blobs": cvw["blobs"][:5], "light_ratio": round(light["ratio"], 4),
                           "ref_ok": bool(ok)}
            else:
                ok = False
                lines = ["vs reference: rack not seen (hands in the way?)"] + mm_part
        if ok:
            lines.append(("WITHIN TARGET: hands out, door on", GREEN))
        if fu is not None or ref_rec:
            st["rec"] = {"utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "target": a.target,
                         "front_face_mm": None if fu is None else round(float(fu), 2),
                         "right_face_mm": None if rl is None else round(float(rl), 2),
                         "rim_turn_deg": None if turn is None else round(turn, 3),
                         "within_tol": bool(ok), "tol_mm": a.tol, "board_frame": a.board_frame, **ref_rec}
        st["lines"] = [x[0] if isinstance(x, tuple) else x for x in lines]
        view = np.vstack([out, live.text_panel(lines + ["q quit"], out.shape[1])])
        st["view"] = view
        return view, st["lines"]

    try:
        live.run(step, {"q": lambda: "quit"}, f"rack view, target {a.target}", headless=a.headless_frames is not None,
                 max_frames=a.headless_frames)
    finally:
        src.close()
        print("\n".join(st["lines"]))
        if st["rec"]:
            (GTC / "results" / "rig" / "rack_view_last.json").write_text(json.dumps(st["rec"], indent=1))
        if st["view"] is not None:
            capture.save_rgb(GTC / "results" / "rig" / "rack_view_last.png", st["view"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
