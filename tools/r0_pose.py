#!/usr/bin/env python3
"""explore-v2: the R0 camera pose (PREREGISTRATION_v1.md section 5) as a sim camera override.

    .venv/bin/python -I tools/r0_pose.py
R0 (course instructions, E_premortem G8): left wall, lens centre 40.0 cm above the foam floor,
27.0 cm from the robot plate's rear face along x, optical axis 45.0 deg below horizontal, panned to aim at
the mat centre. Intrinsics: the sim's D455 camera unchanged (fx = fy = 514.67 px at 640x480, HFOV 63.7 deg).

Inputs, all read from files:
  results/c1/frames_sim.json   floor top (Base panel max z), left wall inner face (Left panel min y),
                               camera_mount local ops and world matrix, the lens prim's pose in the mount
  config/layouts.json          mat centre (mat_env front/back/right/left)
  SO-ARM101-USD.usd (pxr)      plate rear face: base_so101_v2 mesh bbox, placed at the robot root
                               (-0.05, 0, 0), yaw +90 deg (frames_sim robot.root)
Assumptions (not fixed by the R0 text): the lens keeps the sim lens's distance from the left wall
(y = sim lens y), and the camera is level (image x axis horizontal, no roll).

Method: target lens pose T_w_c* -> mount world pose T_w_m* = T_w_c* T_m_c^-1 -> mount local ops
T_p_m* = T_w_p^-1 T_w_m*, with the mount's parent T_w_p = T_w_m0 T_p_m0^-1 -> code offsets as sim/overrides.py
applies them: translate = default + (x, y, z); orient = default * quat_from_euler_xyz(roll, pitch, yaw).
The chain is first checked against every explore-v1 probe (predicted vs read-back lens pose).
Writes config/r0_pose.json.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

GTC = Path(__file__).resolve().parents[1]
COURSE_USD = GTC.parent / "Sim-to-Real-SO-101-Workshop/source/sim_to_real_so101/assets/usd/SO-ARM101-USD.usd"


def q2r(q):
    w, x, y, z = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
                     [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
                     [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)]])


def r2q(R):
    w = math.sqrt(max(0.0, 1 + R[0, 0] + R[1, 1] + R[2, 2])) / 2
    x = math.copysign(math.sqrt(max(0.0, 1 + R[0, 0] - R[1, 1] - R[2, 2])) / 2, R[2, 1] - R[1, 2])
    y = math.copysign(math.sqrt(max(0.0, 1 - R[0, 0] + R[1, 1] - R[2, 2])) / 2, R[0, 2] - R[2, 0])
    z = math.copysign(math.sqrt(max(0.0, 1 - R[0, 0] - R[1, 1] + R[2, 2])) / 2, R[1, 0] - R[0, 1])
    q = np.array([w, x, y, z])
    return q / np.linalg.norm(q)


def quat_from_euler_xyz(roll, pitch, yaw):
    """Isaac Lab isaaclab.utils.math.quat_from_euler_xyz (wxyz)."""
    cy, sy, cr, sr = math.cos(yaw / 2), math.sin(yaw / 2), math.cos(roll / 2), math.sin(roll / 2)
    cp, sp = math.cos(pitch / 2), math.sin(pitch / 2)
    return np.array([cy * cr * cp + sy * sr * sp, cy * sr * cp - sy * cr * sp,
                     cy * cr * sp + sy * sr * cp, sy * cr * cp - cy * sr * sp])


def euler_xyz_from_quat(q):
    """Inverse of quat_from_euler_xyz (q = qz(yaw) qy(pitch) qx(roll))."""
    w, x, y, z = q
    return (math.atan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y)),
            math.asin(max(-1.0, min(1.0, 2 * (w * y - z * x)))),
            math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z)))


def quat_angle(q1, q2):
    """Angle between two rotations, 2 atan2(|v|, |w|) of q1^-1 q2 (stable for tiny angles; acos of the
    matrix trace is not, and the D455 payload carries a 1e-6 scale on one axis)."""
    w1, x1, y1, z1 = q1
    w2, x2, y2, z2 = q2
    w = w1 * w2 + x1 * x2 + y1 * y2 + z1 * z2
    v = (w1 * x2 - x1 * w2 - y1 * z2 + z1 * y2, w1 * y2 + x1 * z2 - y1 * w2 - z1 * x2, w1 * z2 - x1 * y2 + y1 * x2 - z1 * w2)
    return 2 * math.atan2(math.sqrt(sum(c * c for c in v)), abs(w))


def T(R, t):
    M = np.eye(4)
    M[:3, :3], M[:3, 3] = R, t
    return M


def from_usd(m):
    """USD row-major (row-vector) matrix -> 4x4 column-vector transform."""
    m = np.array(m)
    return T(m[:3, :3].T, m[3, :3])


def axis_info(R):
    f = -R[:, 2]                                       # USD camera looks along -Z
    return math.degrees(math.asin(-f[2])), math.degrees(math.atan2(f[1], f[0]))


def plate_rear_x():
    from pxr import Usd, UsdGeom
    st = Usd.Stage.Open(str(COURSE_USD))
    bc = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render])
    r = bc.ComputeWorldBound(st.GetPrimAtPath("/visuals/base/base_so101_v2/mesh")).ComputeAlignedRange()
    return -0.05 - r.GetMax()[1]                       # yaw +90: env x = root x - local y


def mount_local_for(off, t0, q0):
    """What sim/overrides.py writes for a camera override (translate, orient wxyz)."""
    c = {k: off.get(k, 0.0) for k in ("x", "y", "z", "roll", "pitch", "yaw")}
    t = np.array(t0) + [c["x"], c["y"], c["z"]]
    R = q2r(q0) @ q2r(quat_from_euler_xyz(c["roll"], c["pitch"], c["yaw"]))
    return T(R, t)


def main():
    f = json.loads((GTC / "results/c1/frames_sim.json").read_text())
    lay = json.loads((GTC / "config/layouts.json").read_text())["mat_env"]
    cm = f["camera_mount"]
    t0, q0 = cm["local_ops"]["xformOp:translate"], cm["local_ops"]["xformOp:orient"]
    T_w_m0 = from_usd(cm["world_usd"]["matrix_row_major_usd"])
    T_m_c = from_usd(f["camera_external_D455"]["camera_in_mount"]["matrix_row_major_usd"])
    T_w_p = T_w_m0 @ np.linalg.inv(mount_local_for({}, t0, q0))
    T_w_c0 = from_usd(f["camera_external_D455"]["world_usd"]["matrix_row_major_usd"])
    err0 = np.abs(T_w_p @ mount_local_for({}, t0, q0) @ T_m_c - T_w_c0).max()

    # 1. validate the chain on the explore-v1 probes (seed 0 rows; read-back lens pose after reset)
    print("1. chain check: predicted vs read-back lens pose (explore-v1 probes, seed 0)")
    print(f"   nominal rebuild from frames_sim: max matrix error {err0:.2e}")
    worst_mm = worst_deg = 0.0
    for l in open(GTC / "results/explore_v1/probe_explore_v1.jsonl"):
        r = json.loads(l)
        pred = T_w_p @ mount_local_for(r["resolved"]["camera"], t0, q0) @ T_m_c
        ce = r["readback"]["camera_external"]
        dp = 1000 * np.linalg.norm(pred[:3, 3] - ce["pos"])
        da = math.degrees(quat_angle(r2q(pred[:3, :3]), ce["quat_wxyz"]))
        worst_mm, worst_deg = max(worst_mm, dp), max(worst_deg, da)
        print(f"   {r['set']:24s} position {dp:.4f} mm, rotation {da:.4f} deg")
    print(f"   worst: {worst_mm:.4f} mm, {worst_deg:.4f} deg")

    # 2. R0 target from the written numbers
    floor_z = f["lightbox_panels"]["Base"]["world_bbox_max"][2]
    wall_y = f["lightbox_panels"]["Left"]["world_bbox_min"][1]
    rear_x = plate_rear_x()
    mat_c = ((lay["front_x"] + lay["back_x"]) / 2, (lay["right_y"] + lay["left_y"]) / 2)
    lens_y = T_w_c0[1, 3]
    c = np.array([rear_x + 0.270, lens_y, floor_z + 0.400])
    head = math.atan2(mat_c[1] - c[1], mat_c[0] - c[0])
    tilt = math.radians(45.0)
    fwd = np.array([math.cos(tilt) * math.cos(head), math.cos(tilt) * math.sin(head), -math.sin(tilt)])
    x_c = np.cross(fwd, [0, 0, 1])
    x_c /= np.linalg.norm(x_c)
    z_c = -fwd
    y_c = np.cross(z_c, x_c)
    T_w_cR0 = T(np.column_stack([x_c, y_c, z_c]), c)
    print("\n2. R0 target (env frame, m)")
    print(f"   foam floor top z {floor_z:.4f} (Base panel); left wall inner face y {wall_y:.4f} (Left panel)")
    print(f"   plate rear face x {rear_x:.4f} (base_so101_v2 mesh); mat centre ({mat_c[0]:.4f}, {mat_c[1]:.4f})")
    print(f"   lens = ({c[0]:.4f}, {c[1]:.4f}, {c[2]:.4f}): x = rear face + 0.270, z = floor + 0.400, "
          f"y = sim lens y ({wall_y - c[1]:.4f} m from the wall, assumption)")
    print(f"   axis 45.0 deg down, heading {math.degrees(head):.2f} deg (toward the mat centre), level (no roll)")
    t_ground = (c[2] - 0.035) / math.tan(tilt)
    hit = c[:2] + t_ground * np.array([math.cos(head), math.sin(head)])
    print(f"   the axis meets the mat top (z 0.035) at ({hit[0]:.4f}, {hit[1]:.4f}), "
          f"{100 * np.linalg.norm(hit - mat_c):.1f} cm past the mat centre (40 cm and 45 deg cannot both hit it)")
    n_h, n_d = axis_info(T_w_c0[:3, :3])
    print(f"   sim nominal for comparison: lens ({T_w_c0[0, 3]:.4f}, {T_w_c0[1, 3]:.4f}, {T_w_c0[2, 3]:.4f}), "
          f"axis {n_h:.2f} deg down, heading {n_d:.2f} deg")

    # 3. invert the chain to code offsets
    T_p_m = np.linalg.inv(T_w_p) @ T_w_cR0 @ np.linalg.inv(T_m_c)
    d = T_p_m[:3, 3] - np.array(t0)
    dq = r2q(q2r(q0).T @ T_p_m[:3, :3])
    roll, pitch, yaw = euler_xyz_from_quat(dq)
    ov = {"camera": {"x": float(d[0]), "y": float(d[1]), "z": float(d[2]),
                     "roll": float(roll), "pitch": float(pitch), "yaw": float(yaw)}}
    back = T_w_p @ mount_local_for(ov["camera"], t0, q0) @ T_m_c
    b_down, b_head = axis_info(back[:3, :3])
    print("\n3. code offsets (sim/overrides.py camera keys; translate in the mount's parent frame, m; rotation rad)")
    print("   " + json.dumps({k: round(v, 6) for k, v in ov["camera"].items()}))
    print(f"   = translate {100 * d[0]:+.2f}/{100 * d[1]:+.2f}/{100 * d[2]:+.2f} cm, roll {math.degrees(roll):+.2f}, "
          f"pitch {math.degrees(pitch):+.2f}, yaw {math.degrees(yaw):+.2f} deg (code units)")
    print(f"   forward check: lens ({back[0, 3]:.4f}, {back[1, 3]:.4f}, {back[2, 3]:.4f}), axis {b_down:.2f} deg down, "
          f"heading {b_head:.2f} deg, image-x tilt {math.degrees(math.asin(back[2, 0])):.3f} deg")
    out = {"note": "explore-v2: added after sweep v1 and explore-v1, not part of prereg-v1",
           "definition": "PREREGISTRATION_v1.md section 5 R0; E_premortem G8",
           "assumptions": ["lens y = sim lens y (same distance from the left wall)", "level camera (no roll)",
                           "intrinsics: the sim D455 camera unchanged (focal 1.93 mm, horizontalAperture 2.4 mm)"],
           "inputs": {"floor_top_z": floor_z, "left_wall_y": wall_y, "plate_rear_x": rear_x, "mat_centre": mat_c},
           "target_lens_env": c.tolist(), "target_axis_deg_below_horizontal": 45.0,
           "target_heading_deg": math.degrees(head), "overrides": ov,
           "chain_check_worst": {"mm": worst_mm, "deg": worst_deg}}
    (GTC / "config/r0_pose.json").write_text(json.dumps(out, indent=1))
    print("\nwrote config/r0_pose.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
