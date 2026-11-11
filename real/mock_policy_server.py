#!/usr/bin/env python3
"""A stand-in GR00T policy server for dry runs: the real gr00t PolicyServer (same ZMQ/msgpack protocol) with a
dummy policy that returns a 16-step chunk at the course initial pose. Runs in the real-robot image.

    real/run_real.sh python /workspace/gtc/real/mock_policy_server.py --port 5599 --mode ok|hang|slow
ok: answers at once; hang: never answers get_action (tests the 3 s timeout); slow: answers after 1 s.
"""
import argparse
import sys
import time

import numpy as np

sys.path.insert(0, "/Isaac-GR00T/gr00t/eval/real_robot/SO100")


class DummyPolicy:
    def __init__(self, mode):
        from so101_control import SO101Control
        p = SO101Control.initial_pose
        self.arm = np.array([p[k] for k in ("shoulder_pan.pos", "shoulder_lift.pos", "elbow_flex.pos", "wrist_flex.pos",
                                            "wrist_roll.pos")], np.float32)
        self.mode, self.calls = mode, 0

    def get_action(self, observation, options=None):
        self.calls += 1
        if self.mode == "hang":
            time.sleep(3600)
        if self.mode == "slow":
            time.sleep(1.0)
        return ({"single_arm": np.tile(self.arm, (1, 16, 1)), "gripper": np.zeros((1, 16, 1), np.float32)},
                {"mock_call": self.calls})

    def reset(self, options=None):
        return {}


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=5599)
    ap.add_argument("--mode", default="ok", choices=["ok", "hang", "slow"])
    a = ap.parse_args(argv)
    from gr00t.policy.server_client import PolicyServer
    print(f"mock policy server on {a.port}, mode {a.mode}", flush=True)
    PolicyServer(DummyPolicy(a.mode), port=a.port).run()


if __name__ == "__main__":
    main(sys.argv[1:])
