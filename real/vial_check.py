#!/usr/bin/env python3
"""Vial placement check on the pre-trial clean frame (E_premortem row 13, B 5.5), used by real/trial_runner.py.

Targets: the row's layout (config/layouts.json, vial poses in E after the sim's 10 warm-up steps) drawn as solid
silhouettes of the tube (body, conical tip) and its cap, projected with the C920 intrinsics on the undistorted
frame (config/c920_intrinsics.json, K and dist; the frame is undistorted to the same K) from the measured camera
pose (results/poses/<tag>.json from calib/pose.py: R_E_cv, C_E_m, frame E).
Observed: inside a band around the targets, pixels that differ from the block's clean reference (no vials) or are
cap-blue, closed, split into blobs, each blob filled to its convex hull and given to the target it overlaps most.
Pass [P]: every vial's IoU >= 0.7 (B 5.5), the union IoU >= 0.7, and each visible cap overlaps its projected cap
(catches a vial laid the wrong way round; a reversed tube alone keeps a high IoU).
Tube geometry: the real Kashi tube when results/rig/measurements.jsonl has all of MEAS_KEYS (anchored at the tip
+ 17 mm, B 5.5; axis at the body radius above the mat top, the cap end raised by the cap's larger radius); otherwise
the sim tube (Vial.usda) with a WARNING naming the missing measurements.
"""
import json
from pathlib import Path

import cv2
import numpy as np

GTC = Path(__file__).resolve().parents[1]
# Vial.usda (course repo @ ce807d9), read with pxr on Nov 3: local z = tube axis, origin 17 mm from the conical tip.
# Mesh_002 (body): tip z -0.0170 r 4.5 mm, cone to z 0.0039 r 15.7 mm, cylinder to z 0.0980; Mesh_001 (cap):
# z 0.0850-0.0995, r 17.0 mm.
SIM_PROFILE = {"body": [(-0.017, 0.0045), (0.0039, 0.0157), (0.098, 0.0157)], "cap": [(0.085, 0.017), (0.0995, 0.017)]}
MEAS_KEYS = ("kashi_tube_od_mm", "kashi_tube_length_mm", "kashi_cap_od_mm", "kashi_cap_length_mm")
MAT_TOP_Z = 0.035                                   # sim mat top in E (B 1.2); a recorded h_mat_mm overrides it
BASE_BOTTOM_Z = 0.0301                              # sim robot plate bottom (B 1.2), the h_mat datum (B 4.2)
TH = dict(iou_min=0.7, diff_k=6.0, diff_floor=20, band_px=30, close_px=7, min_blob_px=60, cap_frac_min=0.5,
          cap_min_px=30, blue_hsv_lo=[95, 80, 50], blue_hsv_hi=[130, 255, 255],
          centroid_px=4.0,   # [P] except iou_min (B 5.5 [P]); centroid_px: v2 addendum 8c (Nov 6; image noise SD <= 0.21 px)
          method="iou",      # "iou": B 5.5 as registered; "shift": proposed for addendum entry 2 (Nov 8), see score_shift
          search_px=20, cover_min=0.85,   # "shift" only: shift search radius; covered share of the aligned silhouette
          across_mm=7.5, along_mm=7.5)    # "shift" only: tube offset on the mat across / along its axis; entry 1's 8c
                                          # examples (5 mm sideways passes, 10 mm along fails) both hold at 7.5 / 7.5


def quat_to_R(q):
    w, x, y, z = np.asarray(q, float) / np.linalg.norm(q)
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
                     [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
                     [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)]])


def latest_measurements(path):
    vals = {}
    if Path(path).exists():
        for line in open(path):
            vals.update(json.loads(line))
    return vals


def vial_model(measurements=GTC / "results" / "rig" / "measurements.jsonl"):
    """(profile, source, mat_top_z, warnings)."""
    m, warn = latest_measurements(measurements), []
    mat_top = MAT_TOP_Z
    if "h_mat_mm" in m:
        mat_top = BASE_BOTTOM_Z + float(m["h_mat_mm"]) / 1000
    missing = [k for k in MEAS_KEYS if k not in m]
    if missing:
        warn.append(f"WARNING: no measured Kashi tube ({', '.join(missing)} missing in results/rig/measurements.jsonl); "
                    "using the sim tube from Vial.usda (body OD 31.4 mm, cap OD 34.0 mm, length 116.5 mm)")
        return SIM_PROFILE, "sim Vial.usda", mat_top, warn
    od, L, cod, cl = (float(m[k]) / 1000 for k in MEAS_KEYS)
    tip, cone_end = -0.017, -0.017 + (SIM_PROFILE["body"][1][0] - SIM_PROFILE["body"][0][0])
    warn.append("note: the conical tip's length and tip radius are the sim's (not measured)")
    prof = {"body": [(tip, SIM_PROFILE["body"][0][1]), (cone_end, od / 2), (tip + L - cl, od / 2)],
            "cap": [(tip + L - cl, cod / 2), (tip + L, cod / 2)]}
    return prof, "measured Kashi tube", mat_top, warn


def vial_poses(layout, profile, source, mat_top):
    """{vial: (R_E_vial, origin_E)}. Sim tube: the layout's settled pose. Measured tube: same origin (tip + 17 mm)
    and heading, axis at the body radius above the mat top, raised toward the cap by the cap's larger radius."""
    out = {}
    for name, v in sorted(layout["vials"].items()):
        R, p = quat_to_R(v["quat_wxyz"]), np.array(v["pos_env"], float)
        if source != "sim Vial.usda":
            ax = R[:, 2]
            h = np.arctan2(ax[1], ax[0])
            r_b, r_c = profile["body"][1][1], profile["cap"][0][1]
            span = profile["cap"][0][0] - profile["body"][1][0]
            t = np.arctan2(r_c - r_b, span)
            z = np.array([np.cos(h) * np.cos(t), np.sin(h) * np.cos(t), np.sin(t)])
            x = np.cross([0, 0, 1.0], z)
            x /= np.linalg.norm(x)
            R = np.column_stack([x, np.cross(z, x), z])
            p = np.array([p[0], p[1], mat_top + r_b + 0.017 * np.sin(t)])
        out[name] = (R, p)
    return out


def project(P_E, R_E_cv, C_E, K):
    X = (np.asarray(P_E) - C_E) @ R_E_cv                 # rows: points in the camera (CV) frame
    if (X[:, 2] <= 0.01).any():
        raise ValueError("a vial point is behind the camera")
    uv = X[:, :2] / X[:, 2:3]
    return uv @ K[:2, :2].T + K[:2, 2]


def silhouette(segments, R_v, o_v, R_E_cv, C_E, K, shape, n=48):
    m = np.zeros(shape, np.uint8)
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    for (z0, r0), (z1, r1) in zip(segments, segments[1:]):
        ring = lambda z, r: np.column_stack([r * np.cos(a), r * np.sin(a), np.full(n, z)])
        local = np.vstack([ring(z0, r0), ring(z1, r1)])
        uv = project(local @ R_v.T + o_v, R_E_cv, C_E, K)
        cv2.fillConvexPoly(m, cv2.convexHull(np.round(uv * 16).astype(np.int32)), 1, cv2.LINE_8, 4)
    return m.astype(bool)


def targets(layout, profile, source, mat_top, R_E_cv, C_E, K, shape):
    out = {}
    for name, (R, p) in vial_poses(layout, profile, source, mat_top).items():
        cap = silhouette(profile["cap"], R, p, R_E_cv, C_E, K, shape)
        out[name] = {"mask": silhouette(profile["body"], R, p, R_E_cv, C_E, K, shape) | cap, "cap": cap}
    return out


def observe(cur, ref, sd, band, th):
    """Observed vial blobs (convex-hull filled) inside the band, and the cap-blue mask."""
    diff = np.abs(cur.astype(np.int16) - ref.astype(np.int16)).max(axis=2)
    changed = diff > np.maximum(th["diff_k"] * sd, th["diff_floor"])
    blue = cv2.inRange(cv2.cvtColor(cur, cv2.COLOR_RGB2HSV), np.array(th["blue_hsv_lo"], np.uint8),
                       np.array(th["blue_hsv_hi"], np.uint8)) > 0
    k = th["close_px"]
    obs = cv2.morphologyEx(((changed | blue) & band).astype(np.uint8), cv2.MORPH_CLOSE, np.ones((k, k), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(obs, 8)
    blobs = []
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] < th["min_blob_px"]:
            continue
        hull = np.zeros(obs.shape, np.uint8)
        cv2.fillConvexPoly(hull, cv2.convexHull(np.argwhere(lab == i)[:, ::-1].astype(np.int32)), 1)
        blobs.append(hull.astype(bool))
    return blobs, blue & band


def score(tg, blobs, blue, th):
    names = list(tg)
    union_t = np.logical_or.reduce([t["mask"] for t in tg.values()])
    got = {k: np.zeros(union_t.shape, bool) for k in names}
    extra = []
    for b in blobs:
        ov = [int((b & tg[k]["mask"]).sum()) for k in names]
        if max(ov) == 0:
            extra.append(int(b.sum()))
        else:
            got[names[int(np.argmax(ov))]] |= b
    per = {}
    for k in names:
        t, o = tg[k]["mask"], got[k]
        iou = float((t & o).sum() / max((t | o).sum(), 1))
        bl = blue & o
        capf = float((bl & cv2.dilate(tg[k]["cap"].astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)).sum()
                     / bl.sum()) if bl.sum() >= th["cap_min_px"] else None
        ys, xs = np.nonzero(t)
        oy, ox = np.nonzero(o)
        per[k] = {"iou": round(iou, 3), "cap_frac": None if capf is None else round(capf, 3),
                  "target_px": int(t.sum()), "observed_px": int(o.sum()),
                  "centroid_err_px": round(float(np.hypot(ox.mean() - xs.mean(), oy.mean() - ys.mean())), 1) if len(ox) else None,
                  "pass": bool(iou >= th["iou_min"] and (capf is None or capf >= th["cap_frac_min"])
                               and len(ox) > 0 and np.hypot(ox.mean() - xs.mean(), oy.mean() - ys.mean()) <= th["centroid_px"])}
    union_o = np.logical_or.reduce(blobs) if blobs else np.zeros(union_t.shape, bool)
    u_iou = float((union_t & union_o).sum() / max((union_t | union_o).sum(), 1))
    ok = all(v["pass"] for v in per.values()) and u_iou >= th["iou_min"]
    return {"pass": ok, "union_iou": round(u_iou, 3), "iou_min_seen": min(v["iou"] for v in per.values()),
            "vials": per, "extra_blobs_px": extra}


def observe_split(cur, ref, sd, tg, band, th):
    """Changed and cap-blue pixels inside the band, each given to the NEAREST target silhouette (so two tubes that
    touch in the image are split where they meet, instead of one merged patch going to one target)."""
    diff = np.abs(cur.astype(np.int16) - ref.astype(np.int16)).max(axis=2)
    changed = diff > np.maximum(th["diff_k"] * sd, th["diff_floor"])
    blue = cv2.inRange(cv2.cvtColor(cur, cv2.COLOR_RGB2HSV), np.array(th["blue_hsv_lo"], np.uint8),
                       np.array(th["blue_hsv_hi"], np.uint8)) > 0
    k = th["close_px"]
    obs = cv2.morphologyEx(((changed | blue) & band).astype(np.uint8), cv2.MORPH_CLOSE, np.ones((k, k), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(obs, 8)
    keep = np.isin(lab, [i for i in range(1, n) if st[i, cv2.CC_STAT_AREA] >= th["min_blob_px"]])
    names = list(tg)
    dist = np.stack([cv2.distanceTransform((~tg[k]["mask"]).astype(np.uint8), cv2.DIST_L2, 5) for k in names])
    near = np.argmin(dist, axis=0)
    return {k: keep & (near == i) for i, k in enumerate(names)}, blue & band


def score_shift(tg, got, blue, th, px_to_mm=None, axis_xy=None):
    """Per tube: the image shift (within search_px) that best lines the projected silhouette up with that tube's
    pixels (maximum overlap = maximum IoU, as |silhouette| and |pixels| are fixed), the share of the aligned
    silhouette that is covered, and the cap test on the aligned cap. Pass: shift <= centroid_px (8c's 4.0 px, now
    measured as an alignment instead of a centroid, which shading next to the tube pulls off), cover >= cover_min,
    cap as before. IoU is reported, not used: the changed patch of one tube is 20-40 % larger than its silhouette.
    With px_to_mm and axis_xy (the tube's axis direction on the mat, E x/y) the shift is judged in mm on the mat,
    across (<= across_mm) and along (<= along_mm) the tube, instead of in px."""
    S = int(th["search_px"])
    per = {}
    for k in tg:
        t, o, cap = tg[k]["mask"], got[k], tg[k]["cap"]
        ys, xs = np.nonzero(t)
        y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        tpl = t[y0:y1, x0:x1].astype(np.float32)
        H, W = o.shape
        pad = cv2.copyMakeBorder(o.astype(np.float32), S, S, S, S, cv2.BORDER_CONSTANT, value=0)
        win = pad[y0:y1 + 2 * S, x0:x1 + 2 * S]
        cc = cv2.matchTemplate(win, tpl, cv2.TM_CCORR)             # cc[dy+S, dx+S] = overlap at shift (dx, dy)
        dy, dx = np.unravel_index(int(np.argmax(cc)), cc.shape)
        best, dx, dy = float(cc[dy, dx]), int(dx) - S, int(dy) - S
        if best > 0:                                               # sub-pixel by a parabola in x and y
            def par(a, b, c):
                d = a - 2 * b + c
                return 0.5 * (a - c) / d if d < 0 else 0.0
            cy, cx = dy + S, dx + S
            fx = par(cc[cy, cx - 1], cc[cy, cx], cc[cy, cx + 1]) if 0 < cx < cc.shape[1] - 1 else 0.0
            fy = par(cc[cy - 1, cx], cc[cy, cx], cc[cy + 1, cx]) if 0 < cy < cc.shape[0] - 1 else 0.0
            sx, sy = dx + fx, dy + fy
        else:
            sx, sy = float("nan"), float("nan")
        tsum, osum = float(t.sum()), float(o.sum())
        cover = best / tsum if tsum else 0.0
        iou_al = best / max(tsum + osum - best, 1.0)
        M = np.float32([[1, 0, dx], [0, 1, dy]])
        cap_s = cv2.warpAffine(cap.astype(np.uint8), M, (W, H), flags=cv2.INTER_NEAREST).astype(bool)
        bl = blue & o
        capf = float((bl & cv2.dilate(cap_s.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)).sum() / bl.sum()) \
            if bl.sum() >= th["cap_min_px"] else None
        shift = float(np.hypot(sx, sy))
        rec = {"shift_px": [round(sx, 2), round(sy, 2)], "shift_abs_px": round(shift, 2), "cover": round(cover, 3),
               "iou_aligned": round(iou_al, 3), "iou": round(float((t & o).sum() / max((t | o).sum(), 1)), 3),
               "cap_frac": None if capf is None else round(capf, 3), "target_px": int(tsum), "observed_px": int(osum)}
        pos_ok = np.isfinite(shift) and shift <= th["centroid_px"]
        if px_to_mm is not None and np.isfinite(shift):
            e = px_to_mm(k, sx, sy)
            rec["shift_E_mm"] = [round(float(v), 1) for v in e]
            if axis_xy is not None:
                ax = np.asarray(axis_xy[k], float) / np.linalg.norm(axis_xy[k])
                along, across = float(e @ ax), float(e @ np.array([-ax[1], ax[0]]))
                rec["along_mm"], rec["across_mm"] = round(along, 1), round(across, 1)
                pos_ok = abs(across) <= th["across_mm"] and abs(along) <= th["along_mm"]
        rec["pass"] = bool(pos_ok and cover >= th["cover_min"] and (capf is None or capf >= th["cap_frac_min"]))
        per[k] = rec
    return {"pass": all(v["pass"] for v in per.values()), "method": "shift", "vials": per,
            "shift_max_px": max(v["shift_abs_px"] for v in per.values()), "cover_min_seen": min(v["cover"] for v in per.values()),
            "across_max_mm": max((abs(v["across_mm"]) for v in per.values() if "across_mm" in v), default=None),
            "iou_min_seen": min(v["iou"] for v in per.values()), "extra_blobs_px": []}


def load_camera(pose_path, intr_path):
    """(R_E_cv, C_E, K, dist) from a calib/pose.py record in frame E and the intrinsics JSON."""
    rec = json.loads(Path(pose_path).read_text())
    if "R_E_cv" not in rec:
        raise ValueError(f"{pose_path} is not in frame E (no config/board_in_E.json when it was measured)")
    j = json.loads(Path(intr_path).read_text())
    return np.array(rec["R_E_cv"]), np.array(rec["C_E_m"]), np.array(j["K"], float), np.array(j["dist"], float).ravel()


def undistort(img, K, dist):
    if not np.any(dist):
        return img
    mx, my = cv2.initUndistortRectifyMap(K, dist, None, K, img.shape[1::-1], cv2.CV_32FC1)
    return cv2.remap(img, mx, my, cv2.INTER_LINEAR)


def check(cur, ref, sd, layout, cam, model, th=TH):
    """cur/ref RGB and sd as captured (distorted); cam = (R_E_cv, C_E, K, dist); model = vial_model()."""
    R_E_cv, C_E, K, dist = cam
    profile, source, mat_top, warn = model
    cur_u, ref_u = undistort(cur, K, dist), undistort(ref, K, dist)
    sd_u = undistort(sd.astype(np.float32), K, dist)
    tg = targets(layout, profile, source, mat_top, R_E_cv, C_E, K, cur.shape[:2])
    union_t = np.logical_or.reduce([t["mask"] for t in tg.values()]).astype(np.uint8)
    b = th["band_px"]
    band = cv2.dilate(union_t, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * b + 1, 2 * b + 1))).astype(bool)
    if th.get("method", "iou") == "shift":
        got, blue = observe_split(cur_u, ref_u, sd_u, tg, band, th)
        poses = vial_poses(layout, profile, source, mat_top)

        def px_to_mm(name, sx, sy):                    # the shift at the tube's centre, on the plane of its axis
            R, p = poses[name]
            ys, xs = np.nonzero(tg[name]["mask"])
            uv = np.array([[xs.mean(), ys.mean()], [xs.mean() + sx, ys.mean() + sy]])
            d = np.column_stack([(uv[:, 0] - K[0, 2]) / K[0, 0], (uv[:, 1] - K[1, 2]) / K[1, 1], np.ones(2)]) @ R_E_cv.T
            P = C_E + ((p[2] - C_E[2]) / d[:, 2])[:, None] * d
            return 1000 * (P[1, :2] - P[0, :2])
        res = score_shift(tg, got, blue, th, px_to_mm, {k: poses[k][0][:2, 2] for k in poses})
        blobs = list(got.values())
    else:
        blobs, blue = observe(cur_u, ref_u, sd_u, band, th)
        res = score(tg, blobs, blue, th)
    res.update({"layout": layout.get("layout_id"), "tube": source, "warnings": warn, "thresholds": th})
    vis = cur_u.copy()
    for t in tg.values():
        for m, col in ((t["mask"], (0, 255, 0)), (t["cap"], (255, 255, 0))):
            cs, _ = cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            cv2.drawContours(vis, cs, -1, col, 1)
    for bl in blobs:
        cs, _ = cv2.findContours(bl.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        cv2.drawContours(vis, cs, -1, (255, 0, 255), 1)
    return res, vis


def find_layout(layout_id, path=GTC / "config" / "layouts.json"):
    for L in json.loads(Path(path).read_text())["layouts"]:
        if L.get("layout_id") == layout_id:
            return L
    raise KeyError(f"layout {layout_id} is not in {path}")
