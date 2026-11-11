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
# sim/trace_episode.py. Modified by Binary Core LLC, 2026.
#
# Render the sim scene with the arm at logged real joint values (V28-01 follow-up, Nov 6): no policy. The Eval env with
# every randomization at its centre and the layout's seed (L00 = 0), the course's 10 warm-up steps, then for each pose
# a fresh reset, the arm set to the real joint values through the course's own real->sim mapping
# (lerobot_interface.py:137-149) and held there for a few steps; the front and wrist images and the body positions
# are saved. Same joint numbers -> same place? That is the calibration question, separate from the images.
#
#   sim/run_sim.sh render python /workspace/gtc/sim/render_poses.py --headless --seed 0 \
#       --steps_jsonl /workspace/gtc/results/real/shakedown/steps/V28-01_a1.jsonl --chunks 0,4,6,8,10,14,20,30 --tag V28-01_a1
# Writes results/sim/render/<tag>.jsonl and media/sim/render/<tag>/chunk_NNN_{front,wrist}.png.
import argparse
import json
import os

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser(description="Render the sim at logged real joint values")
parser.add_argument("--task", type=str, default="Lerobot-So101-Teleop-Vials-To-Rack-Eval")
parser.add_argument("--tag", type=str, required=True)
parser.add_argument("--seed", type=int, default=0)
parser.add_argument("--steps_jsonl", type=str, required=True)
parser.add_argument("--chunks", type=str, default="0")
parser.add_argument("--hold_steps", type=int, default=3)
parser.add_argument("--results", type=str, default="/workspace/gtc/results/sim/render")
parser.add_argument("--media", type=str, default="/workspace/gtc/media/sim/render")
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()
args_cli.enable_cameras = True
app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

import random  # noqa: E402
import sys  # noqa: E402

import gymnasium as gym  # noqa: E402
import numpy as np  # noqa: E402
import torch  # noqa: E402
from PIL import Image  # noqa: E402

import isaaclab_tasks  # noqa: E402,F401
from isaaclab_tasks.utils import parse_env_cfg  # noqa: E402

import sim_to_real_so101.tasks  # noqa: E402,F401

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import overrides as OV  # noqa: E402
from local_assets import apply_local_assets  # noqa: E402

INITIAL_ACTION = [-0.2736, -0.6109, -0.0745, 1.5148, -1.6034, -0.1465]  # lerobot_eval.py:159-162
VIALS = ("vial_1", "vial_2", "vial_3")


def tl(x):
    return x.detach().cpu().double().tolist() if isinstance(x, torch.Tensor) else x


def reseed(k):
    random.seed(k)
    np.random.seed(k)
    torch.manual_seed(k)
    torch.cuda.manual_seed_all(k)


def save_png(path, arr):
    Image.fromarray(arr.astype(np.uint8)).save(path)


def main():
    env_cfg = parse_env_cfg(args_cli.task, device=args_cli.device, num_envs=1, use_fabric=True)
    apply_local_assets(env_cfg)
    OV.apply_to_cfg(env_cfg, {})
    env_cfg.seed = args_cli.seed
    env = gym.make(args_cli.task, cfg=env_cfg)
    scene, dev = env.unwrapped.scene, env.unwrapped.device
    robot = scene["robot"]
    from sim_to_real_so101.utils.lerobot_interface import LeRobotSO101Interface
    iface = LeRobotSO101Interface(device=dev, port=None, id="leader_arm_1", cameras={}, fps=30, kind="follower")
    names = iface.SO101_JOINT_ORDER
    want = [int(c) for c in args_cli.chunks.split(",")]
    rows = {r["chunk"]: r for r in map(json.loads, open(args_cli.steps_jsonl)) if r["chunk"] in want}
    mdir = f"{args_cli.media}/{args_cli.tag}"
    os.makedirs(mdir, exist_ok=True)
    os.makedirs(args_cli.results, exist_ok=True)
    out = open(f"{args_cli.results}/{args_cli.tag}.jsonl", "a")
    init_a = torch.tensor(INITIAL_ACTION, device=dev)
    for c in want:
        raw = torch.tensor([rows[c]["joints"][n] for n in names], dtype=torch.float32, device=dev)
        q = iface.get_mapped_actions_vectorized(raw)              # the course's real -> sim mapping (radians)
        reseed(args_cli.seed)
        with torch.inference_mode():
            obs, _ = env.reset()
            for _ in range(10):
                obs, *_ = env.step(init_a.unsqueeze(0))
            vials0 = {v: tl(scene[v].data.root_pos_w[0]) for v in VIALS}
            robot.write_joint_state_to_sim(q.unsqueeze(0), torch.zeros_like(q).unsqueeze(0))
            for _ in range(args_cli.hold_steps):
                obs, *_ = env.step(q.unsqueeze(0))
            vis = obs["visual"]
            save_png(f"{mdir}/chunk_{c:03d}_front.png", vis["rgb_external_D455"][0].cpu().numpy())
            save_png(f"{mdir}/chunk_{c:03d}_wrist.png", vis["rgb_ego"][0].cpu().numpy())
            got = dict(zip(names, tl(iface.get_raw_actions_from_radians(obs["policy"]["joint_pos_obs"][0]))))
            row = {"tag": args_cli.tag, "chunk": c, "seed": args_cli.seed, "real_joints": rows[c]["joints"],
                   "q_rad": tl(q), "sim_joints_after_hold": got,
                   "bodies": dict(zip(robot.body_names, tl(robot.data.body_pos_w[0]))),
                   "vials_before": vials0, "vials_after": {v: tl(scene[v].data.root_pos_w[0]) for v in VIALS}}
        out.write(json.dumps(row) + "\n")
        out.flush()
        print(f"[RENDER] chunk {c}: held {[round(got[n], 1) for n in names]} for real "
              f"{[round(rows[c]['joints'][n], 1) for n in names]}", flush=True)
    out.close()
    return 0


if __name__ == "__main__":
    code = 1
    try:
        code = main()
    except Exception:
        import traceback
        traceback.print_exc()
        code = 1
    print(f"[EXIT] code {code}", flush=True)
    sys.stdout.flush()
    os._exit(code)
