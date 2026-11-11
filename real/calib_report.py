#!/usr/bin/env python3
"""After the arm calibration: hash the LeRobot calibration JSON and compute the arm's joint scale against the sim
(E_premortem G3; B finding 5).

    python3 -I real/calib_report.py follower      # ~/.cache/huggingface/lerobot/calibration/robots/so101_follower/<ROBOT_ID>.json
    python3 -I real/calib_report.py leader        # .../teleoperators/so101_leader/<TELEOP_ID>.json
    python3 -I real/calib_report.py --file PATH   # any calibration file (dry run)
Real: LeRobot maps the calibrated count range onto -100..100 (RANGE_M100_100), so one normalised unit is
(range_max - range_min) / 4096 * 360 / 200 degrees. Sim: the course maps -100..100 onto the USD joint range
(utils/lerobot_interface.py SO101_USD_MAPPING), (joint_max - joint_min) / 200 degrees per unit. Factor = real / sim
(> 1: the real joint turns further than the sim for the same command). The gripper uses 0..100 in LeRobot and
is reported for reference only. Writes results/robot/calib_<role>_<utc>.json.
"""
import ast
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path

GTC = Path(__file__).resolve().parents[1]
COURSE = GTC.parent / "Sim-to-Real-SO-101-Workshop"
CALIB = Path.home() / ".cache" / "huggingface" / "lerobot" / "calibration"


def env_ids():
    env = dict(re.findall(r"export (\w+)=(\S+)", (COURSE / "docker" / "env").read_text()))
    return env["ROBOT_ID"], env["TELEOP_ID"]


def sim_ranges():
    src = (COURSE / "source" / "sim_to_real_so101" / "utils" / "lerobot_interface.py").read_text()
    m = re.search(r"SO101_USD_MAPPING = (\{.*?\n    \})", src, re.S)
    return ast.literal_eval(m.group(1))


def main(argv):
    robot_id, teleop_id = env_ids()
    if argv and argv[0] == "--file":
        path, role = Path(argv[1]), "file"
    else:
        role = argv[0] if argv else "follower"
        path = CALIB / ("robots/so101_follower" if role == "follower" else "teleoperators/so101_leader") / \
            f"{robot_id if role == 'follower' else teleop_id}.json"
    if not path.exists():
        raise SystemExit(f"STOP: no calibration file {path}; run real/calibrate_arm.sh {role} first")
    cal, sim = json.loads(path.read_text()), sim_ranges()
    rows = {}
    for joint, c in cal.items():
        real = (c["range_max"] - c["range_min"]) / 4096 * 360 / 200
        s = sim.get(joint)
        sim_u = (s["joint_max"] - s["joint_min"]) / 200 if s else None
        rows[joint] = {"range_counts": c["range_max"] - c["range_min"], "range_deg": round((c["range_max"] - c["range_min"]) / 4096 * 360, 1),
                       "real_deg_per_unit": round(real, 4), "sim_deg_per_unit": sim_u,
                       "factor_real_over_sim": round(real / sim_u, 4) if sim_u and joint != "gripper" else None}
    rec = {"utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "role": role, "file": str(path),
           "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "joints": rows}
    out = GTC / "results" / "robot" / f"calib_{role}_{rec['utc'].replace(':', '')}.json"
    if role != "file":
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(rec, indent=1))
    for j, r in rows.items():
        f = r["factor_real_over_sim"]
        print(f"  {j:13s} range {r['range_deg']:6.1f} deg  real {r['real_deg_per_unit']:.3f} vs sim "
              f"{r['sim_deg_per_unit']} deg/unit  factor {f if f is not None else '-'}")
    print(f"sha256 {rec['sha256']}" + ("" if role == "file" else f" -> {out.relative_to(GTC)}"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
