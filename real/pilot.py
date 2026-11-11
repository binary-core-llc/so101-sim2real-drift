#!/usr/bin/env python3
"""Real-robot pilot run (unscored, E_premortem V26): the course policy loop with a 3 s policy timeout, a cap and a
stop key. Runs in the real-robot container:

    real/run_real.sh python /workspace/gtc/real/pilot.py --run pilot01 --layout L00 [--note "..."]
Keys (type in this terminal): q or space = stop now; s = success seen (stops); f = safety stop; i = invalid.
Ctrl+C also stops. On every stop the arm goes to the course home pose (SO101Control.disconnect, as the course does).

Same pieces as the course docker/real/scripts/so101_eval.py, unchanged: SO101Control (initial pose on connect, home
pose on disconnect) and So100Adapter (observation -> GR00T input -> 16-step chunk), 30 Hz pacing. Added:
  - cameras and the arm port found only by USB identity (calib/usbcam.py); fourcc MJPG; never an index;
  - the course PolicyClient stores timeout_ms but never applies it: RCVTIMEO/SNDTIMEO = --timeout-s, LINGER 0;
    a timeout stops the run (policy_timeout); the server is pinged before the robot is connected;
  - a cap of --cap-s seconds from the first policy query (the course timeout field is never used);
  - camera lock read back after LeRobot opens the streams (B 2.4), re-applied and logged if it drifted;
  - per-chunk JSONL (latency, actions) and the exact policy inputs saved as keyframes; start joint state (T31).
Writes results/pilot/<run>.json, results/pilot/<run>_chunks.jsonl, media/pilot/<run>/chunk_NNN_{front,wrist}.png.
Exit 0 normal stop (key, cap), 4 policy timeout or server error, 3 STOP before the robot moved.
--mock-robot replays images and moves nothing (dry runs; written to results/dryrun_pilot/).
"""
import argparse
import datetime as dt
import json
import os
import select
import sys
import threading
import time
from pathlib import Path

GTC = Path(__file__).resolve().parents[1]
COURSE_SCRIPTS = Path("/Isaac-GR00T/gr00t/eval/real_robot/SO100")
sys.path.insert(0, str(GTC / "calib"))
sys.path.insert(0, str(COURSE_SCRIPTS))
import usbcam  # noqa: E402

LANG = "Pick up the vial and place it in the yellow rack"
KEYS = {"q": "stop", " ": "stop", "s": "success_seen", "f": "safety_stop", "i": "invalid"}


def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds")


class KeyWatcher(threading.Thread):
    """Reads single keys from the terminal (or lines from a pipe) without blocking the control loop."""

    def __init__(self):
        super().__init__(daemon=True)
        self.event, self.label, self.t = threading.Event(), None, None

    def run(self):
        fd, tty = sys.stdin.fileno(), sys.stdin.isatty()
        old = None
        if tty:
            import termios
            import tty as ttym
            old = termios.tcgetattr(fd)
            ttym.setcbreak(fd)
        try:
            while not self.event.is_set():
                r, _, _ = select.select([sys.stdin], [], [], 0.1)
                if not r:
                    continue
                ch = os.read(fd, 1).decode(errors="ignore") if tty else (sys.stdin.readline() or "\n")[:1]
                if ch in KEYS:
                    self.label, self.t = KEYS[ch], time.time()
                    self.event.set()
        finally:
            if old is not None:
                import termios
                termios.tcsetattr(fd, termios.TCSADRAIN, old)


def patched_client(host, port, timeout_s):
    import zmq
    from gr00t.policy import server_client as sc
    ms = int(timeout_s * 1000)
    orig = sc.PolicyClient._init_socket

    def init_with_timeouts(self):
        orig(self)
        for opt, val in ((zmq.RCVTIMEO, ms), (zmq.SNDTIMEO, ms), (zmq.LINGER, 0)):
            self.socket.setsockopt(opt, val)
    sc.PolicyClient._init_socket = init_with_timeouts
    return sc.PolicyClient(host=host, port=port, timeout_ms=ms)


class MockControl:
    """Stands in for SO101Control in dry runs: replays images, returns the course initial pose, moves nothing."""

    def __init__(self, front, wrist):
        import cv2
        self.cv2 = cv2
        self.front = cv2.cvtColor(cv2.imread(front), cv2.COLOR_BGR2RGB)
        self.wrist = cv2.cvtColor(cv2.imread(wrist), cv2.COLOR_BGR2RGB)
        from so101_control import SO101Control
        self.pose = dict(SO101Control.initial_pose)
        self.sent = 0

    def connect(self):
        print("[mock] connect: (real robot would move to the course initial pose)")

    def get_observation(self):
        return {**self.pose, "front": self.front.copy(), "wrist": self.wrist.copy()}

    def send_action(self, a):
        self.sent += 1

    def update_log_action(self, a):
        pass

    def stop_logging_thread(self):
        pass

    def disconnect(self):
        print(f"[mock] disconnect after {self.sent} actions: (real robot would move to the course home pose)")


def make_real_control(front_node, wrist_node, fourcc, wrist_fourcc, port, robot_id):
    from lerobot.cameras.opencv.configuration_opencv import OpenCVCameraConfig
    from lerobot.robots.so101_follower import SO101FollowerConfig
    from so101_control import SetupConfig, SO101Control
    cams = {"wrist": OpenCVCameraConfig(index_or_path=wrist_node, width=640, height=480, fps=30, fourcc=wrist_fourcc),
            "front": OpenCVCameraConfig(index_or_path=front_node, width=640, height=480, fps=30, fourcc=fourcc)}
    cfg = SetupConfig(robot=SO101FollowerConfig(port=port, id=robot_id, cameras=cams))
    return SO101Control(cfg)


def save_png(path, rgb):
    import cv2
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--layout", default=None)
    ap.add_argument("--note", default="")
    ap.add_argument("--lang", default=LANG)
    ap.add_argument("--cap-s", type=float, default=60.0)
    ap.add_argument("--timeout-s", type=float, default=3.0)
    ap.add_argument("--action-horizon", type=int, default=16)
    ap.add_argument("--policy-host", default="localhost")
    ap.add_argument("--policy-port", type=int, default=5555)
    ap.add_argument("--fourcc", default="MJPG")
    ap.add_argument("--wrist-fourcc", default="MJPG")
    ap.add_argument("--yes", action="store_true", help="do not wait for Enter before connecting and starting")
    ap.add_argument("--mock-robot", action="store_true")
    ap.add_argument("--mock-front", default=str(GTC / "results" / "c1" / "nominal_front_rgb.png"))
    ap.add_argument("--mock-wrist", default=str(GTC / "results" / "c1" / "nominal_wrist_rgb.png"))
    a = ap.parse_args(argv)
    out = GTC / "results" / ("dryrun_pilot" if a.mock_robot else "pilot")     # dry runs never mix with real runs
    if (out / f"{a.run}.json").exists():
        print(f"STOP: run {a.run} already exists", file=sys.stderr)
        return 3
    rec = {"run": a.run, "start_utc": utc(), "layout": a.layout, "note": a.note, "lang_instruction": a.lang,
           "cap_s": a.cap_s, "policy_timeout_s": a.timeout_s, "action_horizon": a.action_horizon, "mock_robot": a.mock_robot}
    # 1. devices by USB identity, before anything moves
    if not a.mock_robot:
        try:
            front, wrist, arm = usbcam.find("front"), usbcam.find("wrist"), usbcam.find("follower")
        except usbcam.DeviceError as e:
            print(e, file=sys.stderr)
            return 3
        import camera_lock
        if camera_lock.cmd_apply("all", write=True) != 0:
            print("STOP: camera lock does not read back", file=sys.stderr)
            return 3
        rec["devices"] = {"front": front, "wrist": wrist, "follower": arm}
    # 2. server answers within the timeout
    client = patched_client(a.policy_host, a.policy_port, a.timeout_s)
    t0 = time.time()
    if not client.ping():
        print(f"STOP: the policy server at {a.policy_host}:{a.policy_port} did not answer within {a.timeout_s} s",
              file=sys.stderr)
        return 3
    rec["ping_s"] = round(time.time() - t0, 3)
    from so101_eval import So100Adapter
    policy = So100Adapter(client)
    import re
    env = dict(re.findall(r"export (\w+)=(\S+)", Path("/root/env").read_text())) if Path("/root/env").exists() else {}
    control = MockControl(a.mock_front, a.mock_wrist) if a.mock_robot else \
        make_real_control(front["node"], wrist["node"], a.fourcc, a.wrist_fourcc, arm["node"], env.get("ROBOT_ID", "orange_robot"))
    if not a.yes:
        input("Door closed. If this is the arm's first connect, keep a hand on it and the 12 V plug within reach "
              "(torque comes on before the goal is set). Press Enter to connect (it moves to the start pose) ")
    keys = KeyWatcher()
    chunks_f = out / f"{a.run}_chunks.jsonl"
    out.mkdir(parents=True, exist_ok=True)
    media = GTC / "media" / ("dryrun_pilot" if a.mock_robot else "pilot") / a.run
    stop, t_first, n_chunk, n_act = None, None, 0, 0
    control.connect()
    try:
        obs0 = control.get_observation()
        rec["start_joints"] = {k: float(v) for k, v in obs0.items() if k.endswith(".pos")}
        if not a.mock_robot:
            import camera_lock
            rec["lock_after_stream_open"] = camera_lock.cmd_apply("all", write=False)
            if rec["lock_after_stream_open"] != 0:
                rec["lock_reapplied"] = camera_lock.cmd_apply("all", write=True)
        if not a.yes:
            input("Press Enter to start the policy (keys: q/space stop, s success, f safety stop, i invalid) ")
        keys.start()
        with open(chunks_f, "w") as log:
            while stop is None:
                if keys.event.is_set():
                    stop = keys.label
                    break
                obs = control.get_observation()
                obs["lang"] = a.lang
                tq = time.time()
                t_first = t_first or tq
                try:
                    actions = policy.get_action(obs)
                except Exception as e:  # noqa: BLE001  (zmq.Again on timeout, RuntimeError on server error)
                    stop = "policy_timeout" if type(e).__name__ == "Again" else f"policy_error: {type(e).__name__}: {e}"
                    break
                lat = time.time() - tq
                save_png(media / f"chunk_{n_chunk:03d}_front.png", obs["front"])
                save_png(media / f"chunk_{n_chunk:03d}_wrist.png", obs["wrist"])
                sent = 0
                for act in actions[: a.action_horizon]:
                    if keys.event.is_set() or time.time() - t_first > a.cap_s:
                        break
                    tic = time.time()
                    control.send_action(act)
                    control.update_log_action(act)
                    sent += 1
                    dt_ = time.time() - tic
                    if dt_ < 1.0 / 30:
                        time.sleep(1.0 / 30 - dt_)
                n_act += sent
                log.write(json.dumps({"chunk": n_chunk, "utc": utc(), "t_s": round(tq - t_first, 3), "latency_s": round(lat, 4),
                                      "sent": sent, "first_action": actions[0],
                                      "joints": {k: float(v) for k, v in obs.items() if k.endswith(".pos")}}) + "\n")
                log.flush()
                n_chunk += 1
                if time.time() - t_first > a.cap_s:
                    stop = "cap"
    except KeyboardInterrupt:
        stop = "ctrl_c"
    finally:
        keys.event.set()
        rec.update({"stop": stop, "key_t_s": round(keys.t - t_first, 2) if keys.t and t_first else None,
                    "run_s": round(time.time() - t_first, 2) if t_first else 0.0, "chunks": n_chunk, "actions_sent": n_act,
                    "end_utc": utc()})
        try:
            control.stop_logging_thread()
        finally:
            control.disconnect()
        (out / f"{a.run}.json").write_text(json.dumps(rec, indent=1, default=str))
    print(f"PILOT {a.run}: stop={stop} after {rec['run_s']} s, {n_chunk} chunks, {n_act} actions -> results/pilot/{a.run}.json")
    return 4 if stop and stop.startswith("policy") else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
