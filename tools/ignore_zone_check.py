#!/usr/bin/env python3
"""Do the reference's ignore zones cover every layout's tubes in the front view? (Nov 6, N04-001 preflight: the tip of
the tube nearest the rack in L01 showed outside the tube zone.)

    .venv/bin/python -I tools/ignore_zone_check.py [--ref N04-R0_R0] [--margin 12] [--write-mask]
Projection without the camera pose (the R0 pose is measured after the R0 block): the board homography of the plate-N
fit frame (camera untouched since) and the mat frame from the reference's mat edges, with points above the mat lifted
along the ray to the lens (tools/jig_fit.py geometry). Tubes: each layout's pose (config/layouts.json) with the measured
Kashi tube (real/vial_check.py vial_model / vial_poses). Check: the rack's top face drawn at its height must sit on the
yellow rack. --write-mask: add the union of all layouts' tubes, grown by --margin px, to the reference's ignore mask
(the old mask is kept as ignore_mask_before_<utc>.png; meta.json records the change). --write-tube-masks: one label image per
layout (tubes_<Lxx>.png) for the trial runner's tubes-present check while the R0 tube check is deferred.
--pose TAG (results/poses/TAG.json, frame E): project the tubes and the rack with that measured camera pose instead
(any camera pose, e.g. s1 or a camera block's pose; the board-and-mat model above holds only at R0). The silhouettes
are those of real/vial_check.py (undistorted image), mapped into the captured image the references are taken in.
"""
import argparse
import datetime as dt
import json
import shutil
import sys
from pathlib import Path

import cv2
import numpy as np

GTC = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(GTC / "calib"), str(GTC / "tools"), str(GTC / "real")]

import capture  # noqa: E402
import charuco as C  # noqa: E402
import jig_fit as J  # noqa: E402
import vial_check as V  # noqa: E402


def mat_model(ref_rgb, h_rack=7.85, board_t=0.5, mat_len=45.72, board_frame="media/still/fit_N.png"):
    det = C.Detector().detect(capture.load_rgb(GTC / board_frame))
    Hb, Hinv = J.board_h(det)
    bc = det["obj"][:, :2].mean(axis=0) * 100.0
    H = J.LENS_ABOVE_FOAM - J.MAT_T
    N_uv = (J.LENS_U_FROM_FLOOR_FRONT - J.MAT_FRONT_FROM_FLOOR_FRONT, mat_len + (J.MAT_LEFT_FROM_LEFT_WALL - J.LENS_FROM_LEFT_WALL))
    gray = cv2.cvtColor(ref_rgb, cv2.COLOR_RGB2GRAY)
    fi, ri = J.mat_front_points(gray), J.mat_right_points(gray)
    N = None
    for _ in range(3):
        def ground(p, z):
            pl = J.to_plane(Hinv, p)
            return pl if N is None else J.lift(pl, N, H, board_t, z)
        origin, n, d = J.mat_frame(ground(fi, 0.0), ground(ri, 0.0))
        ua = n if np.dot(bc - origin, n) > 0 else -n
        N = origin + ua * N_uv[0] + d * N_uv[1]

    def to_img(u_cm, v_cm, z_cm):
        """Mat point (cm from the front edge, cm from the right edge, cm above the mat top) -> image px."""
        p = origin[None, :] + np.outer(u_cm, ua) + np.outer(v_cm, d)
        pp = N + (p - N) * (H - board_t) / (H - np.asarray(z_cm, float)[:, None])
        q = np.c_[pp, np.ones(len(pp))] @ Hb.T
        return q[:, :2] / q[:, 2:3]
    return to_img


def pose_model(pose_tag, shape):
    """(tube_masks(layout) -> {vial: captured-image mask}, rack top face in the captured image) from a measured pose."""
    R, C_, K, dist = V.load_camera(GTC / "results" / "poses" / f"{pose_tag}.json", GTC / "config" / "c920_intrinsics.json")
    h, w = shape
    raw = np.stack(np.meshgrid(np.arange(w), np.arange(h)), -1).reshape(-1, 1, 2).astype(np.float32)
    und = cv2.undistortPoints(raw, K, dist, P=K).reshape(h, w, 2)                 # captured px -> undistorted px
    ux, uy = np.clip(np.round(und[..., 0]).astype(int), 0, w - 1), np.clip(np.round(und[..., 1]).astype(int), 0, h - 1)
    inside = (und[..., 0] >= 0) & (und[..., 0] < w) & (und[..., 1] >= 0) & (und[..., 1] < h)
    prof, src, mat_top, _ = V.vial_model()

    def masks(layout):
        tg = V.targets(layout, prof, src, mat_top, R, C_, K, shape)
        return {k: t["mask"][uy, ux] & inside for k, t in tg.items()}, src
    rv, _ = cv2.Rodrigues(R.T)
    O, top = (0.18, 0.08), mat_top + 0.0785
    sq = np.array([[O[0], O[1], top], [O[0] + .12, O[1], top], [O[0] + .12, O[1] + .12, top], [O[0], O[1] + .12, top]])
    rack = cv2.projectPoints(sq, rv, -R.T @ C_, K, dist)[0].reshape(-1, 2)
    return masks, rack


def tube_masks(layout, to_img, mat_env, shape, n=36):
    prof, src, mat_top, _ = V.vial_model()
    out = {}
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    for name, (R, p) in V.vial_poses(layout, prof, src, mat_top).items():
        m = np.zeros(shape, np.uint8)
        for seg in (prof["body"], prof["cap"]):
            for (z0, r0), (z1, r1) in zip(seg, seg[1:]):
                local = np.vstack([np.column_stack([r * np.cos(a), r * np.sin(a), np.full(n, z)]) for z, r in ((z0, r0), (z1, r1))])
                E = local @ R.T + p
                uv = to_img((E[:, 0] - mat_env["front_x"]) * 100, (E[:, 1] - mat_env["right_y"]) * 100, (E[:, 2] - mat_top) * 100)
                cv2.fillConvexPoly(m, cv2.convexHull(np.round(uv).astype(np.int32)), 1)
        out[name] = m.astype(bool)
    return out, src


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", default="N04-R0_R0")
    ap.add_argument("--margin", type=int, default=12)
    ap.add_argument("--pose", help="measured camera pose tag (results/poses/<tag>.json); required away from R0")
    ap.add_argument("--write-mask", action="store_true")
    ap.add_argument("--write-tube-masks", action="store_true", help="save tubes_<Lxx>.png (labels 1-3 = vial_1-3) in the "
                    "reference folder, for the runner's pose-free tubes-present check at R0")
    a = ap.parse_args(argv)
    rdir = GTC / "media" / "real" / "refs" / a.ref
    ref = capture.load_rgb(rdir / "ref_front_median.png")
    ignore = cv2.imread(str(rdir / "ignore_mask.png"), cv2.IMREAD_GRAYSCALE) > 0
    lay = json.loads((GTC / "config" / "layouts.json").read_text())
    vis = ref.copy()
    vis[ignore] = (vis[ignore] * 0.45).astype(np.uint8)
    if a.pose:                                  # any camera pose: tubes and the rack's sim top face from the pose
        pose_masks, sq = pose_model(a.pose, ignore.shape)
    else:
        to_img = mat_model(ref)
        # sanity: the rack's top face (target N, 12 x 12 cm, 7.85 cm above the mat)
        tu, tl = J.TARGET["N"]
        vr = 45.72 - tl
        sq = to_img(np.array([tu, tu + 12, tu + 12, tu]), np.array([vr, vr, vr + 12, vr + 12]), np.full(4, 7.85))
    cv2.polylines(vis, [np.round(sq).astype(np.int32)], True, (0, 255, 255), 1)
    yel = J.yellow_mask(ref)
    union = np.zeros(ignore.shape, bool)
    rows = []
    for L in lay["layouts"]:
        masks, src = pose_masks(L) if a.pose else tube_masks(L, to_img, lay["mat_env"], ignore.shape)
        if a.write_tube_masks:
            lab = np.zeros(ignore.shape, np.uint8)
            for i, name in enumerate(sorted(masks), 1):
                lab[masks[name]] = i
            cv2.imwrite(str(rdir / f"tubes_{L['layout_id']}.png"), lab)
        for name, m in masks.items():
            union |= m
            out = m & ~ignore
            dist = cv2.distanceTransform((~ignore).astype(np.uint8), cv2.DIST_L2, 5)
            rows.append((L["layout_id"], name, int(m.sum()), int(out.sum()), float(dist[out].max()) if out.any() else 0.0))
    vis[union & ~ignore] = (255, 0, 255)
    vis[union & ignore] = (vis[union & ignore] * 0.5 + np.array([255, 0, 255]) * 0.5).astype(np.uint8)
    capture.save_rgb(GTC / "media" / "real" / "shakedown" / f"ignore_zone_check_{a.ref}.png", vis)
    print(f"tube model: {src}; rack top face drawn in yellow (should sit on the rack's top face)")
    print("layout vial    tube_px outside_px  max_px_outside_zone")
    for r in rows:
        if r[3]:
            print(f"{r[0]}    {r[1]}  {r[2]:7d} {r[3]:10d}  {r[4]:6.1f}")
    print(f"{sum(1 for r in rows if r[3])} of {len(rows)} tube placements reach outside the tube zone")
    if a.write_mask:
        grow = cv2.dilate(union.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * a.margin + 1,) * 2)) > 0
        stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        shutil.copy2(rdir / "ignore_mask.png", rdir / f"ignore_mask_before_{stamp}.png")
        new = ignore | grow
        cv2.imwrite(str(rdir / "ignore_mask.png"), new.astype(np.uint8) * 255)
        meta = json.loads((rdir / "meta.json").read_text())
        meta.setdefault("ignore_updates", []).append({"utc": stamp, "added": "all layouts' tubes (measured Kashi tube, "
                                                      f"layouts L00-L09) grown by {a.margin} px", "ignore_frac_before":
                                                      float(ignore.mean()), "ignore_frac_after": float(new.mean())})
        meta["ignore_frac"] = float(new.mean())
        (rdir / "meta.json").write_text(json.dumps(meta, indent=1, default=str))
        print(f"ignore mask updated: {100 * ignore.mean():.1f} % -> {100 * new.mean():.1f} % of the image "
              f"(old mask kept as ignore_mask_before_{stamp}.png)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
