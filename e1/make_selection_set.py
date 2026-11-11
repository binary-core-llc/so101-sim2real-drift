#!/usr/bin/env python3
"""E1 selection set (v2 item 2b: the variant is chosen on simulated scenes only, before E1 sees any real photo).

    .venv/bin/python -I e1/make_selection_set.py            # -> results/e1/selection_sets.json (+ truths)
    sim/run_sim.sh e1sel python /workspace/gtc/sim/sweep_eval.py --headless --cell_id E1SEL \
        --probe @/workspace/gtc/results/e1/selection_sets.json --probe_seeds 0 \
        --results /workspace/gtc/results/e1 --media /workspace/gtc/media/e1sel
Scenes: the Eval scene, every randomization at its centre, layout seed 0, rendered with the C920's measured focal
(fx 630.62 px -> 2.3648 mm at horizontalAperture 2.4 mm), first frame after the 10 warm-up steps (probe mode, no
policy). A = "nominal". B = 12 camera mis-setups (rack nominal) and 12 rack mis-setups (camera nominal), at the scale
of the planned M1/M2 mis-setups (6 deg tilt, 30 mm rack) and smaller, single and combined. Camera moves are physical
(B 1.3: tilt down about the camera's horizontal axis, pan about the vertical, roll about the optical axis; lateral = E y,
depth = E x, height = E z, at the lens) and converted exactly to the sim's camera_mount offsets with the camera rig of
sim/image_matched_pose.py. Rack moves are the code offsets of corner O (x toward the back wall, y toward the camera
wall, yaw about O). Truth per scene in Appendix C terms.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

GTC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GTC / "sim"))
import image_matched_pose as M  # noqa: E402

FX = 630.62
FOCAL_MM = round(FX * 2.4 / 640, 6)
CAM = [("tilt_down_6", dict(tilt=6)), ("tilt_up_6", dict(tilt=-6)), ("tilt_down_3", dict(tilt=3)), ("tilt_up_2", dict(tilt=-2)),
       ("pan_back_4", dict(pan=4)), ("pan_front_4", dict(pan=-4)), ("height_up_15", dict(height=15)),
       ("height_down_20", dict(height=-20)), ("lateral_away_20", dict(lateral=-20)), ("depth_back_20", dict(depth=20)),
       ("roll_3", dict(roll=3)), ("combo_t4_p-2_h-10", dict(tilt=4, pan=-2, height=-10))]
RACK = [("rack_x+30", (30, 0, 0)), ("rack_x-30", (-30, 0, 0)), ("rack_y+30", (0, 30, 0)), ("rack_y-20", (0, -20, 0)),
        ("rack_yaw+15", (0, 0, 15)), ("rack_yaw-10", (0, 0, -10)), ("rack_x+20_y+20", (20, 20, 0)),
        ("rack_x-15_y+25_yaw+8", (-15, 25, 8)), ("rack_y+10", (0, 10, 0)), ("rack_x+10", (10, 0, 0)),
        ("rack_yaw+5", (0, 0, 5)), ("rack_x+25_y-15_yaw-12", (25, -15, -12))]


def rot(axis, deg):
    a = np.asarray(axis, float) / np.linalg.norm(axis)
    return M.axis_angle(a * deg)


def angles(R):
    x, y, z = R[:, 0], R[:, 1], R[:, 2]
    return {"depression_deg": math.degrees(math.asin(-z[2])), "heading_deg": math.degrees(math.atan2(z[1], z[0])),
            "roll_deg": math.degrees(math.atan2(-x[2], -y[2]))}


def moved(R0, C0, tilt=0.0, pan=0.0, roll=0.0, lateral=0.0, depth=0.0, height=0.0):
    """Physical move at the lens: tilt about the camera's horizontal axis, pan about E z, roll about the optical axis."""
    h = np.cross(R0[:, 2], [0, 0, 1.0])                       # horizontal, perpendicular to the optical axis
    R = rot(h, -tilt) @ R0                                     # sign checked below: + tilt = more depression
    R = rot([0, 0, 1.0], pan) @ R
    R = R @ M.axis_angle(np.array([0, 0, 1.0]) * roll)         # about the camera's own z (optical axis)
    return R, C0 + np.array([depth, lateral, height]) / 1000.0


def main():
    fr = json.loads(M.FRAMES.read_text())
    rig = M.Rig(fr)
    R0, C0 = rig.lens(np.zeros(6))
    a0 = angles(R0)
    sets = [{"name": "nominal", "overrides": {"camera_focal_mm": FOCAL_MM}}]
    truth = {"nominal": {"camera_delta": None, "rack_delta": None}}
    for name, mv in CAM:
        R, C = moved(R0, C0, **mv)
        a = angles(R)
        d = {"tilt_down_deg": a["depression_deg"] - a0["depression_deg"],
             "pan_deg": (a["heading_deg"] - a0["heading_deg"] + 180) % 360 - 180, "roll_deg": a["roll_deg"] - a0["roll_deg"],
             "lateral_m": mv.get("lateral", 0) / 1000, "depth_m": mv.get("depth", 0) / 1000, "height_m": mv.get("height", 0) / 1000}
        if "tilt" in mv:
            assert abs(d["tilt_down_deg"] - mv["tilt"]) < 0.05, (name, d)
        off = rig.offsets_for_lens(R, C)
        R2, C2 = rig.lens(off)
        assert M.rot_angle_deg(R2, R) < 1e-6 and np.linalg.norm(C2 - C) < 1e-9
        sets.append({"name": name, "overrides": {"camera_focal_mm": FOCAL_MM, "camera": dict(zip(["x", "y", "z", "roll", "pitch", "yaw"],
                                                                                                map(float, off)))}})
        truth[name] = {"camera_delta": {k: round(v, 5) for k, v in d.items()}, "rack_delta": None}
    for name, (x, y, yw) in RACK:
        sets.append({"name": name, "overrides": {"camera_focal_mm": FOCAL_MM, "rack": {"x": x / 1000, "y": y / 1000, "yaw": math.radians(yw)}}})
        truth[name] = {"camera_delta": None, "rack_delta": {"x_m": x / 1000, "y_m": y / 1000, "yaw_deg": float(yw)}}
    out = GTC / "results" / "e1"
    (out / "selection_sets.json").write_text(json.dumps(sets, indent=1))
    (out / "selection_truth.json").write_text(json.dumps({"focal_mm": FOCAL_MM, "fx_px": FX, "seed": 0, "truth": truth}, indent=1))
    print(f"{len(sets)} sets (1 nominal, {len(CAM)} camera, {len(RACK)} rack), focal {FOCAL_MM} mm -> results/e1/selection_sets.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
