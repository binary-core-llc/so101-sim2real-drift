#!/usr/bin/env python3
"""Drift check of the C920x (B section 8, step 2 plate match), headless.

    .venv/bin/python -I calib/drift_check.py reference        # last step of the setup day, light at trial level (then light off)
    .venv/bin/python -I calib/drift_check.py check            # first thing on each later day, light at trial level
    .venv/bin/python -I calib/drift_check.py compare A.png B.png [--mask M.png]   # any two images (also T19)

check: the camera is found by its USB identity (stops if absent), the lock is re-applied from
config/camera_lock.json (after a reboot it is lost) and read back, 10 frames are averaged and aligned to
results/drift/reference_front.png. Geometry verdict = largest displacement of a 3x3 grid of image points under a
similarity fit (shift, rotation, scale; with brightness gain and offset), started from an ECC Euclidean fit and
refined by Gauss-Newton: <= 1.0 px PASS, 1-2 px WARN, > 2 px FAIL (B 8 step 2). The ECC homography (B 8's model)
is reported too and turns a PASS into WARN when its grid displacement is above 2 px (Oct 25; on rendered
test frames the homography read a 0.50 px shift as 1.03 px, so it does not set the verdict alone).
Brightness against the reference is reported with the B 8 step 5 bands (light check), separately from the
geometry verdict. Take the reference and every check with the light at trial level.
Exit 0 PASS, 1 WARN, 2 FAIL, 3 STOP (no camera, lock does not read back, frame too dark to compare, or ECC did
not converge).
Writes results/drift/<utc>.json and media/drift/<utc>_{frame,diff}.png.
"""
import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))  # sibling modules (python -I skips the script dir)

import camera_lock  # noqa: E402
import capture  # noqa: E402

GTC = Path(__file__).resolve().parents[1]
REF = GTC / "results" / "drift" / "reference_front.png"
PASS_PX, WARN_PX, DARK = 1.0, 2.0, 15.0


def ecc(g0, g1, mask, motion):
    warp = np.eye(3, dtype=np.float32) if motion == cv2.MOTION_HOMOGRAPHY else np.eye(2, 3, dtype=np.float32)
    crit = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 300, 1e-7)
    cc, warp = cv2.findTransformECC(g0, g1, warp, motion, crit, mask, 5)
    return float(cc), warp if warp.shape == (3, 3) else np.vstack([warp, [0, 0, 1]]).astype(np.float32)


def grid_disp(warp, h, w):
    pts = np.array([[x, y, 1.0] for y in (0.1 * h, 0.5 * h, 0.9 * h) for x in (0.1 * w, 0.5 * w, 0.9 * w)])
    q = pts @ warp.T
    return np.hypot(*(q[:, :2] / q[:, 2:] - pts[:, :2]).T)


def similarity_refine(g0, g1, mask, M0, iters=60):
    """Gauss-Newton fit of g0(x) ~ gain * g1(W x) + offset, W a similarity about the image centre:
    x' - c = [[a, -b], [b, a]] (x - c) + t. Starts from the 2x3 warp M0; returns the 2x3 pixel warp."""
    h, w = g0.shape
    c = np.array([(w - 1) / 2, (h - 1) / 2])
    A0 = M0[:, :2]
    t = M0[:, 2] + A0 @ c - c
    p = np.array([A0[0, 0], A0[1, 0], t[0], t[1]], np.float64)          # a, b, tx, ty
    gx1, gy1 = cv2.Sobel(g1, cv2.CV_32F, 1, 0, ksize=3) / 8, cv2.Sobel(g1, cv2.CV_32F, 0, 1, ksize=3) / 8
    ys, xs = np.mgrid[0:h:2, 0:w:2]
    keep = mask[0:h:2, 0:w:2] > 0
    xc, yc = (xs - c[0])[keep].astype(np.float64), (ys - c[1])[keep].astype(np.float64)
    T = g0[0:h:2, 0:w:2][keep].astype(np.float64)

    def warp_of(p):
        a, b, tx, ty = p
        return np.array([[a, -b, tx + c[0] - a * c[0] + b * c[1]], [b, a, ty + c[1] - b * c[0] - a * c[1]]], np.float32)

    for _ in range(iters):
        M = warp_of(p)
        I, Gx, Gy = (cv2.warpAffine(x, M, (w, h), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP)[0:h:2, 0:w:2][keep]
                     .astype(np.float64) for x in (g1, gx1, gy1))
        J = np.column_stack([Gx * xc + Gy * yc, -Gx * yc + Gy * xc, Gx, Gy, I, np.ones_like(I)])
        gain_off, *_ = np.linalg.lstsq(J[:, 4:], T, rcond=None)
        r = T - (gain_off[0] * I + gain_off[1])
        J[:, :4] *= gain_off[0]
        d, *_ = np.linalg.lstsq(J, r, rcond=None)
        p += d[:4]
        if np.abs(d[:4]).max() < 1e-6:
            break
    return warp_of(p)


def align(ref, cur, mask=None):
    """ref -> cur: similarity fit (verdict), ECC homography (reported); 3x3 grid displacement in px."""
    g0, g1 = (cv2.GaussianBlur(cv2.cvtColor(x, cv2.COLOR_RGB2GRAY), (0, 0), 1.0).astype(np.float32) for x in (ref, cur))
    if mask is None:
        mask = ((g0 > 8) & (g0 < 247)).astype(np.uint8)
    try:
        cc, euc = ecc(g0, g1, mask, cv2.MOTION_EUCLIDEAN)
    except cv2.error as e:
        return None, None, str(e).splitlines()[-1]
    sim = similarity_refine(g0, g1, mask, euc[:2])
    warp = np.vstack([sim, [0, 0, 1]]).astype(np.float32)
    disp = grid_disp(warp, *g0.shape)
    a, b = float(sim[0, 0]), float(sim[1, 0])
    rec = {"ecc_euclidean": cc, "max_px": float(disp.max()), "mean_px": float(disp.mean()), "grid_px": disp.round(3).tolist(),
           "similarity": sim.tolist(), "rotation_deg": float(np.degrees(np.arctan2(b, a))), "scale": float(np.hypot(a, b)),
           "euclidean_max_px": float(grid_disp(euc, *g0.shape).max())}
    try:
        _, hw = ecc(g0, g1, mask, cv2.MOTION_HOMOGRAPHY)
        rec["homography_max_px"] = float(grid_disp(hw, *g0.shape).max())
    except cv2.error:
        rec["homography_max_px"] = None
    return rec, warp, None


def verdict(max_px):
    return "PASS" if max_px <= PASS_PX else "WARN" if max_px <= WARN_PX else "FAIL"


def compare(ref, cur, mask=None):
    rec = {"brightness_ratio": float(cur.mean() / max(ref.mean(), 1e-6)), "cur_mean": float(cur.mean())}
    b = abs(rec["brightness_ratio"] - 1)
    rec["brightness"] = "PASS" if b <= 0.04 else "WARN" if b <= 0.08 else "FAIL"
    if cur.mean() < DARK:
        rec.update({"verdict": "STOP", "reason": f"frame too dark to compare (mean {cur.mean():.1f}); is the box light on?"})
        return rec, None
    geo, warp, err = align(ref, cur, mask)
    if geo is None:
        rec.update({"verdict": "STOP", "reason": f"ECC did not converge: {err}"})
        return rec, None
    rec.update(geo)
    rec["verdict"] = verdict(geo["max_px"])
    if rec["verdict"] == "PASS" and (geo.get("homography_max_px") or 0) > WARN_PX:
        rec["verdict"] = "WARN"
        rec["warn_reason"] = f"homography grid displacement {geo['homography_max_px']:.2f} px > {WARN_PX} px"
    return rec, warp


def diff_image(ref, cur, warp):
    h, w = ref.shape[:2]
    back = cv2.warpPerspective(cur, warp, (w, h), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP) if warp is not None else cur
    d = np.abs(ref.astype(int) - back.astype(int)).astype(np.uint8)
    return np.hstack([ref, cur, np.clip(d * 3, 0, 255).astype(np.uint8)])


def grab(frames):
    if camera_lock.cmd_apply("front", write=True) != 0:
        raise SystemExit(3)
    cam = capture.Camera("front")
    try:
        img = capture.mean_frames(cam, frames)
        ident = cam.identity
    finally:
        cam.close()
    return img, ident


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["reference", "check", "compare"])
    ap.add_argument("files", nargs="*")
    ap.add_argument("--frames", type=int, default=10)
    ap.add_argument("--mask", default=None)
    ap.add_argument("--source", default=None, help="test only: compare this image instead of grabbing")
    ap.add_argument("--ref", default=str(REF), help="test only: another reference path")
    ap.add_argument("--out-root", default=str(GTC), help="test only: where results/ and media/ go")
    a = ap.parse_args(argv)
    ref_p, root = Path(a.ref), Path(a.out_root)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    mask = None if not a.mask else (cv2.imread(a.mask, cv2.IMREAD_GRAYSCALE) > 0).astype(np.uint8)
    try:
        if a.cmd == "compare":
            rec, warp = compare(capture.load_rgb(a.files[0]), capture.load_rgb(a.files[1]), mask)
            print(json.dumps({k: v for k, v in rec.items() if k != "homography"}))
            return {"PASS": 0, "WARN": 1, "FAIL": 2}.get(rec["verdict"], 3)
        if a.cmd == "reference":
            img, ident = (capture.load_rgb(a.source), {"product": "test"}) if a.source else grab(a.frames)
            capture.save_rgb(ref_p, img)
            meta = {"utc": stamp, "camera": ident, "frames": a.frames, "mean": float(img.mean())}
            ref_p.with_suffix(".json").write_text(json.dumps(meta, indent=1))
            print(f"reference saved: {ref_p} (mean brightness {img.mean():.1f})")
            return 0
        if not ref_p.exists():
            raise SystemExit(f"STOP: no reference ({ref_p}); take it with: drift_check.py reference")
        cur, ident = (capture.load_rgb(a.source), {"product": "test"}) if a.source else grab(a.frames)
        ref = capture.load_rgb(ref_p)
        rec, warp = compare(ref, cur, mask)
    except SystemExit as e:
        if e.code == 3 or isinstance(e.code, str):
            print(e.code if isinstance(e.code, str) else "STOP: camera lock does not read back", file=sys.stderr)
            return 3
        raise
    rec.update({"utc": stamp, "camera": ident, "reference": json.loads(ref_p.with_suffix(".json").read_text())
                if ref_p.with_suffix(".json").exists() else None})
    out = root / "results" / "drift" / f"{stamp}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec, indent=1))
    capture.save_rgb(root / "media" / "drift" / f"{stamp}_frame.png", cur)
    capture.save_rgb(root / "media" / "drift" / f"{stamp}_diff.png", diff_image(ref, cur, warp))
    if rec["verdict"] == "STOP":
        print(f"DRIFT STOP: {rec['reason']}")
        return 3
    print(f"DRIFT {rec['verdict']}: max grid displacement {rec['max_px']:.2f} px (similarity; scale {rec['scale']:.4f}, "
          f"rotation {rec['rotation_deg']:+.3f} deg; PASS <= {PASS_PX}, WARN <= {WARN_PX}); homography "
          f"{rec.get('homography_max_px') or float('nan'):.2f} px; brightness x{rec['brightness_ratio']:.3f} "
          f"({rec['brightness']}, informational) -> {out}")
    return {"PASS": 0, "WARN": 1, "FAIL": 2}[rec["verdict"]]


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
