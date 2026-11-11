#!/usr/bin/env python3
"""Write the sweep cell S1_measured_c920 (addendum entry 2): the simulation at the real nominal camera pose S1.

    .venv/bin/python -I sim/make_s1_cell.py [--pose results/poses/s1.json] [--intrinsics config/c920_intrinsics.json] \\
        [--out results/h4/cells_s1.csv]

S1 was set toward the sim's render point by the sled HUD and accepted at its measured pose (X2 mean, pose.py in E).
This cell puts the sim's render prim at that pose: the camera_mount offsets from sim/image_matched_pose.py
Rig.offsets_for_lens (its exact inverse is checked here), plus the C920's measured focal as in H4_c920_measured
(sim/make_h4_cells.py). Same format, checkpoint, task and seeds as S0_nominal: 200 episodes = seeds 0-39 x 5.
The sim camera stays a square-pixel pinhole centred on the image (as in the H4 cells).
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

GTC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))   # sibling modules (python -I skips the script dir)

import image_matched_pose as M  # noqa: E402
import make_h4_cells as H  # noqa: E402
import overrides  # noqa: E402

FRAMES = GTC / "results" / "c1" / "frames_sim.json"


def build(pose_path, intrinsics):
    frames = json.loads(FRAMES.read_text())
    pose = json.loads(Path(pose_path).read_text())
    if "R_E_cv" not in pose:
        raise SystemExit(f"STOP: {pose_path} has no pose in E")
    R, C = np.array(pose["R_E_cv"]), np.array(pose["C_E_m"])
    rig = M.Rig(frames)
    off = rig.offsets_for_lens(R, C)
    R2, C2 = rig.lens(off)
    err_mm, err_deg = 1000 * float(np.linalg.norm(C2 - C)), M.rot_angle_deg(R2, R)
    if err_mm > 1e-3 or err_deg > 1e-4:
        raise SystemExit(f"STOP: offsets do not reproduce the pose ({err_mm:.2e} mm, {err_deg:.2e} deg)")
    inside, margin = M.inside_box(frames, C)
    if not inside:
        raise SystemExit("STOP: the measured lens is outside the sim box")
    (h4,), _ = H.build(intrinsics, measured_only=True)
    focal = json.loads(h4["overrides_json"])["camera_focal_mm"]
    cam = dict(zip(("x", "y", "z", "roll", "pitch", "yaw"), (float(v) for v in off)))
    ov = {"camera": cam, "camera_focal_mm": focal}
    overrides.resolve(ov)
    s0 = H.s0_row()
    psha = hashlib.sha256(Path(pose_path).read_bytes()).hexdigest()
    row = {**{k: s0[k] for k in ("lane", "checkpoint", "task", "n_episodes", "seed_base", "seed_mod", "as_shipped")},
           "cell_id": "S1_measured_c920", "priority": "4", "overrides_json": json.dumps(ov),
           "notes": f"real S1 (X2 mean {Path(pose_path).name}, sha256 {psha[:12]}): lens C_E "
                    f"{[round(float(v), 4) for v in C]} m; C920 focal {focal:.6f} mm; offsets reproduce the pose to "
                    f"{err_mm:.1e} mm / {err_deg:.1e} deg; {H.LIMIT}"}
    assert row["n_episodes"] == "200" and row["seed_base"] == "0" and row["seed_mod"] == "40", row
    return row, {"pose_sha256": psha, "offsets": cam, "focal_mm": focal, "inside_margin_m": margin,
                 "roundtrip_mm": err_mm, "roundtrip_deg": err_deg}


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--pose", default=str(GTC / "results" / "poses" / "s1.json"))
    ap.add_argument("--intrinsics", default=str(GTC / "config" / "c920_intrinsics.json"))
    ap.add_argument("--out", default=str(GTC / "results" / "h4" / "cells_s1.csv"))
    a = ap.parse_args(argv)
    row, info = build(a.pose, a.intrinsics)
    text = H.to_csv([row])
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(text)
    print(f"S1_measured_c920: offsets {json.dumps({k: round(v, 6) for k, v in info['offsets'].items()})}, focal "
          f"{info['focal_mm']:.6f} mm; lens {100 * info['inside_margin_m']:.1f} cm inside the box; round trip "
          f"{info['roundtrip_mm']:.1e} mm / {info['roundtrip_deg']:.1e} deg")
    print(f"wrote {a.out} (sha256 {hashlib.sha256(text.encode()).hexdigest()})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
