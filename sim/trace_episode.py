# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Derived from the course's source/sim_to_real_so101/scripts/lerobot_eval.py @ ce807d9 (Apache-2.0), through our
# sim/sweep_eval.py (not modified). Modified by Binary Core LLC, 2026.
#
# Trace one sim episode step by step (V28-01 follow-up, Nov 6): the Eval env with every randomization at its centre
# (sim/overrides.py), the course's 10-step warm-up action, GR00TRemotePolicy and success rule, the T32 local assets
# and real ZMQ timeouts, as in sim/sweep_eval.py. Added: every policy query is logged in the units the real runner
# logs (LeRobot joint values, -100..100 and gripper 0..100, through the course's own sim<->real mapping,
# lerobot_interface.py:137-170), with the exact front/wrist images sent, the robot body positions and the objects.
#
#   sim/run_sim.sh trace python /workspace/gtc/sim/trace_episode.py --headless --seed 0 --tag L00 --repeats 3
# Writes results/sim/trace/<tag>.jsonl (one row per policy query, then one summary row per repeat),
# results/sim/trace/<tag>_steps.jsonl (every env step), results/sim/trace/<tag>_r<k>_first_input.npz (the first
# query's model input as sent) and media/sim/trace/<tag>_r<k>/chunk_NNN_{front,wrist}.png.
import argparse
import json
import os

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser(description="Trace one sim episode (derived from the course lerobot_eval.py)")
parser.add_argument("--task", type=str, default="Lerobot-So101-Teleop-Vials-To-Rack-Eval")
parser.add_argument("--tag", type=str, required=True)
parser.add_argument("--seed", type=int, default=0, help="layout seed (L00 = 0, config/layouts.json)")
parser.add_argument("--repeats", type=int, default=1, help="episodes at the same seed (the policy samples noise)")
parser.add_argument("--overrides", type=str, default="{}")
parser.add_argument("--results", type=str, default="/workspace/gtc/results/sim/trace")
parser.add_argument("--media", type=str, default="/workspace/gtc/media/sim/trace")
parser.add_argument("--policy_host", type=str, default="localhost")
parser.add_argument("--policy_port", type=int, default=5555)
parser.add_argument("--policy_timeout_s", type=float, default=10.0)
parser.add_argument("--action_horizon", type=int, default=16)
parser.add_argument("--lang_instruction", type=str, default="Pick up the vial and place it in the yellow rack")
parser.add_argument("--rename_map", type=str, default='{"external_D455": "front", "ego": "wrist"}')
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()
args_cli.enable_cameras = True
app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

import datetime as dt  # noqa: E402
import random  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402

import gymnasium as gym  # noqa: E402
import numpy as np  # noqa: E402
import torch  # noqa: E402
import zmq  # noqa: E402
from PIL import Image  # noqa: E402

import isaaclab_tasks  # noqa: E402,F401
from isaaclab_tasks.utils import parse_env_cfg  # noqa: E402

import sim_to_real_so101.tasks  # noqa: E402,F401

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import overrides as OV  # noqa: E402
from local_assets import apply_local_assets  # noqa: E402

INITIAL_ACTION = [-0.2736, -0.6109, -0.0745, 1.5148, -1.6034, -0.1465]  # lerobot_eval.py:159-162
VIALS = ("vial_1", "vial_2", "vial_3")
LIFT_M = 0.01                                                            # C 1.4 grasp: lifted >= 1 cm


def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds")


def tl(x):
    return x.detach().cpu().double().tolist() if isinstance(x, torch.Tensor) else x


def reseed(k):
    random.seed(k)
    np.random.seed(k)
    torch.manual_seed(k)
    torch.cuda.manual_seed_all(k)


def save_png(path, arr):
    Image.fromarray(arr).save(path)


class Jsonl:
    def __init__(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.f = open(path, "a")

    def write(self, row):
        self.f.write(json.dumps(row) + "\n")
        self.f.flush()
        os.fsync(self.f.fileno())


def main():
    env_cfg = parse_env_cfg(args_cli.task, device=args_cli.device, num_envs=1, use_fabric=True)
    apply_local_assets(env_cfg)
    resolved = OV.apply_to_cfg(env_cfg, json.loads(args_cli.overrides))
    env_cfg.seed = args_cli.seed
    env = gym.make(args_cli.task, cfg=env_cfg)
    scene = env.unwrapped.scene
    robot = scene["robot"]

    from sim_to_real_so101.utils.lerobot_interface import GR00TRemotePolicy, LeRobotSO101Interface
    cameras = {}
    for obj in scene.keys():
        if obj.startswith("camera_"):
            cc = getattr(scene.cfg, obj)
            cameras[obj.replace("camera_", "")] = {"height": cc.height, "width": cc.width}
    iface = LeRobotSO101Interface(device=env.unwrapped.device, port=None, id="leader_arm_1", cameras=cameras,
                                  fps=30, kind="follower", rename_map=json.loads(args_cli.rename_map))
    iface.init_device(visualize=False)
    policy = GR00TRemotePolicy(robot_iface=iface, host=args_cli.policy_host, port=args_cli.policy_port,
                               action_horizon=args_cli.action_horizon, lang_instruction=args_cli.lang_instruction)
    ms = int(args_cli.policy_timeout_s * 1000)
    from sim_to_real_so101.gr00t_client import server_client as sc
    orig_init = sc.PolicyClient._init_socket

    def init_with_timeouts(self):
        orig_init(self)
        for opt, val in ((zmq.RCVTIMEO, ms), (zmq.SNDTIMEO, ms), (zmq.LINGER, 0)):
            self.socket.setsockopt(opt, val)
    sc.PolicyClient._init_socket = init_with_timeouts
    policy.connect()
    calls = []
    orig_get = policy._client.get_action

    def logged_get(model_input, *a, **k):
        t0 = time.perf_counter()
        chunk, info = orig_get(model_input, *a, **k)
        calls.append({"input": model_input, "chunk": chunk, "latency_s": time.perf_counter() - t0})
        return chunk, info
    policy._client.get_action = logged_get

    names = iface.SO101_JOINT_ORDER
    raw = lambda q: dict(zip(names, tl(iface.get_raw_actions_from_radians(q))))
    out = Jsonl(f"{args_cli.results}/{args_cli.tag}.jsonl")
    steps_out = Jsonl(f"{args_cli.results}/{args_cli.tag}_steps.jsonl")
    step_dt = env.unwrapped.step_dt
    print(f"[TRACE] {args_cli.tag} seed {args_cli.seed} x{args_cli.repeats}, step_dt {step_dt}, bodies {robot.body_names}",
          flush=True)
    for rep in range(args_cli.repeats):
        mdir = f"{args_cli.media}/{args_cli.tag}_r{rep}"
        os.makedirs(mdir, exist_ok=True)
        reseed(args_cli.seed)
        calls.clear()
        with torch.inference_mode():
            obs, _ = env.reset()
            policy.reset()
            start_z = {v: float(scene[v].data.root_pos_w[0, 2]) for v in VIALS}
            actions = torch.zeros(env.action_space.shape, device=env.unwrapped.device)
            init_a = torch.tensor(INITIAL_ACTION, device=env.unwrapped.device)
            step, n_chunk, grasped, success, status, first_lift = 0, 0, False, False, "ok", None
            while True:
                q = obs["policy"]["joint_pos_obs"][0].clone()
                if step < 10:
                    actions[:] = init_a
                else:
                    n_before = len(calls)
                    try:
                        actions[:] = policy.get_action(q, obs["visual"], log=False)
                    except (zmq.error.Again, zmq.error.ZMQError) as e:
                        status = f"policy_timeout: {e}"
                        break
                    if len(calls) > n_before:                       # a new chunk was queried at this step
                        c = calls[-1]
                        vis = obs["visual"]
                        save_png(f"{mdir}/chunk_{n_chunk:03d}_front.png", vis["rgb_external_D455"][0].cpu().numpy().astype(np.uint8))
                        save_png(f"{mdir}/chunk_{n_chunk:03d}_wrist.png", vis["rgb_ego"][0].cpu().numpy().astype(np.uint8))
                        if n_chunk == 0:
                            np.savez_compressed(f"{args_cli.results}/{args_cli.tag}_r{rep}_first_input.npz",
                                                front=c["input"]["video"]["front"], wrist=c["input"]["video"]["wrist"],
                                                single_arm=c["input"]["state"]["single_arm"],
                                                gripper=c["input"]["state"]["gripper"],
                                                chunk_single_arm=c["chunk"]["single_arm"], chunk_gripper=c["chunk"]["gripper"])
                        out.write({"rep": rep, "chunk": n_chunk, "step": step, "t_s": round((step - 10) * step_dt, 4),
                                   "latency_s": round(c["latency_s"], 4), "joints": raw(q), "joint_pos_rad": tl(q),
                                   "actions": policy._decode_action_chunk(c["chunk"]),
                                   "bodies": dict(zip(robot.body_names, tl(robot.data.body_pos_w[0]))),
                                   "vials": {v: tl(scene[v].data.root_pos_w[0]) for v in VIALS},
                                   "rack": tl(scene["rack_left"].data.root_pos_w[0])})
                        n_chunk += 1
                vz = {v: float(scene[v].data.root_pos_w[0, 2]) for v in VIALS}
                if first_lift is None:
                    up = [v for v in VIALS if vz[v] - start_z[v] >= LIFT_M]
                    if up:
                        first_lift = {"vial": up[0], "step": step, "t_s": round((step - 10) * step_dt, 4)}
                steps_out.write({"rep": rep, "step": step, "joints": raw(q), "action_rad": tl(actions[0] if actions.dim() > 1
                                                                                          else actions),
                                 "vial_z": vz})
                obs, _, terminated, truncated, _ = env.step(actions)
                step += 1
                g = obs.get("subtask_terms", {}).get("vial_grasped")
                if g is not None and bool(torch.as_tensor(g).any()):
                    grasped = True
                te, tr = bool(terminated.any()), bool(truncated.any())
                if te or tr:
                    success = te and not tr
                    break
        row = {"utc": utc(), "rep": rep, "summary": True, "tag": args_cli.tag, "seed": args_cli.seed, "status": status,
               "success": bool(success), "steps": step, "policy_t_s": round((step - 10) * step_dt, 4), "grasped": grasped,
               "first_lift": first_lift, "start_vial_z": start_z, "n_chunks": n_chunk, "step_dt": step_dt,
               "resolved": resolved, "lang_instruction": args_cli.lang_instruction, "task": args_cli.task,
               "gtc_git": os.environ.get("GTC_GIT", ""), "gtc_dirty": os.environ.get("GTC_DIRTY", ""),
               "image": os.environ.get("GTC_IMAGE", ""), "server_image": os.environ.get("GTC_SERVER_IMAGE", ""),
               "model_rev": os.environ.get("GTC_MODEL_REV", "")}
        out.write(row)
        print(f"[TRACE] rep {rep} success={success} steps={step} grasped={grasped} first_lift={first_lift} "
              f"chunks={n_chunk} status={status}", flush=True)
        if status != "ok":
            return 3
    return 0


if __name__ == "__main__":
    code = 1
    try:
        code = main()
    except Exception:
        import traceback
        traceback.print_exc()
        code = 1
    print(f"[EXIT] code {code} at {utc()}", flush=True)
    sys.stdout.flush()
    os._exit(code)
