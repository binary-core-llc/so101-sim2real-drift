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
# sim/render_poses.py. Modified by Binary Core LLC, 2026.
#
# Jaw tip height above the mat (pose check, Nov 6): the arm at given joint values (LeRobot units, the course's
# real->sim mapping), held a few steps; the lowest point of the fixed jaw ('gripper' link) and of the moving jaw
# ('jaw' link) from their meshes, against the mat's top face. Height does not depend on where the tubes or the base
# sit, so it separates the calibration from placement.
#
#   sim/run_sim.sh tips python /workspace/gtc/sim/jaw_tips.py --headless --chunks 6,7,8          # pose-check targets
#   sim/run_sim.sh tips python /workspace/gtc/sim/jaw_tips.py --headless --posecheck results/real/posecheck/L00.jsonl
# Writes results/sim/render/jaw_tips_<tag>.jsonl.
import argparse
import json
import os

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser(description="Sim jaw tip heights at given joint values")
parser.add_argument("--task", type=str, default="Lerobot-So101-Teleop-Vials-To-Rack-Eval")
parser.add_argument("--seed", type=int, default=0)
parser.add_argument("--trace", type=str, default="/workspace/gtc/results/sim/trace/L00_nominal.jsonl")
parser.add_argument("--rep", type=int, default=0)
parser.add_argument("--chunks", type=str, default="6,7,8")
parser.add_argument("--posecheck", type=str, default="", help="use the 'reached' joints of a pose-check file instead")
parser.add_argument("--tag", type=str, default="targets")
parser.add_argument("--hold_steps", type=int, default=3)
parser.add_argument("--scale", type=str, default="", help='JSON {joint: factor}: joint value x factor before the course '
                    'mapping (the real calibrated range over the sim range, ranges centred alike)')
parser.add_argument("--frames_dir", type=str, default="", help="also save the front and wrist images here")
parser.add_argument("--results", type=str, default="/workspace/gtc/results/sim/render")
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
from pxr import Usd, UsdGeom  # noqa: E402

import isaaclab.sim as sim_utils  # noqa: E402
import isaaclab.utils.math as math_utils  # noqa: E402
import isaaclab_tasks  # noqa: E402,F401
from isaaclab_tasks.utils import parse_env_cfg  # noqa: E402

import sim_to_real_so101.tasks  # noqa: E402,F401

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import overrides as OV  # noqa: E402
from local_assets import apply_local_assets  # noqa: E402

INITIAL_ACTION = [-0.2736, -0.6109, -0.0745, 1.5148, -1.6034, -0.1465]  # lerobot_eval.py:159-162
J = ["shoulder_pan.pos", "shoulder_lift.pos", "elbow_flex.pos", "wrist_flex.pos", "wrist_roll.pos", "gripper.pos"]
LINKS = ("gripper", "jaw")                                                # fixed jaw, moving jaw


def tl(x):
    return x.detach().cpu().double().tolist() if isinstance(x, torch.Tensor) else x


def reseed(k):
    random.seed(k)
    np.random.seed(k)
    torch.manual_seed(k)
    torch.cuda.manual_seed_all(k)


def mat4(m):
    return np.array([[m[i][j] for j in range(4)] for i in range(4)])


def link_points(stage, link_path):
    """All mesh points under a link, in the link's frame (static: both transforms read from the same USD state)."""
    link = stage.GetPrimAtPath(link_path)
    inv_link = np.linalg.inv(mat4(UsdGeom.Xformable(link).ComputeLocalToWorldTransform(Usd.TimeCode.Default())))
    pts, names = [], []
    for p in Usd.PrimRange(link, Usd.TraverseInstanceProxies()):
        if p.IsA(UsdGeom.Mesh):
            v = UsdGeom.Mesh(p).GetPointsAttr().Get()
            if v is None or len(v) == 0:
                continue
            m = mat4(UsdGeom.Xformable(p).ComputeLocalToWorldTransform(Usd.TimeCode.Default())) @ inv_link
            h = np.c_[np.array(v, dtype=float), np.ones(len(v))] @ m            # USD row-vector convention
            pts.append(h[:, :3])
            names.append((str(p.GetPath()), len(v)))
    scale = np.linalg.norm(np.linalg.inv(inv_link)[:3, :3], axis=1)
    return (np.vstack(pts) if pts else np.zeros((0, 3))), names, scale.tolist()


def main():
    env_cfg = parse_env_cfg(args_cli.task, device=args_cli.device, num_envs=1, use_fabric=True)
    apply_local_assets(env_cfg)
    OV.apply_to_cfg(env_cfg, {})
    env_cfg.seed = args_cli.seed
    env = gym.make(args_cli.task, cfg=env_cfg)
    scene, dev = env.unwrapped.scene, env.unwrapped.device
    robot = scene["robot"]
    stage = sim_utils.get_current_stage()
    from sim_to_real_so101.utils.lerobot_interface import LeRobotSO101Interface
    iface = LeRobotSO101Interface(device=dev, port=None, id="leader_arm_1", cameras={}, fps=30, kind="follower")

    if args_cli.posecheck:
        poses = [(r["chunk"], r["reached"]) for r in map(json.loads, open(args_cli.posecheck))]
    else:
        want = [int(c) for c in args_cli.chunks.split(",")]
        rows = {r["chunk"]: r for r in map(json.loads, open(args_cli.trace)) if r.get("rep") == args_cli.rep
                and r.get("chunk") in want}
        poses = [(c, {j: rows[c]["joints"][j] for j in J}) for c in want]
        g = max(p["gripper.pos"] for _, p in poses)                      # as real/pose_check.py: jaws kept open
        for _, p in poses:
            p["gripper.pos"] = g

    link_paths = robot.root_physx_view.link_paths[0]
    by_name = {p.rsplit("/", 1)[-1]: p for p in link_paths}
    local = {n: link_points(stage, by_name[n]) for n in LINKS}
    for n in LINKS:
        print(f"[TIPS] link {n}: {by_name[n]}, {len(local[n][0])} points from {len(local[n][1])} meshes, "
              f"link world scale {np.round(local[n][2], 4).tolist()}", flush=True)
    mat_box = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default", "render"]).ComputeWorldBound(
        stage.GetPrimAtPath("/World/envs/env_0/Mat")).ComputeAlignedRange()
    mat_top = float(mat_box.GetMax()[2])
    bidx = {n: robot.body_names.index(n) for n in LINKS}
    init_a = torch.tensor(INITIAL_ACTION, device=dev)
    os.makedirs(args_cli.results, exist_ok=True)
    out = open(f"{args_cli.results}/jaw_tips_{args_cli.tag}.jsonl", "a")
    scale = json.loads(args_cli.scale) if args_cli.scale else {}
    for c, pose in poses:
        sv = [pose[j] * scale.get(j, 1.0) for j in J]
        q = iface.get_mapped_actions_vectorized(torch.tensor(sv, dtype=torch.float32, device=dev))
        reseed(args_cli.seed)
        with torch.inference_mode():
            env.reset()
            for _ in range(10):
                env.step(init_a.unsqueeze(0))
            robot.write_joint_state_to_sim(q.unsqueeze(0), torch.zeros_like(q).unsqueeze(0))
            for _ in range(args_cli.hold_steps):
                obs, *_ = env.step(q.unsqueeze(0))
            held = dict(zip(J, tl(iface.get_raw_actions_from_radians(obs["policy"]["joint_pos_obs"][0]))))
            tips = {}
            for n in LINKS:
                pos = robot.data.body_pos_w[0, bidx[n]].double().cpu()
                quat = robot.data.body_quat_w[0, bidx[n]].double().cpu()
                pl = torch.tensor(local[n][0], dtype=torch.float64)
                pw = math_utils.quat_apply(quat.expand(len(pl), 4), pl) + pos
                k = int(torch.argmin(pw[:, 2]))
                per_mesh, i0 = {}, 0
                for name, nv in local[n][1]:                            # lowest point of each mesh (visual/collision)
                    per_mesh[name.rsplit(n + "/", 1)[-1]] = round((float(pw[i0:i0 + nv, 2].min()) - mat_top) * 1000, 1)
                    i0 += nv
                tips[n] = {"lowest_point_env": [round(x, 4) for x in pw[k].tolist()],
                           "height_above_mat_mm": round((float(pw[k, 2]) - mat_top) * 1000, 1),
                           "per_mesh_mm": dict(sorted(per_mesh.items(), key=lambda kv: kv[1])[:6])}
            if args_cli.frames_dir:
                from PIL import Image
                os.makedirs(args_cli.frames_dir, exist_ok=True)
                for cam, key in (("front", "rgb_external_D455"), ("wrist", "rgb_ego")):
                    Image.fromarray(obs["visual"][key][0].cpu().numpy().astype(np.uint8)).save(
                        f"{args_cli.frames_dir}/chunk_{c:03d}_{cam}.png")
        row = {"tag": args_cli.tag, "chunk": c, "joints": pose, "scale": scale, "sim_values": sv, "held": held, "mat_top_z_m": mat_top, "tips": tips}
        out.write(json.dumps(row) + "\n")
        out.flush()
        print(f"[TIPS] chunk {c}: fixed jaw {tips['gripper']['height_above_mat_mm']} mm, moving jaw "
              f"{tips['jaw']['height_above_mat_mm']} mm above the mat (top z {mat_top:.4f}); held "
              f"{[round(held[j], 1) for j in J]}", flush=True)
        for n in LINKS:
            print(f"[TIPS]   {n}: lowest {tips[n]['lowest_point_env']}  meshes {tips[n]['per_mesh_mm']}", flush=True)
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
