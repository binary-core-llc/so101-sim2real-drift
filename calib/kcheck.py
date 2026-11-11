#!/usr/bin/env python3
"""K-check (B 4.9, E V30): where the real jaw tip lands for 5 sim joint configurations, read on the sled's grid.

    .venv/bin/python -I calib/kcheck.py poses [--hover-mm 3]      # host: FK/IK from the course USD
    real/kcheck.sh                                                # robot (container): 5 poses, the operator reads
    .venv/bin/python -I calib/kcheck.py report [RUN.json]         # host: delta per pose, pan fit, verdict
    .venv/bin/python -I calib/kcheck.py run --mock                # dry run of the robot part, nothing moves
Order on Nov 5: sled measured into config/board_in_E.json -> `poses` (again: the hover height uses its h_K) -> rack
and vials off the mat, sled seated (paper test on both lobes), door open -> real/kcheck.sh -> `report`.

poses: forward kinematics of SO-ARM101-USD.usd (course repo @ ce807d9): base at the Isaac readback root pose
(results/c1/frames_sim.json robot.root), each revolute joint T_b1 = T_b0 * T(localPos0, localRot0) * Rz(q) *
T(localPos1, localRot1)^-1, checked against the Isaac body readback in the same file (stops if > 1 mm / 0.1 deg).
Normalised values <-> sim degrees exactly as the course (utils/lerobot_interface.py SO101_USD_MAPPING, read from
the file). Jaw tip = midpoint of the fixed jaw's end vertex (wrist_roll_follower mesh, lowest along the gripper
axis) and the moving jaw's end vertex, gripper at 0 (closed, as the course initial pose); wrist roll fixed at the
course initial pose (so101_control.py initial_pose). Each target is solved (damped least squares) for the tip
H mm above the board top (z of T_E_K) with the gripper axis pointing down if reachable, and again 30 mm higher
(the pre-pose). Every mesh vertex of the arm beyond the shoulder (subsampled; the shoulder only pans) must stay
>= H - 1 mm above the board at the hover and
>= 10 mm along the moves between poses (cosine interpolation of the normalised values, as the course moves).
Writes config/kcheck_poses.json. Without config/board_in_E.json it uses the CAD sled datums and a provisional h_K
(marked provisional; `run` refuses it).

run (real-robot container, course SO101Control): connect (course initial pose) -> per pose: Enter -> pre-pose
(3 s) -> Enter -> hover (2 s; q or space stops the move) -> joints read back -> the operator types the reading ->
back up to the pre-pose. End: course initial pose, then the course disconnect (home pose, torque off).
Reading = the board point straight below the jaw tip, in mm, in board coordinates: x from grid column line 0 (the
grid edge nearest the robot) toward the back wall, y from grid row line 0 (the grid edge nearest the camera wall)
toward the RIGHT wall. Squares are 30 mm: count whole squares, add the steel-ruler reading from the last line.
Writes results/robot/kcheck_<utc>.json.

report: reading -> E via config/board_in_E.json; per pose delta (real - sim) in x, y, radius and bearing about
the pan axis; fit of the pan-joint delta (the bearing delta in the joint's sign) = (s - 1) * theta_sim + z0 (pan
scale s, pan zero offset z0 in sim joint degrees, at theta_sim = 0); the pan scale
the calibration predicts (calib range / 4096 * 360 / 200 vs the sim's 1.1 deg per unit). Verdict on the largest
|delta xy| (B 4.9): < 5 mm registered; 5-15 mm report it and run the G3_joint_scale cell; > 15 mm recalibrate
(course procedure) before any trial. Writes results/robot/kcheck_<utc>_report.json.
"""
import argparse
import ast
import datetime as dt
import hashlib
import json
import math
import re
import select
import subprocess
import sys
import termios
import time
import tty
from pathlib import Path

import numpy as np

GTC = Path(__file__).resolve().parents[1]
COURSE = GTC.parent / "Sim-to-Real-SO-101-Workshop"
USD = COURSE / "source/sim_to_real_so101/assets/usd/SO-ARM101-USD.usd"
IFACE = COURSE / "source/sim_to_real_so101/utils/lerobot_interface.py"
CONTROL = COURSE / "docker/real/scripts/so101_control.py"
FRAMES = GTC / "results/c1/frames_sim.json"
BOARD = GTC / "config/board_in_E.json"
POSES = GTC / "config/kcheck_poses.json"
OUT = GTC / "results/robot"
CALIB = Path("/root/.cache/huggingface/lerobot/calibration/robots/so101_follower")   # inside the container
COURSE_SCRIPTS = Path("/Isaac-GR00T/gr00t/eval/real_robot/SO100")

NAMES = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]
USD_JOINTS = ["Rotation", "Pitch", "Elbow", "Wrist_Pitch", "Wrist_Roll", "Jaw"]
BODIES = ["base", "shoulder", "upper_arm", "lower_arm", "wrist", "gripper", "jaw"]
GRID_MM = (240.0, 180.0)            # 8 x 6 squares of 30 mm (docs/charuco_board.json)
GRID_MARGIN_MM = 5.0                # targets sit >= 15 mm inside the grid; 5 mm is left for the measured sled
PRE_MM, PATH_CLEAR_MM, LIMIT_N = 30.0, 10.0, 95.0
CAD_SLED = {"method": "sled", "d_x_mm": 101.1, "d_y_mm": 89.2, "yaw_deg": 0.0,
            "h_K_mm": 10.8, "_h_K": "provisional: mat 6.0 + foam board 4.7 + print, robot on the foam floor"}
# Targets in E (B 4.9). The board grid covers about x 0.100-0.340, y -0.070-0.110 (B 4.2), so targets off the grid
# are moved along their bearing from the pan axis (-0.0269, 0.0208) to 15 mm inside it (or to the nearest grid point).
TARGETS = [
    ("rack_bearing", (0.139, 0.095), "rack centre (0.24, 0.14) is off the grid: same bearing (+24.1 deg), 15 mm "
                                     "inside row line 0"),
    ("vial_2", (0.230, 0.000), "default vial_2 (frames_sim objects_after_reset), on the grid"),
    ("vial_1_bearing", (0.166, -0.055), "vial_1 (0.23, -0.08) is 10 mm past row line 6: same bearing (-21.4 deg), "
                                        "15 mm inside"),
    ("vial_3_side", (0.115, -0.055), "vial_3 (0.23, -0.16) is off the grid and its bearing (-35.1 deg) misses it: "
                                     "15 mm inside the nearest grid corner (bearing -28.1 deg)"),
    ("straight_far", (0.280, 0.0208), "straight ahead along the pan axis line, far reach (the gripper can't point "
                                      "straight down beyond about x 0.25: wrist_flex limit)"),
]


def utc():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H%M%S+0000")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def course_commit():
    r = subprocess.run(["git", "-C", str(COURSE), "rev-parse", "--short=7", "HEAD"], capture_output=True, text=True)
    return r.stdout.strip() or "unknown"


def course_dict(path, name):
    """A literal dict assigned in a course file (class attribute or module/class constant)."""
    for n in ast.walk(ast.parse(Path(path).read_text())):
        if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", None) == name:
            return ast.literal_eval(n.value), n.lineno
    raise SystemExit(f"STOP: {name} not found in {path}")


def n2deg(n, mapping):
    """Course get_mapped_actions_vectorized: first 5 joints -100..100, gripper 0..100 -> USD joint range (deg)."""
    out = []
    for k, v in zip(NAMES, n):
        lo, hi = mapping[k]["joint_min"], mapping[k]["joint_max"]
        out.append(lo + ((v + 100) / 200 if k != "gripper" else v / 100) * (hi - lo))
    return np.array(out)


# ---------------------------------------------------------------- kinematics (host, pxr)
def q2r(q):
    w, x, y, z = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
                     [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
                     [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)]])


def T(R=np.eye(3), t=(0, 0, 0)):
    M = np.eye(4)
    M[:3, :3], M[:3, 3] = R, t
    return M


def Rz(rad):
    c, s = math.cos(rad), math.sin(rad)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


class Arm:
    """The course USD's joint chain and visual meshes (body-local), placed at the Isaac root pose."""

    def __init__(self, frames):
        from pxr import Usd, UsdGeom
        st = Usd.Stage.Open(str(USD))
        self.joints = []
        for j in USD_JOINTS:
            p = st.GetPrimAtPath(f"/so101_new_calib/joints/{j}")
            g = lambda a: p.GetAttribute(a).Get()
            q = lambda v: (v.GetReal(), *v.GetImaginary())
            if g("physics:axis") != "Z":
                raise SystemExit(f"STOP: joint {j} axis {g('physics:axis')}, this FK handles Z only")
            self.joints.append((T(q2r(q(g("physics:localRot0"))), g("physics:localPos0")),
                                np.linalg.inv(T(q2r(q(g("physics:localRot1"))), g("physics:localPos1")))))
        root = frames["robot"]["root"]
        self.T_base = T(q2r(root["quat_wxyz"]), root["pos"])
        xc = UsdGeom.XformCache()
        self.mesh = {}
        for b in BODIES[1:]:
            pts = []
            for p in Usd.PrimRange(st.GetPrimAtPath(f"/visuals/{b}")):
                if p.GetTypeName() == "Mesh":
                    v = np.array(UsdGeom.Mesh(p).GetPointsAttr().Get())
                    M = np.array(xc.GetLocalToWorldTransform(p))     # /visuals/<body> is the body frame
                    w = v @ M[:3, :3] + M[3, :3]
                    pts.append(w)
                    if p.GetPath().pathString.endswith("wrist_roll_follower_so101_v1/mesh"):
                        self.fixed_tip = w[np.argmin(w[:, 2])]              # gripper frame: jaw points along -z
                    if p.GetPath().pathString.endswith("moving_jaw_so101_v1/mesh"):
                        jaw_pts = w
            self.mesh[b] = np.concatenate(pts)
        self.jaw_pts = jaw_pts
        self.sub = {b: m[::40] for b, m in self.mesh.items() if b != "shoulder"}   # the shoulder only pans

    def fk(self, q_rad):
        out, M = {"base": self.T_base}, self.T_base
        for (A, Binv), q, b in zip(self.joints, q_rad, BODIES[1:]):
            M = M @ A @ T(Rz(q)) @ Binv
            out[b] = M
        return out

    def moving_tip(self, q_jaw):
        """The moving jaw's end vertex: lowest along the gripper axis (-z of the gripper frame) at this jaw angle."""
        A, Binv = self.joints[5]
        M = A @ T(Rz(q_jaw)) @ Binv                                   # jaw frame in the gripper frame
        g = self.jaw_pts @ M[:3, :3].T + M[:3, 3]
        return self.jaw_pts[np.argmin(g[:, 2])]

    def tip(self, F, jaw_vertex):
        a = F["gripper"] @ np.r_[self.fixed_tip, 1]
        b = F["jaw"] @ np.r_[jaw_vertex, 1]
        return (a[:3] + b[:3]) / 2, a[:3], b[:3]

    def min_z(self, F, bodies=None):
        return min(float((self.sub[b] @ F[b][:3, :3].T + F[b][:3, 3])[:, 2].min()) for b in (bodies or self.sub))


def validate_fk(arm, frames):
    """FK at the readback joint angles vs the Isaac body poses (results/c1/frames_sim.json)."""
    r = frames["robot"]
    order = [r["joint_names"].index(j) for j in USD_JOINTS]
    F = arm.fk(np.array(r["joint_pos_rad"])[order])
    worst_mm, worst_deg = 0.0, 0.0
    for b in BODIES:
        P = r["bodies"][b]
        R = q2r(P["quat_wxyz"])
        worst_mm = max(worst_mm, 1000 * float(np.linalg.norm(F[b][:3, 3] - np.array(P["pos"]))))
        c = (np.trace(R.T @ F[b][:3, :3]) - 1) / 2
        worst_deg = max(worst_deg, math.degrees(math.acos(max(-1.0, min(1.0, c)))))
    return {"max_pos_err_mm": round(worst_mm, 4), "max_rot_err_deg": round(worst_deg, 4),
            "against": "results/c1/frames_sim.json robot.bodies (Isaac readback after reset + 10 warm-up steps)"}


def board_T(board_path):
    sys.path.insert(0, str(GTC / "calib"))
    import charuco as C
    if Path(board_path).exists():
        T_E_K, b = C.board_in_E(board_path)
        return T_E_K, b, False, sha(board_path)
    R = C.Rz(CAD_SLED["yaw_deg"]) @ np.diag([1.0, -1.0, -1.0])
    o = (-0.0011 + CAD_SLED["d_x_mm"] / 1000, 0.0208 + CAD_SLED["d_y_mm"] / 1000, 0.0301 + CAD_SLED["h_K_mm"] / 1000)
    return C.T(R, o), CAD_SLED, True, None


def solve(arm, mapping, target, fixed_n, jaw_vertex, seeds):
    """Normalised (pan, lift, elbow, wrist_flex) putting the tip on target with the gripper axis down (if reachable).
    Damped least squares, numeric Jacobian; residual = tip error (mm) and axis error (deg, weight 0.1 mm/deg), so
    the tip position wins where the wrist_flex limit (|n| <= 95) stops the gripper from pointing straight down."""
    def res(n4):
        n = np.r_[n4, fixed_n]
        F = arm.fk(np.radians(n2deg(n, mapping)))
        tip = arm.tip(F, jaw_vertex)[0]
        axis = F["gripper"][:3, :3] @ np.array([0, 0, -1.0])
        return np.r_[1000 * (tip - target), 0.1 * np.degrees(axis - np.array([0, 0, -1.0]))]

    best = None
    for s in seeds:
        n, lam = np.array(s, float), 1e-2
        r = res(n)
        for _ in range(200):
            J = np.stack([(res(n + e) - r) / 1e-3 for e in np.eye(4) * 1e-3], axis=1)
            H, g = J.T @ J, J.T @ r
            step = np.linalg.solve(H + lam * np.diag(np.diag(H) + 1e-9), -g)
            n2 = np.clip(n + step, -LIMIT_N, LIMIT_N)
            r2 = res(n2)
            if r2 @ r2 < r @ r:
                n, r, lam = n2, r2, max(lam / 3, 1e-6)
                if np.linalg.norm(step) < 1e-6:
                    break
            else:
                lam *= 4
                if lam > 1e8:
                    break
        pos_mm, tilt = float(np.linalg.norm(r[:3])), float(np.linalg.norm(r[3:])) * 10
        key = (pos_mm > 0.1, round(tilt, 1), float(np.abs(n - np.array(seeds[0])).sum()))
        if best is None or key < best[0]:
            best = (key, n, pos_mm)
    _, n, pos_mm = best
    n6 = np.r_[n, fixed_n]
    F = arm.fk(np.radians(n2deg(n6, mapping)))
    axis = F["gripper"][:3, :3] @ np.array([0, 0, -1.0])
    tilt = math.degrees(math.acos(max(-1.0, min(1.0, -axis[2]))))
    return n6, pos_mm, tilt, F


def cos_path(a, b, steps=31):
    return [a + (1 - math.cos(math.pi * i / steps)) / 2 * (b - a) for i in range(steps + 1)]


def cmd_poses(a):
    frames = json.loads(FRAMES.read_text())
    mapping, map_line = course_dict(IFACE, "SO101_USD_MAPPING")
    initial, init_line = course_dict(CONTROL, "initial_pose")
    init_n = np.array([initial[f"{k}.pos"] for k in NAMES])
    arm = Arm(frames)
    val = validate_fk(arm, frames)
    print(f"FK vs Isaac readback: {val['max_pos_err_mm']} mm, {val['max_rot_err_deg']} deg (all 7 bodies)")
    if val["max_pos_err_mm"] > 1.0 or val["max_rot_err_deg"] > 0.1:
        raise SystemExit("STOP: the FK does not reproduce the Isaac readback")
    T_E_K, board, provisional, board_sha = board_T(a.board_in_e)
    K_E = np.linalg.inv(T_E_K)
    z_board = float(T_E_K[2, 3])
    fixed_n = init_n[4:].copy()
    fixed_n[1] = 0.0                                                   # gripper closed (course initial pose: 0)
    jaw_vertex = arm.moving_tip(math.radians(n2deg(np.r_[init_n[:4], fixed_n], mapping)[5]))
    seeds = [init_n[:4], np.array([0, 0, 0, 80.0]), np.array([0, -20, 40, 60.0]), np.array([0, 20, -20, 90.0])]
    H = a.hover_mm / 1000
    pan_xy = arm.fk(np.zeros(6))["shoulder"][:2, 3]
    poses, ok_all = [], True
    for name, (x, y), why in TARGETS:
        seeds_t = [s.copy() for s in seeds]
        for s in seeds_t:                                              # pan seed: the target's bearing
            s[0] = math.degrees(math.atan2(y - pan_xy[1], x - pan_xy[0])) / 1.1
        out = {"name": name, "why": why, "target_E_xy": [x, y]}
        for tag, dz in (("hover", H), ("pre", H + PRE_MM / 1000)):
            z = z_board + dz
            for _ in range(4):                                         # keep the lowest arm point dz above the board
                n6, pos_mm, tilt, F = solve(arm, mapping, np.array([x, y, z]), fixed_n, jaw_vertex, seeds_t)
                clear = arm.min_z(F) - z_board
                if clear >= dz - 0.0005:
                    break
                z += dz - clear
            tip, ftip, mtip = arm.tip(F, jaw_vertex)
            out[tag] = {"n": [round(float(v), 4) for v in n6], "sim_deg": [round(float(v), 3) for v in n2deg(n6, mapping)],
                        "tip_E": [round(float(v), 5) for v in tip], "tip_fixed_jaw_E": [round(float(v), 5) for v in ftip],
                        "tip_moving_jaw_E": [round(float(v), 5) for v in mtip], "ik_pos_err_mm": round(pos_mm, 3),
                        "gripper_tilt_from_down_deg": round(tilt, 2), "lowest_arm_point_above_board_mm": round(1000 * clear, 2)}
            seeds_t = [n6[:4]] + seeds_t
        k = K_E @ np.r_[out["hover"]["tip_E"], 1]
        out["tip_board_mm"] = [round(1000 * float(k[0]), 1), round(1000 * float(k[1]), 1)]
        out["on_grid"] = bool(GRID_MARGIN_MM <= out["tip_board_mm"][0] <= GRID_MM[0] - GRID_MARGIN_MM and
                              GRID_MARGIN_MM <= out["tip_board_mm"][1] <= GRID_MM[1] - GRID_MARGIN_MM)
        if out["hover"]["ik_pos_err_mm"] > 0.5 or out["hover"]["lowest_arm_point_above_board_mm"] < a.hover_mm - 1:
            out["problem"] = "IK did not reach the hover point"
        poses.append(out)
    # moves: initial -> pre1 -> hover1 -> pre1 -> pre2 ... -> pre5 -> initial; lowest arm point along each move
    seq = [("initial", init_n)]
    for p in poses:
        seq += [(f"{p['name']}:pre", np.array(p["pre"]["n"])), (f"{p['name']}:hover", np.array(p["hover"]["n"])),
                (f"{p['name']}:pre", np.array(p["pre"]["n"]))]
    seq.append(("initial", init_n))
    moves = []
    for (na, qa), (nb, qb) in zip(seq, seq[1:]):
        low = min(arm.min_z(arm.fk(np.radians(n2deg(q, mapping)))) for q in cos_path(qa, qb, 15)) - z_board
        need = (a.hover_mm - 1) if nb.endswith("hover") or na.endswith("hover") else PATH_CLEAR_MM
        moves.append({"from": na, "to": nb, "lowest_arm_point_above_board_mm": round(1000 * low, 2),
                      "ok": bool(1000 * low >= need)})
    for p in poses:
        h = p["hover"]
        flag = "" if p["on_grid"] and "problem" not in p else "  <-- " + ("off the grid" if not p["on_grid"] else p["problem"])
        print(f"{p['name']:15s} tip E ({h['tip_E'][0]:.3f}, {h['tip_E'][1]:.3f}, {h['tip_E'][2]:.4f})  board "
              f"({p['tip_board_mm'][0]:.1f}, {p['tip_board_mm'][1]:.1f}) mm  tilt {h['gripper_tilt_from_down_deg']:.1f} deg  "
              f"lowest {h['lowest_arm_point_above_board_mm']:.1f} mm  n {h['n']}{flag}")
        ok_all &= p["on_grid"] and "problem" not in p
    bad = [m for m in moves if not m["ok"]]
    for m in bad:
        print(f"MOVE TOO LOW: {m['from']} -> {m['to']}: lowest arm point {m['lowest_arm_point_above_board_mm']} mm")
    ok_all &= not bad
    rec = {"schema": "gtc kcheck poses v1", "created_utc": utc(), "provisional": provisional,
           "hover_mm": a.hover_mm, "pre_mm": PRE_MM, "board_in_E": board, "board_in_E_sha256": board_sha,
           "T_E_K": T_E_K.round(6).tolist(), "board_top_z_E": round(z_board, 5), "fk_validation": val,
           "pan_axis_E": [round(float(v), 5) for v in arm.fk(np.zeros(6))["shoulder"][:3, 3]],
           "pan_joint_z_up": int(round(float((arm.T_base @ arm.joints[0][0])[2, 2]))),   # -1: + pan turns clockwise
           "usd": str(USD.relative_to(GTC.parent)), "usd_sha256": sha(USD), "course_commit": course_commit(),
           "mapping": f"{IFACE.relative_to(GTC.parent)}:{map_line} SO101_USD_MAPPING", "mapping_values": mapping,
           "initial_pose": f"{CONTROL.relative_to(GTC.parent)}:{init_line}", "initial_n": init_n.tolist(),
           "fixed": {"wrist_roll_n": float(fixed_n[0]), "gripper_n": float(fixed_n[1])},
           "tip": "midpoint of the fixed jaw's end vertex (wrist_roll_follower_so101_v1, lowest along gripper -z) and "
                  "the moving jaw's end vertex (moving_jaw_so101_v1, lowest along gripper -z at gripper n 0)",
           "method": "damped least squares on normalised pan/lift/elbow/wrist_flex (|n| <= 95), tip on target and "
                     "gripper axis down; target raised until the lowest arm vertex (every 40th) is the hover above "
                     "the board; moves checked with the course's cosine interpolation of normalised values",
           "joint_order": NAMES, "poses": poses, "moves": moves, "all_ok": bool(ok_all)}
    out = Path(a.out)
    out.write_text(json.dumps(rec, indent=1))
    print(f"wrote {out}" + ("  (PROVISIONAL: no config/board_in_E.json; `run` refuses it)" if provisional else ""))
    return 0 if ok_all else 2


# ---------------------------------------------------------------- robot (container)
class Keys:
    """q or space stops a move; single keys in cbreak mode, only while a move runs."""

    def __enter__(self):
        self.fd, self.old = sys.stdin.fileno(), None
        if sys.stdin.isatty():
            self.old = termios.tcgetattr(self.fd)
            tty.setcbreak(self.fd)
        return self

    def hit(self):
        if self.old is None or not select.select([sys.stdin], [], [], 0)[0]:
            return False
        return sys.stdin.read(1) in ("q", " ")

    def __exit__(self, *_):
        if self.old is not None:
            termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old)


class RealArm:
    def __init__(self, port, robot_id):
        sys.path.insert(0, str(COURSE_SCRIPTS))
        from lerobot.robots.so101_follower import SO101FollowerConfig
        from so101_control import SetupConfig, SO101Control
        self.c = SO101Control(SetupConfig(robot=SO101FollowerConfig(port=port, id=robot_id)))

    def connect(self):
        self.c.connect()                        # course: initial pose over 3 s

    def obs(self):
        o = self.c.robot.get_observation()
        return np.array([float(o[f"{k}.pos"]) for k in NAMES])

    def send(self, n):
        self.c.robot.send_action({f"{k}.pos": float(v) for k, v in zip(NAMES, n)})

    def disconnect(self):
        self.c.disconnect()                     # course: home pose over 3 s, then torque off


class MockArm:
    def __init__(self, init_n):
        self.n = np.array(init_n, float)

    def connect(self):
        print("[mock] connect: course initial pose")

    def obs(self):
        return self.n.copy()

    def send(self, n):
        self.n = np.array(n, float)

    def disconnect(self):
        print("[mock] disconnect: course home pose, torque off")


def move(arm, target, duration, fps=30.0):
    """The course move_to_pose (cosine ease from the current reading), stoppable with q/space. Returns 'stopped'."""
    start, target = arm.obs(), np.array(target, float)
    steps = int(duration * fps)
    with Keys() as k:
        for i in range(1, steps + 1):
            if k.hit():
                return "stopped"
            arm.send(start + (1 - math.cos(math.pi * i / steps)) / 2 * (target - start))
            time.sleep(1.0 / fps)
    return None


def ask(prompt, mock_answers):
    if mock_answers is not None:
        v = mock_answers.pop(0) if mock_answers else ""
        print(f"{prompt}{v}")
        return v
    if sys.stdin.isatty():                      # an Enter typed during a move must not confirm the next step
        termios.tcflush(sys.stdin.fileno(), termios.TCIFLUSH)
    return input(prompt).strip()


def ask_reading(prompt, mock_answers):
    """'x y' (mm, optional 'touch') or 'skip'; asks again on anything else."""
    while True:
        parts = ask(prompt, mock_answers).split()
        if parts[:1] == ["skip"]:
            return None
        try:
            x, y = float(parts[0]), float(parts[1])
            if set(parts[2:]) <= {"touch"} and 0 <= x <= GRID_MM[0] + 30 and 0 <= y <= GRID_MM[1] + 30:
                return x, y, "touch" in parts[2:]
        except (IndexError, ValueError):
            pass
        print("  type x and y in mm (e.g. '131.5 108'), optionally 'touch', or 'skip'")
        if mock_answers is not None and not mock_answers:
            return None


def cmd_run(a):
    poses = json.loads(Path(a.poses).read_text())
    if poses["provisional"] and not a.mock:
        raise SystemExit("STOP: config/kcheck_poses.json is provisional (no board_in_E.json when it was made); "
                         "measure the sled, then run `kcheck.py poses` again")
    if not poses["all_ok"] and not a.mock:
        raise SystemExit("STOP: kcheck_poses.json has a pose off the grid or a move too low (see `poses` output)")
    rec = {"schema": "gtc kcheck run v1", "utc": utc(), "mock": a.mock, "poses_sha256": sha(a.poses), "poses_file": poses,
           "hover_mm": poses["hover_mm"], "results": []}
    if a.mock:
        arm = MockArm(poses["initial_n"])
        answers = list(a.answers.split(";")) if a.answers is not None else None
    else:
        env = dict(re.findall(r"export (\w+)=(\S+)", Path("/root/env").read_text()))
        rid = env.get("ROBOT_ID", "orange_robot")
        cal = CALIB / f"{rid}.json"
        rec.update({"robot_id": rid, "port": a.port, "calib_file": str(cal), "calib_sha256": sha(cal),
                    "calib": json.loads(cal.read_text())})
        arm, answers = RealArm(a.port, rid), None
    print("K-check: rack and vials off the mat, sled seated (paper test on both lobes), door open, you in the room.\n"
          "Reading: the board point straight below the jaw tip, mm: x from grid column line 0 (robot-side grid edge)\n"
          "toward the back wall, y from grid row line 0 (camera-wall grid edge) toward the RIGHT wall; 30 mm squares.")
    ask("FIRST CONNECT: hand on the arm, 12 V plug within reach (torque comes on before the goal is set). "
        "Enter = connect (the arm rises to the course start pose) ", answers)
    arm.connect()
    try:
        for p in poses["poses"]:
            r = {"name": p["name"], "commanded_hover_n": p["hover"]["n"], "commanded_pre_n": p["pre"]["n"]}
            rec["results"].append(r)
            if ask(f"[{p['name']}] Enter = move above it ({poses['pre_mm']:.0f} mm), s = skip this pose ", answers) == "s":
                r["status"] = "skipped"
                continue
            if move(arm, p["pre"]["n"], 3.0) == "stopped":
                r["status"] = "stopped_on_the_way"
                ask("Stopped. Enter = continue with the next pose ", answers)
                continue
            if ask(f"Enter = descend to the hover ({poses['hover_mm']:g} mm above the board; q or space stops), "
                   "s = skip ", answers) == "s":
                r["status"] = "skipped_above"
                continue
            r["descent"] = move(arm, p["hover"]["n"], 2.0) or "completed"
            time.sleep(0.5)
            r["readback_n"] = [round(float(v), 3) for v in arm.obs()]
            v = ask_reading("Tip reading 'x y' in mm, or 'skip'. If a jaw touches the board, add 'touch' and "
                            "re-check the sled seat (paper test on both lobes) before the next pose: ", answers)
            if v:
                r.update({"reading_board_mm": [v[0], v[1]], "touch": v[2], "status": "read"})
            else:
                r["status"] = "not_read"
            move(arm, p["pre"]["n"], 2.0)
        move(arm, poses["initial_n"], 3.0)
    finally:
        arm.disconnect()                        # from a hover too, the course home move lifts the tip at once (sim)
        out = Path(a.out_dir)
        out.mkdir(parents=True, exist_ok=True)
        path = out / f"kcheck_{rec['utc']}{'_mock' if a.mock else ''}.json"
        path.write_text(json.dumps(rec, indent=1))
        print(f"wrote {path}")
    return 0


# ---------------------------------------------------------------- report (host)
def cmd_report(a):
    runs = sorted(OUT.glob("kcheck_*.json"))
    runs = [r for r in runs if not r.name.endswith(("_report.json", "_mock.json"))] or runs
    path = Path(a.run) if a.run else (runs[-1] if runs else None)
    if path is None:
        raise SystemExit("STOP: no results/robot/kcheck_*.json")
    run = json.loads(path.read_text())
    poses = run["poses_file"]
    T_E_K, board, provisional, board_sha = board_T(a.board_in_e)
    if provisional:
        raise SystemExit("STOP: no config/board_in_E.json: the grid reading can't be put in E")
    if board_sha != poses["board_in_E_sha256"]:
        print("WARNING: config/board_in_E.json changed since the poses were made (sha256 differs)")
    pan, up = np.array(poses["pan_axis_E"][:2]), poses["pan_joint_z_up"]
    rows = []
    for r, p in zip(run["results"], poses["poses"]):
        if r.get("status") != "read":
            rows.append({"name": r["name"], "status": r.get("status")})
            continue
        bx, by = r["reading_board_mm"]
        real = (T_E_K @ np.r_[bx / 1000, by / 1000, 0, 1])[:2]
        sim = np.array(p["hover"]["tip_E"][:2])
        d = 1000 * (real - sim)
        bear = lambda q: math.degrees(math.atan2(q[1] - pan[1], q[0] - pan[0]))
        rows.append({"name": r["name"], "status": "read", "touch": r["touch"], "real_E": real.round(5).tolist(),
                     "sim_E": sim.tolist(), "dx_mm": round(float(d[0]), 1), "dy_mm": round(float(d[1]), 1),
                     "d_mm": round(float(np.linalg.norm(d)), 1),
                     "d_radius_mm": round(1000 * float(np.linalg.norm(real - pan) - np.linalg.norm(sim - pan)), 1),
                     "d_bearing_deg": round(bear(real) - bear(sim), 2),
                     "d_pan_joint_deg": round(up * (bear(real) - bear(sim)), 2),
                     "theta_sim_pan_deg": round(float(p["hover"]["sim_deg"][0]), 2)})
    read = [x for x in rows if x["status"] == "read"]
    fit = None
    if read:
        th = np.array([x["theta_sim_pan_deg"] for x in read])
        db = np.array([x["d_pan_joint_deg"] for x in read])
        if len(read) >= 2 and np.ptp(th) > 5:
            A = np.c_[th, np.ones_like(th)]
            (k, z0), *_ = np.linalg.lstsq(A, db, rcond=None)
            fit = {"pan_scale": round(1 + float(k), 4), "pan_zero_offset_deg": round(float(z0), 2),
                   "rms_deg": round(float(np.sqrt(np.mean((A @ [k, z0] - db) ** 2))), 2), "n": len(read)}
        else:
            fit = {"pan_scale": None, "pan_zero_offset_deg": round(float(db.mean()), 2), "n": len(read),
                   "note": "fewer than 2 poses or pan spread <= 5 deg: offset only"}
    pred = None
    if run.get("calib"):
        c = run["calib"]["shoulder_pan"]
        sim_dpu = (poses["mapping_values"]["shoulder_pan"]["joint_max"] - poses["mapping_values"]["shoulder_pan"]["joint_min"]) / 200
        pred = round(abs(c["range_max"] - c["range_min"]) / 4096 * 360 / 200 / sim_dpu, 4)
    worst = max((x["d_mm"] for x in read), default=None)
    verdict = ("NO READINGS" if worst is None else "REGISTERED (< 5 mm)" if worst < 5 else
               "REPORT: 5-15 mm, a known sim-real kinematic difference; run the G3_joint_scale cell" if worst <= 15 else
               "RECALIBRATE (> 15 mm): course procedure, then repeat the K-check, before any trial")
    for x in rows:
        if x["status"] != "read":
            print(f"{x['name']:15s} {x['status']}")
        else:
            print(f"{x['name']:15s} dx {x['dx_mm']:+6.1f}  dy {x['dy_mm']:+6.1f}  |d| {x['d_mm']:5.1f} mm  "
                  f"radius {x['d_radius_mm']:+5.1f} mm  bearing {x['d_bearing_deg']:+5.2f} deg{'  TOUCH' if x['touch'] else ''}")
    print(f"pan fit: {fit}   calibration-predicted pan scale: {pred}")
    print(f"K-CHECK {verdict}" + (f" (largest |d| {worst} mm)" if worst is not None else ""))
    rep = {"schema": "gtc kcheck report v1", "utc": utc(), "run": str(path), "run_sha256": sha(path),
           "board_in_E_sha256": board_sha, "rows": rows, "pan_fit": fit, "pan_scale_from_calibration": pred,
           "largest_d_mm": worst, "verdict": verdict,
           "thresholds": "B 4.9: < 5 mm registered; 5-15 mm report + G3_joint_scale cell; > 15 mm recalibrate"}
    out = path.with_name(path.stem + "_report.json")
    out.write_text(json.dumps(rep, indent=1))
    print(f"wrote {out}")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("poses")
    p.add_argument("--hover-mm", type=float, default=3.0)
    p.add_argument("--board-in-e", default=str(BOARD))
    p.add_argument("--out", default=str(POSES), help="tests only; the run reads config/kcheck_poses.json")
    p = sp.add_parser("run")
    p.add_argument("--port")
    p.add_argument("--poses", default=str(POSES))
    p.add_argument("--mock", action="store_true", help="nothing moves; no robot")
    p.add_argument("--answers", help="mock only: ';'-separated answers to the prompts")
    p.add_argument("--out-dir", default=str(OUT), help="tests only")
    p = sp.add_parser("report")
    p.add_argument("run", nargs="?")
    p.add_argument("--board-in-e", default=str(BOARD))
    a = ap.parse_args()
    if a.cmd == "run" and not a.mock and not a.port:
        raise SystemExit("STOP: --port (real/kcheck.sh finds it by USB identity)")
    return {"poses": cmd_poses, "run": cmd_run, "report": cmd_report}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
