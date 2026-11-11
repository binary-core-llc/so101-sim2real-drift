#!/usr/bin/env python3
"""Drift check dry run: the sim R0 render as the reference, shifted/rotated/dimmed copies as later frames.

    .venv/bin/python -I tests/test_drift_synthetic.py
Expected verdicts (B 8 step 2 on the 3x3 grid, similarity fit): <= 1 px PASS, 1-2 px WARN, > 2 px FAIL; a
perspective change the similarity fit cannot follow is caught by the homography rule (> 2 px -> WARN); a dimmer
light alone does not move the geometry; a dark frame STOPs. A 0.3 deg roll moves the outer grid points 1.68 px.
"""
import subprocess
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np

GTC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GTC / "calib"))
import capture  # noqa: E402


def warp(img, dx=0, dy=0, rot=0.0, gain=1.0, scale=1.0, keystone=0.0):
    M = cv2.getRotationMatrix2D((319.5, 239.5), rot, scale)
    M[:, 2] += (dx, dy)
    H = np.vstack([M, [0, keystone, 1.0]])
    out = cv2.warpPerspective(img, H, (640, 480), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    return np.clip(out.astype(float) * gain, 0, 255).astype(np.uint8)


def main():
    ref = capture.load_rgb(GTC / "results/overlay_refs/sim_r0_front_rgb.png")
    tmp = Path(tempfile.mkdtemp())
    capture.save_rgb(tmp / "ref.png", ref)
    cases = [("identical", {}, 0), ("0.5 px", {"dx": 0.5}, 0), ("1.5 px", {"dx": 1.2, "dy": 0.9}, 1), ("3 px", {"dx": 3.0}, 2),
             ("0.3 deg roll = 1.68 px", {"rot": 0.3}, 1), ("0.5 deg roll = 2.8 px", {"rot": 0.5}, 2),
             ("zoom 0.3 % = 0.96 px", {"scale": 1.003}, 0), ("zoom -0.5 % + 0.4 px = 1.9 px", {"scale": 0.995, "dx": 0.4}, 1),
             ("keystone: sim 1.3, homography 2.3 px", {"keystone": 7e-6}, 1),
             ("light x0.8, no move", {"gain": 0.8}, 0), ("dark", {"gain": 0.03}, 3)]
    ok = True
    for name, kw, want in cases:
        capture.save_rgb(tmp / "cur.png", warp(ref, **kw))
        r = subprocess.run([sys.executable, "-I", str(GTC / "calib/drift_check.py"), "check", "--source", str(tmp / "cur.png"),
                            "--ref", str(tmp / "ref.png"), "--out-root", str(tmp)], capture_output=True, text=True)
        good = r.returncode == want
        ok &= good
        print(f"  {name:24s} exit {r.returncode} (want {want}) {'ok' if good else 'BAD'}  {r.stdout.strip()[:90]}")
    import drift_check as D                         # the homography rule alone: similarity PASS, homography > 2 px
    D.align = lambda r, c, m=None: ({"max_px": 0.8, "homography_max_px": 2.3}, np.eye(3), None)
    rec, _ = D.compare(ref, ref)
    good = rec["verdict"] == "WARN"
    ok &= good
    print(f"  {'rule: similarity 0.8, homography 2.3':24s} verdict {rec['verdict']} (want WARN) {'ok' if good else 'BAD'}")
    print("DRIFT TEST", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
