#!/usr/bin/env python3
"""calib/aim_view.py grid centre and horizon roll on projected board corners (no camera).

    .venv/bin/python -I tests/test_aim_view.py
Pinhole cameras at R0-like poses (depression 39-51 deg, heading -95 to -75, roll -3 to +2) with several focal
lengths, principal points and board yaws (test values, not readings): without noise, roll from the board's
vanishing line within 0.001 deg and the grid centre within 0.01 px of its projection; with 0.05 px corner noise,
roll SD <= 0.1 deg. Then the made-up test lens distortion of tests/make_synthetic_calib.py (not the C920's), to show
the size of the uncorrected-distortion error (printed only).
"""
import math
import sys
from pathlib import Path

import cv2
import numpy as np

GTC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GTC / "calib"))
sys.path.insert(0, str(GTC / "tests"))
import aim_view  # noqa: E402
import charuco as C  # noqa: E402
from make_synthetic_calib import DIST, K as K_TEST  # noqa: E402

LENS_E = np.array([0.182, 0.330, 0.400])
MAT_E = np.array([0.220, 0.0, 0.0])


def board_E(yaw_deg):
    """Inner corners and grid centre of the board lying flat, centred on the mat centre, in E."""
    obj = C.make_board().getChessboardCorners()[:, :2]
    c, s = math.cos(math.radians(yaw_deg)), math.sin(math.radians(yaw_deg))
    R = np.array([[c, -s], [s, c]])
    xy = (obj - aim_view.CENTRE_OBJ) @ R.T + MAT_E[:2]
    return obj, np.column_stack([xy, np.zeros(len(xy))])


def project(P_E, R_E_cv, K, dist=None):
    rvec, _ = cv2.Rodrigues(R_E_cv.T)
    tvec = -R_E_cv.T @ LENS_E
    img, _ = cv2.projectPoints(P_E, rvec, tvec, K, dist if dist is not None else np.zeros(5))
    return img.reshape(-1, 2)


def det_of(obj, img):
    return {"ids": np.arange(len(obj)), "obj": np.column_stack([obj, np.zeros(len(obj))]), "img": img}


def main():
    rng = np.random.default_rng(5)
    worst_roll, worst_c, n = 0.0, 0.0, 0
    for d, h, r in [(45, -83.4, 0.0), (45, -83.4, 2.0), (45, -90, -1.5), (39, -75, 0.7), (51, -95, -3.0)]:
        R = C.rot_from_angles(d, h, r)
        for f in (450.0, 600.0):
            for cx, cy in ((320.0, 240.0), (305.0, 255.0)):
                K = np.array([[f, 0, cx], [0, f, cy], [0, 0, 1.0]])
                for yaw in (0.0, 30.0, 90.0):
                    obj, P = board_E(yaw)
                    det = det_of(obj, project(P, R, K))
                    centre = project(np.array([MAT_E]), R, K)[0]
                    worst_roll = max(worst_roll, abs(aim_view.roll(det) - r))
                    worst_c = max(worst_c, float(np.linalg.norm(aim_view.grid_centre(det) - centre)))
                    n += 1
    ok = worst_roll <= 0.001 and worst_c <= 0.01
    print(f"  {'ok  ' if ok else 'FAIL'} {n} poses, no noise: roll error max {worst_roll:.5f} deg, grid centre error "
          f"max {worst_c:.4f} px")
    R = C.rot_from_angles(45, -83.4, 0.0)
    K = np.array([[495.0, 0, 320], [0, 495.0, 240], [0, 0, 1]])
    obj, P = board_E(0.0)
    sd = float(np.std([aim_view.roll(det_of(obj, project(P, R, K) + rng.normal(0, 0.05, (len(P), 2))))
                       for _ in range(200)]))
    ok_n = sd <= 0.1
    print(f"  {'ok  ' if ok_n else 'FAIL'} 0.05 px corner noise: roll SD {sd:.3f} deg over 200 draws")
    ok = ok and ok_n
    got = aim_view.roll(det_of(obj, project(P, R, K_TEST, DIST)))
    print(f"  info: test-lens distortion uncorrected: roll {got:+.3f} deg for a true 0.0")
    print("AIM VIEW TEST " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
