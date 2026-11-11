#!/usr/bin/env python3
"""Door clearance check (J6, Nov 4): hold the follower at the course home pose with the door closed.

    real/hold_home.sh
Course SO101Control (docker/real/scripts/so101_control.py): connect, the course initial (start) pose over 3 s;
Enter: the course home pose over 3 s, the same move every trial and pilot ends with (SO101Control.disconnect).
The arm holds there until Enter, then the course disconnect (home, torque off). Joint readings printed at each pose.
FIRST CONNECT: keep a hand on the arm and the 12 V plug within reach (torque comes on before the goal is set).
Never press Ctrl+C twice (a second interrupt aborts the home move); the hard stop is the 12 V plug.
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, "/Isaac-GR00T/gr00t/eval/real_robot/SO100")


def joints(control):
    obs = control.robot.get_observation()
    return {k.removesuffix(".pos"): round(float(v), 1) for k, v in obs.items() if k.endswith(".pos")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", required=True)
    a = ap.parse_args()
    from lerobot.robots.so101_follower import SO101FollowerConfig
    from so101_control import SetupConfig, SO101Control
    env = dict(re.findall(r"export (\w+)=(\S+)", Path("/root/env").read_text()))
    control = SO101Control(SetupConfig(robot=SO101FollowerConfig(port=a.port, id=env.get("ROBOT_ID", "orange_robot"))))
    input("Door closed and latched. Hand on the arm, 12 V plug within reach. Enter = connect (the arm rises to the "
          "start pose) ")
    control.connect()
    try:
        print("start pose:", joints(control))
        input("Enter = the course home pose (3 s), the move every trial ends with ")
        control.move_to_home_pose()
        print("home pose:", joints(control))
        input("Holding at home. Does a sheet of paper slide between the arm and the door's inside face? If the arm "
              "presses the door, press Enter now. Enter = torque off (the arm settles to rest) ")
    finally:
        control.disconnect()
        print("torque off")


if __name__ == "__main__":
    main()
