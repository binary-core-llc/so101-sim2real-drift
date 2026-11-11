#!/usr/bin/env python3
"""Pose check (V28-01 follow-up, Nov 6): do the same joint numbers put the real gripper where they put the sim gripper?

    real/run_real.sh python /workspace/gtc/real/pose_check.py --tag L00 [--chunks 6,7,8]

No policy. The arm moves only on Enter, with the operator at the standing spot and a hand near the 12 V plug.
Poses are the sim's own states at the given chunks of the L00 trace (results/sim/trace/L00_nominal.jsonl, rep 0,
LeRobot joint values, the same units the real runner sends): chunk 6 = approach above vial_3, 7 = lower approach,
8 = the sim grasp (gripper kept open at the chunk 7 value, so the jaws do not close). Course SO101Control: connect ->
the course start pose (3 s); each pose by move_to_pose over --duration s; the front and wrist frames and the joints
reached are saved at each; back to the first pose, then the course disconnect
(home pose, torque off). Answer q at any prompt to go home now.
Compare: media/real/posecheck/<tag>/chunk_NNN_{front,wrist}.png against the sim trace frames of the same chunk
(media/sim/trace/L00_nominal_r0/). Never press Ctrl+C twice (a second interrupt aborts the home move).
"""
import argparse
import datetime as dt
import json
import re
import sys
import time
from pathlib import Path

GTC = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(GTC / "calib"), str(GTC / "real"), "/Isaac-GR00T/gr00t/eval/real_robot/SO100"]
import pilot  # noqa: E402  (make_real_control, save_png)
import usbcam  # noqa: E402
import camera_lock  # noqa: E402
from trial_runner import load_joint_map, map_act, map_obs  # noqa: E402

J = ["shoulder_pan.pos", "shoulder_lift.pos", "elbow_flex.pos", "wrist_flex.pos", "wrist_roll.pos", "gripper.pos"]


def lock_check(write):
    try:
        return camera_lock.cmd_apply("all", write=write)
    except SystemExit as e:
        print(e, file=sys.stderr)
        return 2


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="L00")
    ap.add_argument("--trace", default=str(GTC / "results/sim/trace/L00_nominal.jsonl"))
    ap.add_argument("--rep", type=int, default=0)
    ap.add_argument("--chunks", default="6,7,8")
    ap.add_argument("--duration", type=float, default=3.0)
    ap.add_argument("--fourcc", default="MJPG")
    ap.add_argument("--wrist-fourcc", default="MJPG")
    ap.add_argument("--joint-map", help="as trial_runner.py --joint-map: send scale * v + offset; the record also keeps "
                    "the reached values in the policy's units (reached_policy)")
    a = ap.parse_args(argv)
    jmap = load_joint_map(a.joint_map)
    want = [int(c) for c in a.chunks.split(",")]
    rows = {r["chunk"]: r for r in map(json.loads, open(a.trace)) if r.get("rep") == a.rep and r.get("chunk") in want}
    poses = {c: {j: float(rows[c]["joints"][j]) for j in J} for c in want}
    grip_open = max(p["gripper.pos"] for p in poses.values())
    for p in poses.values():
        p["gripper.pos"] = grip_open                              # jaws stay open (no squeeze on anything)
    out_dir = GTC / "media/real/posecheck" / a.tag
    res = GTC / "results/real/posecheck" / f"{a.tag}.jsonl"
    res.parent.mkdir(parents=True, exist_ok=True)
    front, wrist, arm = usbcam.find("front"), usbcam.find("wrist"), usbcam.find("follower")
    if lock_check(write=True) != 0:
        raise SystemExit("STOP: camera lock does not read back (B 2.4)")
    env = dict(re.findall(r"export (\w+)=(\S+)", Path("/root/env").read_text()))
    control = pilot.make_real_control(front["node"], wrist["node"], a.fourcc, a.wrist_fourcc, arm["node"],
                                      env.get("ROBOT_ID", "orange_robot"))
    for c in want:
        print(f"  chunk {c}: " + "  ".join(f"{j.split('.')[0]} {poses[c][j]:6.1f}" for j in J))
    if input("Vials as the sim's L00 (or only vial_3), door closed, hands off. Enter = connect (start pose, 3 s), "
             "q = quit ").strip() == "q":
        return 0
    control.connect()
    reached = []
    try:
        if lock_check(write=False) != 0 and lock_check(write=True) != 0:
            raise SystemExit("STOP: camera lock does not hold after the stream opened")
        for c in want:
            if input(f"Enter = move to sim chunk {c} ({a.duration:.0f} s), q = go home now ").strip() == "q":
                break
            control.move_to_pose(map_act(poses[c], jmap), duration=a.duration)
            reached.append(c)
            time.sleep(0.5)                                       # settle before the frames
            obs = control.robot.get_observation()
            pilot.save_png(out_dir / f"chunk_{c:03d}_front.png", obs["front"])
            pilot.save_png(out_dir / f"chunk_{c:03d}_wrist.png", obs["wrist"])
            got = {j: round(float(obs[j]), 2) for j in J}
            note = input("Where are the jaws relative to vial_3 (e.g. 'centred', '3 cm toward robot, 2 cm toward right "
                         "edge', 'touching mat')? ").strip()
            row = {"utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "tag": a.tag, "chunk": c,
                   "target": poses[c], "reached": got, "operator_note": note,
                   "joint_map": None if not jmap else {"path": a.joint_map, "joints": {k: list(v) for k, v in jmap.items()}},
                   "reached_policy": {j: round(float(v), 2) for j, v in map_obs(got, jmap).items()},
                   "front": str((out_dir / f"chunk_{c:03d}_front.png").relative_to(GTC)),
                   "wrist": str((out_dir / f"chunk_{c:03d}_wrist.png").relative_to(GTC))}
            with open(res, "a") as f:
                f.write(json.dumps(row) + "\n")
            print("  reached: " + "  ".join(f"{j.split('.')[0]} {got[j]:6.1f}" for j in J))
        if len(reached) > 1:                                  # back up the way it came before the home move
            control.move_to_pose(map_act(poses[want[0]], jmap), duration=a.duration)
    finally:
        control.disconnect()                                      # course: home pose over 3 s, then torque off
    print(f"-> {res.relative_to(GTC)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
