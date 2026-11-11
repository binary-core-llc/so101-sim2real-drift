#!/usr/bin/env python3
"""E3 synthetic validation: photos rendered from the course scene at known camera / rack deltas (exact scene, no
segmentation), with a don't-care patch where the robot would be; E3's estimate against the truth.

    python -I validate.py --frames frames_sim.json --usd-dir <assets/usd> [--out results.json]
Camera truths are lens-frame moves from the simulation's camera (the C920 focal); rack truths are (x, y mm, yaw deg)
about corner O.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import estimate as E  # noqa: E402
import render as Rn  # noqa: E402

F = 630.62
CAM_TRUTHS = {"tilt_down_6": [0, 0, 0, -6, 0, 0], "tilt_up_6": [0, 0, 0, 6, 0, 0], "pan_3": [0, 0, 0, 0, 3, 0],
              "height_15": [0, -15, 0, 0, 0, 0], "mix": [8, -10, 12, -4, 2, 1]}
RACK_TRUTHS = {"y+30": [0, 30, 0], "x+30": [30, 0, 0], "x-30": [-30, 0, 0], "yaw15": [0, 0, 15], "y-10_yaw8": [0, -10, 8], "mix": [15, 20, -5]}


def photo(scene, R, C, rack=(0, 0, 0)):
    img = Rn.render_e3(scene, R, C, F, 640, 480, rack)
    img[60:330, 520:] = 0                          # where the arm sits in the front view: don't care
    return img.astype(np.uint8)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", required=True)
    ap.add_argument("--usd-dir", required=True)
    ap.add_argument("--out")
    ap.add_argument("--search", choices=["nm", "cem"], default="nm")
    a = ap.parse_args(argv)
    scene, rig = Rn.load_scene(a.frames, a.usd_dir)
    be = E.NumpyBackend(scene)
    cam = (lambda R0, C0, ph: E.search_camera_cem(be, F, R0, C0, ph, log=lambda *x: None)) if a.search == "cem" else \
        (lambda R0, C0, ph: E.search_camera(scene, F, R0, C0, ph, log=lambda *x: None))
    rack = (lambda R0, C0, ph: E.search_rack_cem(be, F, R0, C0, ph, log=lambda *x: None)) if a.search == "cem" else \
        (lambda R0, C0, ph: E.search_rack(scene, F, R0, C0, ph, log=lambda *x: None))
    R0, C0 = rig.lens(np.zeros(6))
    out = {"camera": {}, "rack": {}}
    for k, p in CAM_TRUTHS.items():
        Rt, Ct = Rn.lens_move(R0, C0, p)
        R, C, _, secs = cam(R0, C0, photo(scene, Rt, Ct))
        truth, est = E.b13_delta(R0, C0, Rt, Ct), E.b13_delta(R0, C0, R, C)
        err = {k2: est[k2] - truth[k2] for k2 in truth}
        out["camera"][k] = {"truth": truth, "estimate": est, "error": err, "seconds": round(secs, 1)}
        print(f"camera {k:12s} error: tilt {err['tilt_down_deg']:+.2f} pan {err['pan_deg']:+.2f} roll {err['roll_deg']:+.2f} deg; "
              f"lateral {1000 * err['lateral_m']:+.1f} depth {1000 * err['depth_m']:+.1f} height {1000 * err['height_m']:+.1f} mm ({secs:.0f} s)")
    for k, q in RACK_TRUTHS.items():
        x, secs = rack(R0, C0, photo(scene, R0, C0, (q[0] / 1000, q[1] / 1000, q[2])))
        err = (np.array(x) - np.array(q, float)).tolist()
        out["rack"][k] = {"truth": q, "estimate": list(map(float, x)), "error": err, "seconds": round(secs, 1)}
        print(f"rack   {k:12s} error: x {err[0]:+.2f} y {err[1]:+.2f} mm, yaw {err[2]:+.2f} deg ({secs:.0f} s)")
    if a.out:
        Path(a.out).write_text(json.dumps(out, indent=1, default=float))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
