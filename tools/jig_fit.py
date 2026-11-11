#!/usr/bin/env python3
"""L-jig camera fit test (E row 11; prereg v2 D15): where the rack stands on the mat after each plate (N, X3, Y3),
from the front C920 at R0, before the R0 trials and without the camera pose (G8).

    .venv/bin/python -I tools/jig_fit.py --h-rack CM --board-t CM [--mat-len CM] [--frames N=... X3=... Y3=...]
Scale: the ChArUco board lies flat on the mat, untouched for all three frames; its homography gives metric
coordinates on the board's top plane (30 mm squares as printed). Mat frame (cm): u from the mat's front edge (robot
side) toward the back wall, v from the mat's right edge toward the left edge.
- Mat front edge: the mat/floor boundary at the image's right side (rows below the robot); mat right edge: the short
  stretch visible between the board's right end and the wrist camera, taken perpendicular to the front edge.
- Rack front face (target u 11.25 N/Y3, 14.25 X3): the right edge of the yellow region near the mat. At N the lens
  is within about 0.5 mm of that face's plane, so the face is seen edge-on and every point of its outline lies on the
  mat line u = face; at X3 the face's bottom edge is visible. The median of the lowest 40 % of the outline is used.
- Rack right face (target 14.85 N/X3, 11.85 Y3 from the mat's LEFT edge): its bottom edge is hidden behind the
  rack, so its top edge (the far rim of the top face, h-rack above the mat) is brought down with the lens height
  and ground point from the R0 tape readings (40.3 cm above the foam floor, 28.2 cm from the floor's front edge,
  5.2 cm from the left wall; build-spec box layout for the mat and walls). Distance from the left edge =
  mat length - v.
Heights: points seen on the mat (z = 0) or at height z are moved along their ray from the board's top plane (board
thickness above the mat) to their own height. Lens distortion is not removed (no C920 intrinsics before C3; the
same frames are re-measured after C3), so the result is good to about 2 mm, enough to catch a misplaced stop.
Writes results/rig/jig_fit_<utc>.json.
"""
import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import cv2
import numpy as np

GTC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GTC / "calib"))
import capture  # noqa: E402
import charuco as C  # noqa: E402

TARGET = {"N": (11.25, 14.85), "X3": (14.25, 14.85), "Y3": (11.25, 11.85)}   # front face u, right face from LEFT edge
MAT_T = 0.6                        # EVA mat thickness (build spec: the mat's 6 mm edge)
LENS_ABOVE_FOAM = 40.3             # R0 tape (about), Nov 5
LENS_U_FROM_FLOOR_FRONT = 28.2     # R0 tape (about)
MAT_FRONT_FROM_FLOOR_FRONT = 10.1 + 6.87   # plate front face (build-spec layout) + the mat's ruler distance
LENS_FROM_LEFT_WALL = 5.2          # R0 tape (about)
MAT_LEFT_FROM_LEFT_WALL = 53.4 - 22.9 - 15.23   # plate left face - left wall inner face (layout) - ruler distance


def board_h(det):
    """Board plane (cm) -> image homography and its inverse."""
    H, _ = cv2.findHomography(det["obj"][:, :2] * 100.0, det["img"])
    return H, np.linalg.inv(H)


def to_plane(Hinv, pts):
    p = cv2.perspectiveTransform(np.asarray(pts, np.float64).reshape(-1, 1, 2), Hinv)
    return p.reshape(-1, 2)


def crossing(profile, lo_to_hi=True):
    """Subpixel index where a 1-D profile crosses half-way between its ends' levels (first crossing)."""
    p = np.asarray(profile, float)
    a, b = np.median(p[:5]), np.median(p[-5:])
    mid = (a + b) / 2
    s = p - mid if lo_to_hi else mid - p
    idx = np.where((s[:-1] < 0) & (s[1:] >= 0))[0]
    if not len(idx):
        return None
    i = idx[0]
    return i + (-s[i]) / (s[i + 1] - s[i])


def mat_front_points(gray, rows=range(300, 476, 2), x0=430, x1=620):
    pts = []
    for y in rows:
        c = crossing(gray[y, x0:x1].astype(float), lo_to_hi=True)       # dark mat -> bright floor
        if c is not None:
            pts.append((x0 + c, y))
    return np.array(pts)


def mat_right_points(gray, cols=range(430, 496, 2), y0=55, y1=125):
    pts = []
    for x in cols:
        c = crossing(gray[y0:y1, x].astype(float), lo_to_hi=False)      # bright floor -> dark mat, going down
        if c is not None:
            pts.append((x, y0 + c))
    return np.array(pts)


def yellow_mask(rgb):
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    m = ((hsv[..., 0] >= 15) & (hsv[..., 0] <= 40) & (hsv[..., 1] >= 90) & (hsv[..., 2] >= 90)).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m)
    k = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    return (lab == k).astype(np.uint8)


def rack_right_outline(rgb, m):
    """Per row, the subpixel right end of the yellow region (yellow -> dark mat), rows from its top to 475."""
    sat = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)[..., 1].astype(float)
    ys = np.where(m.any(axis=1))[0]
    pts = []
    for y in range(int(ys.min()) + 6, min(int(ys.max()), 475) + 1):
        xs = np.where(m[y])[0]
        xr = int(xs.max())
        seg = sat[y, max(xr - 12, 0):xr + 12]
        c = crossing(seg, lo_to_hi=False)
        if c is not None:
            pts.append((max(xr - 12, 0) + c, y))
    return np.array(pts)


def rack_far_rim(rgb, m):
    """Per column, the subpixel top end of the yellow region along the far rim of the top face: from the top face's
    far-left corner (the highest point of the region) to 10 px before its right end; stray points dropped."""
    sat = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)[..., 1].astype(float)
    cols = np.where(m.any(axis=0))[0]
    top = {int(x): int(np.where(m[:, x])[0].min()) for x in cols}
    x_tl = min(top, key=lambda x: (top[x], x))
    pts = []
    for x in range(x_tl + 5, int(cols.max()) - 10):
        yt = top[x]
        seg = sat[max(yt - 12, 0):yt + 12, x]
        c = crossing(seg, lo_to_hi=True)
        if c is not None:
            pts.append((x, max(yt - 12, 0) + c))
    return inliers(np.array(pts))


def inliers(p, tol=1.5):
    """Points within tol px of a straight line through them (two passes)."""
    keep = np.ones(len(p), bool)
    for _ in range(2):
        c, d = fit_line(p[keep])
        res = np.abs((p - c) @ np.array([-d[1], d[0]]))
        keep = res <= max(tol, 2.5 * np.median(res[keep]))
    return p[keep]


def fit_line(p):
    """Total least squares line: point, unit direction."""
    c = p.mean(axis=0)
    _, _, vt = np.linalg.svd(p - c)
    return c, vt[0]


def mat_frame(front_pl, right_pl):
    """Origin = front-right corner, u axis along the front edge's normal toward the board side, v along the front edge
    toward the mat's left (away from the right edge points)."""
    c, d = fit_line(front_pl)
    n = np.array([-d[1], d[0]])
    r = right_pl.mean(axis=0)
    if np.dot(r - c, d) > 0:      # v axis points from the right edge toward the left edge
        d = -d
    v_r = np.dot(r - c, d)
    origin = c + d * v_r          # right edge position along the front edge (perpendicular right edge)
    return origin, n, d


def mat_uv(p, origin, n, d, toward):
    u_axis = n if np.dot(toward - origin, n) > 0 else -n
    q = np.asarray(p) - origin
    return np.c_[q @ u_axis, q @ d]


def lift(p_plane, N, H, d_board, z):
    """A point seen at p_plane on the board's top plane (d_board above the mat) that really is at height z."""
    return N + (p_plane - N) * (H - z) / (H - d_board)


def analyse(rgb, h_rack, board_t, mat_len, H, N_uv):
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    det = C.Detector().detect(rgb)
    if det is None or len(det["ids"]) < 12:
        raise SystemExit("STOP: board not seen")
    Hb, Hinv = board_h(det)
    front_img, right_img = mat_front_points(gray), mat_right_points(gray)
    m = yellow_mask(rgb)
    face_img, rim_img = rack_right_outline(rgb, m), rack_far_rim(rgb, m)
    board_centre = det["obj"][:, :2].mean(axis=0) * 100.0
    N = None
    for _ in range(3):            # the ground point depends on the mat frame, which depends on the ground point
        def ground(p_img, z):
            pl = to_plane(Hinv, p_img)
            return pl if N is None else lift(pl, N, H, board_t, z)
        fr, rr = ground(front_img, 0.0), ground(right_img, 0.0)
        origin, n, d = mat_frame(fr, rr)
        toward = board_centre
        u_axis = n if np.dot(toward - origin, n) > 0 else -n
        N = origin + u_axis * N_uv[0] + d * N_uv[1]
    face = mat_uv(ground(face_img, 0.0), origin, n, d, toward)
    rim = mat_uv(ground(rim_img, h_rack), origin, n, d, toward)
    sel = face_img[:, 1] >= np.quantile(face_img[:, 1], 0.6)
    low_img = inliers(face_img[sel])
    low = mat_uv(ground(low_img, 0.0), origin, n, d, toward)
    fr_res = mat_uv(fr, origin, n, d, toward)[:, 0]
    return {"board_corners": int(len(det["ids"])), "front_edge_points": int(len(front_img)),
            "front_edge_residual_cm_sd": float(np.std(fr_res)), "right_edge_points": int(len(right_img)),
            "face_rows": int(len(low_img)), "rim_cols": int(len(rim_img)),
            "front_face_u_cm": float(np.median(low[:, 0])), "front_face_u_spread_cm": float(np.ptp(low[:, 0])),
            "right_face_v_from_right_cm": float(np.median(rim[:, 1])),
            "right_face_from_left_cm": float(mat_len - np.median(rim[:, 1])),
            "right_face_v_spread_cm": float(np.ptp(rim[:, 1]))}


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--h-rack", type=float, required=True, help="rack top above the mat (cm)")
    ap.add_argument("--board-t", type=float, required=True, help="board thickness incl. print (cm)")
    ap.add_argument("--mat-len", type=float, default=45.72, help="mat length along its front edge (cm)")
    ap.add_argument("--frames", nargs="+", default=["N=media/still/fit_N.png", "X3=media/still/fit_X3.png",
                                                   "Y3=media/still/fit_Y3.png"])
    a = ap.parse_args(argv)
    H = LENS_ABOVE_FOAM - MAT_T
    N_uv = (LENS_U_FROM_FLOOR_FRONT - MAT_FRONT_FROM_FLOOR_FRONT,
            a.mat_len + (MAT_LEFT_FROM_LEFT_WALL - LENS_FROM_LEFT_WALL))
    rec = {"utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "h_rack_cm": a.h_rack,
           "board_t_cm": a.board_t, "mat_len_cm": a.mat_len, "lens_above_mat_cm": H, "ground_point_uv_cm": N_uv,
           "plates": {}}
    for spec in a.frames:
        name, path = spec.split("=", 1)
        r = analyse(capture.load_rgb(GTC / path), a.h_rack, a.board_t, a.mat_len, H, N_uv)
        tu, tl = TARGET[name]
        r.update(frame=path, target_front_u_cm=tu, target_right_from_left_cm=tl,
                 d_front_mm=round(10 * (r["front_face_u_cm"] - tu), 1),
                 d_right_mm=round(10 * (r["right_face_from_left_cm"] - tl), 1))
        rec["plates"][name] = r
        print(f"{name:3s} front face {r['front_face_u_cm']:6.2f} cm (target {tu:5.2f}, {r['d_front_mm']:+5.1f} mm) | "
              f"right face {r['right_face_from_left_cm']:6.2f} cm from the left edge (target {tl:5.2f}, "
              f"{r['d_right_mm']:+5.1f} mm) | corners {r['board_corners']}, spreads {r['front_face_u_spread_cm']:.2f} / "
              f"{r['right_face_v_spread_cm']:.2f} cm")
    out = GTC / "results" / "rig" / f"jig_fit_{rec['utc'].replace(':', '')}.json"
    out.write_text(json.dumps(rec, indent=1))
    print(f"-> {out.relative_to(GTC)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
