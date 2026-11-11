#!/usr/bin/env python3
"""T20 dry run: a "C920x photo" of the sim R0 scene through a different, distorted lens (the made-up test lens of
tests/make_synthetic_calib.py), same pose. With that lens's intrinsics the overlay's remap must put it back on
the sim render (sub-pixel); without intrinsics (D455 values) the misalignment must show.

    .venv/bin/python -I tests/test_overlay_synthetic.py
Measures the residual shift by ECC (translation) on the overlapping region, and runs overlay.py headless on
the synthetic photo in both modes (writes test_*.png in a temporary folder).
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np

GTC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GTC / "calib"))
sys.path.insert(0, str(GTC / "tests"))
import capture  # noqa: E402
import overlay  # noqa: E402
from make_synthetic_calib import DIST, K  # noqa: E402


def through_lens(sim_rgb, K_sim, K_c, dist_c):
    """Image a C920-like camera with (K_c, dist_c) would take from the sim camera's pose."""
    w, h = 640, 480
    uv = np.stack(np.meshgrid(np.arange(w), np.arange(h)), -1).reshape(-1, 1, 2).astype(np.float64)
    n = cv2.undistortPointsIter(uv, K_c, dist_c, None, None, (cv2.TERM_CRITERIA_COUNT | cv2.TERM_CRITERIA_EPS, 40, 1e-10))
    n = n.reshape(-1, 2)
    mx = (K_sim[0, 0] * n[:, 0] + K_sim[0, 2]).reshape(h, w).astype(np.float32)
    my = (K_sim[1, 1] * n[:, 1] + K_sim[1, 2]).reshape(h, w).astype(np.float32)
    return cv2.remap(sim_rgb, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)


def shift(a, b, mask):
    warp = np.eye(2, 3, dtype=np.float32)
    ga, gb = (cv2.cvtColor(x, cv2.COLOR_RGB2GRAY).astype(np.float32) for x in (a, b))
    _, warp = cv2.findTransformECC(ga, gb, warp, cv2.MOTION_TRANSLATION,
                                   (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-6), mask.astype(np.uint8), 5)
    return float(np.hypot(warp[0, 2], warp[1, 2]))


def main():
    Ks = overlay.k_sim()
    sim, _ = overlay.load_ref(overlay.REFS["sim_r0"])
    photo = through_lens(sim, Ks, K, DIST)
    tmp = Path(tempfile.mkdtemp())
    capture.save_rgb(tmp / "photo.png", photo)
    (tmp / "intr.json").write_text(json.dumps({"K": K.tolist(), "dist": DIST.tolist()}))
    back = overlay.Undistorter(str(tmp / "intr.json"), Ks)(photo)
    valid = cv2.erode((back.sum(-1) > 0).astype(np.uint8), np.ones((9, 9), np.uint8))
    diff = np.abs(back.astype(int) - sim.astype(int)).mean(-1)[valid > 0]
    s_with = shift(sim, back, valid)
    s_without = shift(sim, photo, (photo.sum(-1) > 0).astype(np.uint8))
    ok = s_with < 0.25 and np.median(diff) < 3
    print(f"  with intrinsics: residual shift {s_with:.3f} px, median |diff| {np.median(diff):.2f} grey levels "
          f"over {valid.mean() * 100:.0f}% of the image")
    print(f"  without (D455 values): shift {s_without:.2f} px (the C920-vs-D455 lens difference stays visible)")
    out = tmp
    for mode, extra in (("with_intrinsics", ["--intrinsics", str(tmp / "intr.json")]), ("d455_values", [])):
        r = subprocess.run([sys.executable, "-I", str(GTC / "calib" / "overlay.py"), "--ref", "sim_r0", "--source",
                            str(tmp / "photo.png"), "--headless-frames", "3", "--save", str(out / f"test_{mode}.png")] + extra,
                           capture_output=True, text=True)
        ok &= r.returncode == 0
        print(f"  overlay.py headless ({mode}): exit {r.returncode} -> {out / f"test_{mode}.png"} {r.stderr[-200:]}")
    r = subprocess.run([sys.executable, "-I", str(GTC / "calib" / "overlay.py"), "--ref", "sim_nominal", "--source",
                        str(tmp / "photo.png"), "--headless-frames", "2"], capture_output=True, text=True)
    ok &= r.returncode == 0
    print(f"  overlay.py headless (sim_nominal reference): exit {r.returncode} {r.stderr[-200:]}")
    print("OVERLAY TEST", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
