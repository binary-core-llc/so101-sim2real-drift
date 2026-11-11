#!/usr/bin/env python3
"""Pose tool dry run on rendered views of the real print: the sled board seen from the R0 camera pose.

    .venv/bin/python -I tests/test_pose_synthetic.py [intrinsics.json]
The board sits at the B 4.2 CAD placement (grid origin E (0.100, 0.110), board x = +x_E, y = -y_E); the camera is
at the R0 target (config/r0_pose.json: lens centre, 45.0 deg down, heading toward the mat centre, level), then
tilted +6 deg, rolled +3 deg and panned +2 deg with the board untouched. Views are rendered with the made-up test
lens of tests/make_synthetic_calib.py; the pose tool uses the intrinsics given (default: that same lens), so a
calibration's own error can be included. Checks (T11 [P]): absolute centre <= 1 mm and angles <= 0.1 deg with
the true lens; deltas within 0.05 deg; same deltas without board_in_E.json.
"""
import json
import math
import sys
import tempfile
from pathlib import Path

import numpy as np

GTC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GTC / "calib"))
sys.path.insert(0, str(GTC / "tests"))
import charuco as C  # noqa: E402
import pose  # noqa: E402
from make_synthetic_calib import DIST, K  # noqa: E402


def R_E_cv(depression, heading, roll):
    d, h, r = map(math.radians, (depression, heading, roll))
    z = np.array([math.cos(d) * math.cos(h), math.cos(d) * math.sin(h), -math.sin(d)])
    x = np.cross(z, [0, 0, 1.0])
    x /= np.linalg.norm(x)
    y = np.cross(z, x)
    return np.column_stack([math.cos(r) * x + math.sin(r) * y, -math.sin(r) * x + math.cos(r) * y, z])


def main(argv):
    Kp, Dp = K, DIST
    if argv:
        j = json.loads(Path(argv[0]).read_text())
        Kp, Dp = np.array(j["K"]), np.array(j["dist"])
    r0 = json.loads((GTC / "config" / "r0_pose.json").read_text())
    C_E = np.array(r0["target_lens_env"])
    board = {"d_x_mm": 101.1, "d_y_mm": 89.2, "h_K_mm": 9.9, "yaw_deg": 0.0, "method": "test: B 4.2 CAD intent"}
    tmp = Path(tempfile.mkdtemp())
    (tmp / "board.json").write_text(json.dumps(board))
    T_E_K, _ = C.board_in_E(tmp / "board.json")
    tex, H, _ = C.pdf_texture(300)
    base = (45.0, r0["target_heading_deg"], 0.0)
    cases = {"r0": base, "tilt6": (51.0, base[1], 0.0), "roll3": (45.0, base[1], 3.0), "pan2": (45.0, base[1] + 2.0, 0.0)}
    recs, ok = {}, True
    for name, ang in cases.items():
        T_E_cv = C.T(R_E_cv(*ang), C_E)
        T_cv_K = np.linalg.inv(T_E_cv) @ T_E_K
        frames = [np.repeat(C.render_view(tex, H, K, DIST, T_cv_K, noise=1.5, blur=0.7, rng=np.random.default_rng(i))[:, :, None], 3, 2)
                  for i in range(8)]
        recs[name] = pose.measure_frames(frames, Kp, Dp, 30.0, T_E_K)
        recs[name + "_noE"] = pose.measure_frames(frames, Kp, Dp, 30.0, None)
        g = recs[name]["angles"]
        err_c = 1000 * np.linalg.norm(np.subtract(recs[name]["C_E_m"], C_E))
        err_a = max(abs(g["depression_deg"] - ang[0]), abs((g["heading_deg"] - ang[1] + 180) % 360 - 180), abs(g["roll_deg"] - ang[2]))
        print(f"  {name:6s} corners {recs[name]['n_corners']:2d} RMS {recs[name]['rms_px']:.3f} px | centre error {err_c:.2f} mm, "
              f"angle error {err_a:.3f} deg (depression {g['depression_deg']:.2f}, heading {g['heading_deg']:.2f}, roll {g['roll_deg']:.2f})")
        if not argv:
            ok &= err_c <= 1.0 and err_a <= 0.1
    for name, key, want in (("tilt6", "tilt_down_deg", 6.0), ("roll3", "roll_deg", 3.0), ("pan2", "pan_deg", 2.0)):
        for suffix in ("", "_noE"):
            d = pose.diff(recs["r0" + suffix], recs[name + suffix])
            good = abs(d[key] - want) <= 0.05
            ok &= good
            print(f"  diff r0 -> {name}{suffix or ' (E)':7s} {key} {d[key]:+.3f} (want {want:+.1f}) "
                  f"other: tilt {d['tilt_down_deg']:+.3f} roll {d['roll_deg']:+.3f} pan {d['pan_deg']:+.3f}  {'ok' if good else 'FAIL'}")
    print("POSE TEST", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
