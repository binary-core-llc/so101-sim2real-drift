#!/usr/bin/env python3
"""Sled datums from the front C920's own C3 views: where the tongue's end face and the key sit in the ChArUco grid
(B 4.2 d_x, d_y and the end-face yaw), as a check on config/board_in_E.json.

    .venv/bin/python -I tools/sled_from_views.py [--views media/calib/intrinsics/A/*.png ...] [--out DIR]
                                                 [--square-mm 29.97] [--t-mm 4.85]
Each view: corners and pose with config/c920_intrinsics.json (board frame K: origin at the grid's outer corner on
the title side, x along the 8-square side away from the tongue, y along the 6-square side, z into the board). The
tongue region is resampled onto a board-parallel plane at 10 px/mm and the edges are found along profiles (smoothed
gradient peak, sub-pixel by a parabola), then fitted with lines (3-sigma clipped).
Parallax: the tongue is the same foam piece as the carrier, so its top is the board's top plane (bare foam, the
print's ~0.1 mm is ignored). A face whose outward normal points toward the camera centre shows its BOTTOM edge as the
dark/white boundary, t-mm below the top; that edge is measured on the plane z = t. A face pointing away shows its
top edge, measured on z = 0. Decided per view and per face (end face and key tip: normal -x; key sides: -y and +y).
Per view, in board mm: d_x on each side of the key and at the grid corner (by = 0), end-face yaw, key width,
protrusion and centre (bx_k, by_k). In board_in_E terms (calib/charuco.py board_in_E): yaw = atan(d(d_x)/d(by)),
negative when the title side (by = 0) is farther; d_x_mm = d_x at by = 0; d_y_mm = cos(yaw) by_k - sin(yaw) bx_k.
Writes <out>/sled_from_views.json and an annotated crop per kept view.
"""
import argparse
import glob
import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "calib"))  # python -I skips the script dir

import charuco as C  # noqa: E402

GTC = Path(__file__).resolve().parents[1]
PPM = 10.0                       # rectified px per mm
BOX = (-122.0, -60.0, 30.0, 150.0)   # bx0, bx1, by0, by1 (mm): tongue end, key and both tongue sides
SMOOTH_PX = 4.0                  # Gaussian sigma along each profile (rectified px)
MIN_CONTRAST = 60                # grey levels between the mat and the foam


def rectify(gray, rv, tv, K, dist, z_mm):
    x0, x1, y0, y1 = BOX
    xs, ys = np.arange(x0, x1, 1 / PPM), np.arange(y0, y1, 1 / PPM)
    X, Y = np.meshgrid(xs, ys)
    pts = np.stack([X.ravel(), Y.ravel(), np.full(X.size, z_mm)], 1) / 1000
    uv, _ = cv2.projectPoints(pts, rv, tv, K, dist)
    uv = uv.reshape(Y.shape + (2,)).astype(np.float32)
    out = cv2.remap(gray, uv[..., 0], uv[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=-1)
    inside = (uv[..., 0] > 2) & (uv[..., 0] < gray.shape[1] - 3) & (uv[..., 1] > 2) & (uv[..., 1] < gray.shape[0] - 3)
    return out.astype(np.float64), inside


def window_ok(ok, r0, r1, c0, c1):
    """The slice ok[r0:r1, c0:c1] lies inside the resampled box and inside the image."""
    H, W = ok.shape
    return 0 <= r0 < r1 <= H and 0 <= c0 < c1 <= W and bool(ok[r0:r1, c0:c1].all())


def to_px(bx, by):
    return (bx - BOX[0]) * PPM, (by - BOX[2]) * PPM


def to_mm(px, py):
    return px / PPM + BOX[0], py / PPM + BOX[2]


def edge_on_profile(prof, rising=True):
    """Sub-pixel index of the outermost strong step: the first dark->bright step from the dark (low-index) end when
    rising, the last bright->dark step when falling (a visible face strip sits between the mat and the top, so the
    mat-side step is its bottom edge). Steps under half the strongest one are ignored; None if the contrast is weak."""
    if prof.size < 20:
        return None
    g = cv2.GaussianBlur(np.ascontiguousarray(prof, dtype=np.float64).reshape(1, -1), (0, 0), SMOOTH_PX).ravel()
    d = np.gradient(g) * (1 if rising else -1)
    lo, hi = np.percentile(g, 10), np.percentile(g, 90)
    if hi - lo < MIN_CONTRAST or d[3:-3].max() <= 0:
        return None
    peaks = [i for i in range(3, len(d) - 3) if d[i] >= d[i - 1] and d[i] > d[i + 1] and d[i] >= 0.5 * d[3:-3].max()]
    if not peaks:
        return None
    i = peaks[0] if rising else peaks[-1]
    den = d[i - 1] - 2 * d[i] + d[i + 1]
    return i + (0.5 * (d[i - 1] - d[i + 1]) / den if den < 0 else 0.0)


def fit_line(a, b):
    """b = c0 + c1 a, 3-sigma clipped; returns (c0, c1, rms, n)."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    keep = np.ones(len(a), bool)
    for _ in range(4):
        c1, c0 = np.polyfit(a[keep], b[keep], 1)
        r = b - (c0 + c1 * a)
        s = max(np.std(r[keep]), 1e-3)
        new = np.abs(r) < 3 * s
        if new.sum() == keep.sum():
            break
        keep = new
    return c0, c1, float(np.std(r[keep])), int(keep.sum())


def coarse(img0, inside):
    """Tongue mask (Otsu) -> end face bx, key rows, tongue side rows (mm), from the z = 0 resampling."""
    u8 = np.clip(img0, 0, 255).astype(np.uint8)
    _, m = cv2.threshold(u8, 0, 1, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((9, 9), np.uint8)) & inside
    n, lab, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8))
    if n < 2:
        return None
    j = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    m = lab == j
    col = int(to_px(-80.0, 0)[0])                  # a column across the tongue's body
    rows = np.where(m[:, col])[0]
    if len(rows) < 600:
        return None
    side_lo, side_hi = to_mm(0, rows[0])[1], to_mm(0, rows[-1])[1]
    left = np.array([np.argmax(r) if r.any() else -1 for r in m])   # first bright px per row
    rr = np.arange(int(to_px(0, side_lo + 3)[1]), int(to_px(0, side_hi - 3)[1]))
    lx = to_mm(left[rr], 0)[0]
    face = np.median(lx)
    key = rr[lx < face - 2.5]
    if len(key) < 200:
        return None
    return {"side_lo": side_lo, "side_hi": side_hi, "face": face, "tip": float(np.median(to_mm(left[key], 0)[0])),
            "key_lo": to_mm(0, key[0])[1], "key_hi": to_mm(0, key[-1])[1]}


def footprint(c, x, y, grow=0.0):
    """Inside the foam slab's outline (tongue, key, carrier) seen from above, grown by `grow` mm."""
    tongue = (x >= c["face"] - grow) & (y >= c["side_lo"] - grow) & (y <= c["side_hi"] + grow)
    key = (x >= c["tip"] - grow) & (x <= c["face"] + grow) & (y >= c["key_lo"] - grow) & (y <= c["key_hi"] + grow)
    carrier = (x >= -25.0 - grow) & (y >= -21.0 - grow) & (y <= 203.0 + grow)
    return tongue | key | carrier


def clear_view(c, Ck, bx, by, plane, t_mm):
    """True when the dark/white boundary at (bx, by) is a clean edge: for a top edge (hidden face) the ray past it
    lands on the mat outside the slab; for a bottom edge (visible face) nothing of the slab is between it and the lens."""
    if plane == "top":
        s = t_mm / -Ck[2]
        lx, ly = bx + (bx - Ck[0]) * s, by + (by - Ck[1]) * s
        return not footprint(c, lx, ly, 0.7)
    for f in np.linspace(0.15, 1.0, 6):
        s = f * t_mm / (t_mm - Ck[2])
        if footprint(c, bx + (Ck[0] - bx) * s, by + (Ck[1] - by) * s, -0.3):
            return False
    return True


def measure_view(path, det, K, dist, t_mm, crop_dir=None):
    bgr = cv2.imread(str(path))
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    d = det.detect(gray)
    if d is None or len(d["ids"]) < 20:
        return {"view": str(path), "rejected": "fewer than 20 corners"}
    sol = C.solve_pose(d, K, dist)
    if sol["rms_px"] > 0.30:
        return {"view": str(path), "rejected": f"pose RMS {sol['rms_px']:.3f} px"}
    R, tv = sol["T_cv_K"][:3, :3], sol["T_cv_K"][:3, 3]
    rv = cv2.Rodrigues(R)[0]
    Ck = -R.T @ tv * 1000
    rec = {"view": str(path), "n_corners": int(len(d["ids"])), "rms_px": round(sol["rms_px"], 3),
           "camera_in_board_mm": Ck.round(1).tolist()}
    if Ck[2] > -100:
        return {**rec, "rejected": "camera not above the board"}
    imgs = {"top": rectify(gray, rv, tv, K, dist, 0.0), "bottom": rectify(gray, rv, tv, K, dist, t_mm)}
    cs = {k: coarse(*v) for k, v in imgs.items()}
    if cs["top"] is None or cs["bottom"] is None:
        return {**rec, "rejected": "tongue or key not found (out of view or low contrast)"}
    c0 = cs["top"]
    planes = {"face": "bottom" if Ck[0] < c0["face"] else "top", "tip": "bottom" if Ck[0] < c0["tip"] else "top",
              "side_lo": "bottom" if Ck[1] < c0["key_lo"] else "top", "side_hi": "bottom" if Ck[1] > c0["key_hi"] else "top"}
    # the slab's outline: each edge from the plane it is seen on
    c = {"face": cs[planes["face"]]["face"], "tip": cs[planes["tip"]]["tip"], "key_lo": cs[planes["side_lo"]]["key_lo"],
         "key_hi": cs[planes["side_hi"]]["key_hi"], "side_lo": c0["side_lo"], "side_hi": c0["side_hi"]}
    pts = {k: [] for k in ("face_lo", "face_hi", "tip", "side_lo", "side_hi")}
    im, ok = imgs[planes["face"]]
    for seg, (a, b) in (("face_lo", (c["side_lo"] + 3, c["key_lo"] - 3)), ("face_hi", (c["key_hi"] + 3, c["side_hi"] - 3))):
        x0, x1 = int(to_px(c["face"] - 4, 0)[0]), int(to_px(c["face"] + 4, 0)[0])
        for by in np.arange(a, b, 0.25):
            py = int(round(to_px(0, by)[1]))
            if not window_ok(ok, py, py + 1, x0, x1):
                continue
            e = edge_on_profile(im[py, x0:x1], rising=True)
            if e is not None:
                bx = to_mm(x0 + e, 0)[0]
                if clear_view(c, Ck, bx, by, planes["face"], t_mm):
                    pts[seg].append((by, bx))
    im, ok = imgs[planes["tip"]]
    x0, x1 = int(to_px(c["tip"] - 4, 0)[0]), int(to_px(c["tip"] + 3, 0)[0])
    for by in np.arange(c["key_lo"] + 3, c["key_hi"] - 3, 0.25):
        py = int(round(to_px(0, by)[1]))
        if window_ok(ok, py, py + 1, x0, x1):
            e = edge_on_profile(im[py, x0:x1], rising=True)
            if e is not None:
                bx = to_mm(x0 + e, 0)[0]
                if clear_view(c, Ck, bx, by, planes["tip"], t_mm):
                    pts["tip"].append((by, bx))
    for side, rising in (("side_lo", True), ("side_hi", False)):
        im, ok = imgs[planes[side]]
        yc = c["key_lo"] if side == "side_lo" else c["key_hi"]
        y0, y1 = int(to_px(0, yc - 4)[1]), int(to_px(0, yc + 4)[1])
        for bx in np.arange(c["tip"] + 1.0, c["face"] - 1.0, 0.1):
            px = int(round(to_px(bx, 0)[0]))
            if window_ok(ok, y0, y1, px, px + 1):
                e = edge_on_profile(im[y0:y1, px], rising=rising)
                if e is not None:
                    by = to_mm(0, y0 + e)[1]
                    if clear_view(c, Ck, bx, by, planes[side], t_mm):
                        pts[side].append((bx, by))
    n = {k: len(v) for k, v in pts.items()}
    rec.update({"planes": planes, "edge_points": n})
    if min(n["face_lo"], n["face_hi"]) < 20:
        return {**rec, "rejected": f"end face: too few clean edge points {n}"}
    face = np.array(pts["face_lo"] + pts["face_hi"])
    a0, a1, face_rms, _ = fit_line(face[:, 0], face[:, 1])               # bx = a0 + a1 by
    lo, hi = np.array(pts["face_lo"]), np.array(pts["face_hi"])
    yaw = math.degrees(math.atan(-a1))
    out = {**rec, "d_x_corner_mm": round(-a0, 3), "yaw_deg": round(yaw, 3), "face_rms_mm": round(face_rms, 3),
           "d_x_title_side_mm": round(-(a0 + a1 * lo[:, 0].mean()), 3), "by_title_side": round(lo[:, 0].mean(), 1),
           "d_x_other_side_mm": round(-(a0 + a1 * hi[:, 0].mean()), 3), "by_other_side": round(hi[:, 0].mean(), 1),
           "tongue_sides_coarse_mm": [round(c["side_lo"], 1), round(c["side_hi"], 1)]}
    # each key edge on its own (the two sides are rarely both clean in one view): the tip at by = 90 and each side
    # at the key's mid-length, so views seen from either side can be combined in the board frame
    if n["tip"] >= 40:
        t0, t1, tip_rms, _ = fit_line(*np.array(pts["tip"]).T)
        out["tip_bx_at_by90"] = round(t0 + t1 * 90.0, 3)
        out["key_mid_bx"] = round(0.5 * ((a0 + a1 * 90.0) + (t0 + t1 * 90.0)), 3)
        for side in ("side_lo", "side_hi"):
            if n[side] >= 10:
                f = fit_line(*np.array(pts[side]).T)
                out[f"{side}_by_at_mid"] = round(f[0] + f[1] * out["key_mid_bx"], 3)
                out[f"{side}_rms_mm"] = round(f[2], 3)
    key_ok = n["tip"] >= 40 and min(n["side_lo"], n["side_hi"]) >= 10
    if key_ok:
        t0, t1, tip_rms, _ = fit_line(*np.array(pts["tip"]).T)            # bx = t0 + t1 by
        sl = fit_line(*np.array(pts["side_lo"]).T)                        # by = s0 + s1 bx
        sh = fit_line(*np.array(pts["side_hi"]).T)
        by_k = 0.5 * (c["key_lo"] + c["key_hi"])
        for _ in range(3):                                                # key centre at the key's mid-length
            bx_face, bx_tip = a0 + a1 * by_k, t0 + t1 * by_k
            bx_k = 0.5 * (bx_face + bx_tip)
            y_lo, y_hi = sl[0] + sl[1] * bx_k, sh[0] + sh[1] * bx_k
            by_k = 0.5 * (y_lo + y_hi)
        s, co = math.sin(math.radians(yaw)), math.cos(math.radians(yaw))
        out.update({"key_width_mm": round(y_hi - y_lo, 3), "key_protrusion_mm": round(bx_face - bx_tip, 3),
                    "bx_k": round(bx_k, 3), "by_k": round(by_k, 3), "d_y_mm": round(co * by_k - s * bx_k, 3),
                    "key_side_slopes_deg": [round(math.degrees(math.atan(sl[1])), 2), round(math.degrees(math.atan(sh[1])), 2)],
                    "tip_rms_mm": round(tip_rms, 3), "key_side_rms_mm": [round(sl[2], 3), round(sh[2], 3)]})
    else:
        out["key_note"] = f"key not measured: too few clean edge points {n}"
    if crop_dir is not None:
        vis = cv2.cvtColor(np.clip(imgs[planes["face"]][0], 0, 255).astype(np.uint8), cv2.COLOR_GRAY2BGR)

        def P(bx, by):
            x, y = to_px(bx, by)
            return int(round(x)), int(round(y))
        for k, col in (("face_lo", (0, 0, 255)), ("face_hi", (0, 0, 255)), ("tip", (0, 200, 0))):
            for by, bx in pts[k]:
                cv2.circle(vis, P(bx, by), 1, col, -1)
        for k in ("side_lo", "side_hi"):
            for bx, by in pts[k]:
                cv2.circle(vis, P(bx, by), 1, (255, 0, 0), -1)
        cv2.line(vis, P(a0 + a1 * c["side_lo"], c["side_lo"]), P(a0 + a1 * c["side_hi"], c["side_hi"]), (0, 0, 255), 1)
        if key_ok:
            cv2.circle(vis, P(bx_k, by_k), 4, (0, 255, 255), -1)
        cv2.putText(vis, f"face plane {planes['face']}", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)
        cv2.imwrite(str(Path(crop_dir) / (Path(path).parent.name + "_" + Path(path).stem + ".png")), vis)
    return out


def summary(rows):
    keys = ("d_x_corner_mm", "yaw_deg", "d_y_mm", "d_x_title_side_mm", "d_x_other_side_mm", "key_width_mm",
            "key_protrusion_mm", "by_k")
    out = {"n": len(rows), "n_key": sum("d_y_mm" in r for r in rows)}
    for k in keys:
        v = np.array([r[k] for r in rows if k in r])
        if len(v) == 0:
            continue
        out[k] = {"mean": round(float(v.mean()), 3), "sd": round(float(v.std(ddof=1)), 3) if len(v) > 1 else None,
                  "sd_mean": round(float(v.std(ddof=1) / math.sqrt(len(v))), 3) if len(v) > 1 else None,
                  "median": round(float(np.median(v)), 3)}
    return out


def key_combined(rows):
    """Key centre from the side_lo views and the side_hi views together (each side where its face is hidden from the
    lens, so its top edge is the boundary); yaw from the end face of the views whose face plane is the top."""
    lo = [r["side_lo_by_at_mid"] for r in rows if "side_lo_by_at_mid" in r and r["planes"]["side_lo"] == "top"]
    hi = [r["side_hi_by_at_mid"] for r in rows if "side_hi_by_at_mid" in r and r["planes"]["side_hi"] == "top"]
    mid = [r["key_mid_bx"] for r in rows if "key_mid_bx" in r]
    tip = [r["tip_bx_at_by90"] for r in rows if "tip_bx_at_by90" in r and r["planes"]["tip"] == "top"]
    yaws = [r["yaw_deg"] for r in rows if r["planes"]["face"] == "top"]
    mid = [r["key_mid_bx"] for r in rows if "key_mid_bx" in r and r["planes"]["face"] == "top"]
    if not lo or not hi:
        return None
    by_k, bx_k, yaw = 0.5 * (np.mean(lo) + np.mean(hi)), float(np.median(mid)), float(np.mean(yaws))
    s, c = math.sin(math.radians(yaw)), math.cos(math.radians(yaw))
    sd = lambda v: round(float(np.std(v, ddof=1)), 3) if len(v) > 1 else None
    return {"n_side_lo": len(lo), "side_lo_by": round(float(np.mean(lo)), 3), "side_lo_sd": sd(lo),
            "n_side_hi": len(hi), "side_hi_by": round(float(np.mean(hi)), 3), "side_hi_sd": sd(hi),
            "key_width_mm": round(float(np.mean(hi) - np.mean(lo)), 3), "by_k": round(by_k, 3), "bx_k": round(bx_k, 3),
            "tip_bx_at_by90": round(float(np.mean(tip)), 3) if tip else None, "yaw_used_deg": round(yaw, 3),
            "d_y_mm": round(c * by_k - s * bx_k, 3),
            "d_y_sd_mean": round(0.5 * math.hypot(np.std(lo, ddof=1) / math.sqrt(len(lo)) if len(lo) > 1 else 0,
                                                  np.std(hi, ddof=1) / math.sqrt(len(hi)) if len(hi) > 1 else 0), 3)}


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--views", nargs="*")
    ap.add_argument("--out", required=True)
    ap.add_argument("--square-mm", type=float, default=29.97)
    ap.add_argument("--t-mm", type=float, default=4.85, help="board thickness: top of the print to the foam's underside")
    ap.add_argument("--intrinsics", default=str(GTC / "config" / "c920_intrinsics.json"))
    a = ap.parse_args(argv)
    views = a.views or sorted(glob.glob(str(GTC / "media/calib/intrinsics/A/*.png"))) + sorted(
        glob.glob(str(GTC / "media/calib/intrinsics/B/*.png")))
    intr = json.loads(Path(a.intrinsics).read_text())
    K, dist = np.array(intr["K"]), np.array(intr["dist"])
    det = C.Detector(a.square_mm)
    out = Path(a.out)
    (out / "crops").mkdir(parents=True, exist_ok=True)
    rows = [measure_view(v, det, K, dist, a.t_mm, out / "crops") for v in views]
    kept = [r for r in rows if "rejected" not in r]
    res = {"intrinsics": a.intrinsics, "square_mm": a.square_mm, "t_mm": a.t_mm, "ppm": PPM,
           "summary_all": summary(kept) if kept else None,
           "summary_face_top": summary([r for r in kept if r["planes"]["face"] == "top"]) if kept else None,
           "summary_face_bottom": summary([r for r in kept if r["planes"]["face"] == "bottom"])
           if any(r["planes"]["face"] == "bottom" for r in kept) else None,
           "views": rows}
    res["key_combined"] = key_combined(kept)
    (out / "sled_from_views.json").write_text(json.dumps(res, indent=1))
    for r in kept:
        key = (f"d_y {r['d_y_mm']:.2f} key {r['key_width_mm']:.2f} x {r['key_protrusion_mm']:.2f}" if "d_y_mm" in r
               else "key -")
        print(f"{Path(r['view']).parent.name}/{Path(r['view']).name}: d_x0 {r['d_x_corner_mm']:.2f} yaw {r['yaw_deg']:+.2f} "
              f"sides {r['d_x_title_side_mm']:.2f}/{r['d_x_other_side_mm']:.2f} | {key} | {r['planes']} "
              f"pts {r['edge_points']} C_K {[round(v) for v in r['camera_in_board_mm']]}")
    print(f"kept {len(kept)} of {len(rows)}")
    if kept:
        print(json.dumps(res["summary_all"], indent=None))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
