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
# GTC 2027 (C3): derived from the course's source/sim_to_real_so101/scripts/lerobot_eval.py
# @ ce807d9. Same env, same 10-step warm-up action, same GR00TRemotePolicy, same success rule
# (terminated and not truncated). Changes, all documented:
#   - every randomization fixed at its centre; only the cell's factor changes (sim/overrides.py);
#   - common random numbers: RNGs re-seeded with seed_base + episode right before env.reset();
#   - live-stage readback after every reset, checked against the request (T05);
#   - policy calls with real ZMQ timeouts (the course PolicyClient never applies timeout_ms);
#   - per-episode JSONL, first-policy-frame and final-frame dumps, STOP file, heartbeat;
#   - the scene loads through the T32 local asset wrappers (no S3);
#   - flush + fsync + os._exit at the end (lerobot_eval.py:251-252 never returns);
#   - keyboard control and Rerun logging removed; probe mode (no policy) for T05-T07 and V05.
#
#   sim/run_sim.sh <name> python /workspace/gtc/sim/sweep_eval.py --headless --cell_id nominal \
#       --overrides '{}' --n_episodes 50 --seed_base 1000
import argparse
import json
import os

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser(description="GTC sweep eval (derived from the course lerobot_eval.py)")
parser.add_argument("--task", type=str, default="Lerobot-So101-Teleop-Vials-To-Rack-Eval")
parser.add_argument("--cell_id", type=str, required=True)
parser.add_argument("--overrides", type=str, default="{}", help="JSON dict or @file (see sim/overrides.py)")
parser.add_argument("--n_episodes", type=int, default=10)
parser.add_argument("--start_episode", type=int, default=0, help="resume: first episode index to run")
parser.add_argument("--seed_base", type=int, default=1000)
parser.add_argument("--seed_mod", type=int, default=0, help="repeats: seed = seed_base + episode % seed_mod (0 = off)")
parser.add_argument("--as_shipped", action="store_true", help="run the task exactly as shipped (no centring, no added "
                    "terms); the readback is recorded, not checked (S-course)")
parser.add_argument("--results", type=str, default="/workspace/gtc/results/sim")
parser.add_argument("--media", type=str, default="/workspace/gtc/media/sim")
parser.add_argument("--policy_host", type=str, default="localhost")
parser.add_argument("--policy_port", type=int, default=5555)
parser.add_argument("--policy_timeout_s", type=float, default=10.0)
parser.add_argument("--action_horizon", type=int, default=16)
parser.add_argument("--lang_instruction", type=str, default="Pick up the vial and place it in the yellow rack")
parser.add_argument("--rename_map", type=str, default='{"external_D455": "front", "ego": "wrist"}')
parser.add_argument("--checkpoint", type=str, default="", help="logged only (the server decides)")
parser.add_argument("--no_frames", action="store_true", help="skip the step-0/final frame dumps")
parser.add_argument("--online_assets", action="store_true", help="load the course USDs from S3 as they are")
parser.add_argument("--stop_file", type=str, default="/workspace/gtc/queue/STOP")
parser.add_argument("--probe", type=str, default="", help="@file with [{name, overrides}]: no policy; reset, readback, "
                    "10 warm-up steps and dumps for every set x seed (T05/T06/T07, V05)")
parser.add_argument("--probe_seeds", type=str, default="0", help="e.g. 0-29 or 0,5,7")
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()
args_cli.enable_cameras = True
app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

import datetime as dt  # noqa: E402
import math  # noqa: E402
import random  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402

import gymnasium as gym  # noqa: E402
import numpy as np  # noqa: E402
import torch  # noqa: E402
import zmq  # noqa: E402
from pxr import Gf, Usd, UsdGeom  # noqa: E402

import isaaclab.sim as sim_utils  # noqa: E402
import isaaclab.utils.math as math_utils  # noqa: E402
import isaaclab_tasks  # noqa: E402,F401
from isaaclab_tasks.utils import parse_env_cfg  # noqa: E402

import sim_to_real_so101.tasks  # noqa: E402,F401
from sim_to_real_so101.mdp import resets as course_resets  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import overrides as OV  # noqa: E402

ENV0 = "/World/envs/env_0"
MOUNT = f"{ENV0}/LightStudio/LightBox/camera_mount"
MOUNT_PATTERN = "{ENV_REGEX_NS}/LightStudio/LightBox/camera_mount"
LIGHT = f"{ENV0}/LightStudio/LightBox/RectLight"
INITIAL_ACTION = [-0.2736, -0.6109, -0.0745, 1.5148, -1.6034, -0.1465]  # lerobot_eval.py:159-162
RACK_DEFAULT = (0.18, 0.08, 0.06)  # vials_to_rack_env_cfg.py:103
TOL = 1e-4


def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds")


def tl(x):
    return x.detach().cpu().double().tolist() if isinstance(x, torch.Tensor) else x


def reseed(k):
    random.seed(k)
    np.random.seed(k)
    torch.manual_seed(k)
    torch.cuda.manual_seed_all(k)


def parse_seeds(s):
    out = []
    for part in s.split(","):
        a, _, b = part.partition("-")
        out += list(range(int(a), int(b) + 1)) if b else [int(a)]
    return out


def load_json_arg(s):
    if s.startswith("@"):
        with open(s[1:]) as f:
            return json.load(f)
    return json.loads(s)


def quat_angle(q1, q2):
    """Angle of the relative rotation q1^-1 q2 (wxyz), stable for tiny angles (2*atan2(|v|, |w|))."""
    w1, x1, y1, z1 = q1
    w2, x2, y2, z2 = q2
    w = w1 * w2 + x1 * x2 + y1 * y2 + z1 * z2
    x = w1 * x2 - x1 * w2 - y1 * z2 + z1 * y2
    y = w1 * y2 + x1 * z2 - y1 * w2 - z1 * x2
    z = w1 * z2 - x1 * y2 + y1 * x2 - z1 * w2
    return 2 * math.atan2(math.sqrt(x * x + y * y + z * z), abs(w))


def world_pose(stage, path):
    m = UsdGeom.Xformable(stage.GetPrimAtPath(path)).ComputeLocalToWorldTransform(Usd.TimeCode.Default())
    rot = m.RemoveScaleShear().ExtractRotationQuat()
    z = Gf.Vec3d(m.GetRow3(2)).GetNormalized()
    fwd = [-z[0], -z[1], -z[2]]  # USD camera looks along -Z
    return {"pos": list(m.ExtractTranslation()), "quat_wxyz": [rot.GetReal(), *rot.GetImaginary()],
            "axis_deg_below_horizontal": math.degrees(math.asin(-fwd[2])),
            "axis_heading_deg": math.degrees(math.atan2(fwd[1], fwd[0]))}


def readback(env, r):
    """Read the live stage right after env.reset() and compare with the requested levels (T05)."""
    stage = sim_utils.get_current_stage()
    scene = env.unwrapped.scene
    out, ok = {}, True

    base = course_resets._default_poses_cache[MOUNT_PATTERN]
    mp = stage.GetPrimAtPath(MOUNT)
    t = mp.GetAttribute("xformOp:translate").Get()
    q = mp.GetAttribute("xformOp:orient").Get()
    q = [q.GetReal(), *q.GetImaginary()]
    c = r["camera"]
    exp_t = [base["pos"][0] + c["x"], base["pos"][1] + c["y"], base["pos"][2] + c["z"]]
    dq = math_utils.quat_from_euler_xyz(torch.tensor([c["roll"]]), torch.tensor([c["pitch"]]), torch.tensor([c["yaw"]]))
    exp_q = math_utils.quat_mul(torch.tensor([base["quat"]]), dq)[0].tolist()
    e_t, e_q = max(abs(a - b) for a, b in zip(t, exp_t)), quat_angle(q, exp_q)
    out["camera_mount"] = {"translate": list(t), "orient": q, "err_m": e_t, "err_rad": e_q}
    ok &= e_t < TOL and e_q < TOL

    cam = scene["camera_external_D455"]
    cpath = str(cam._sensor_prims[0].GetPath())
    focal = stage.GetPrimAtPath(cpath).GetAttribute("focalLength").Get()
    hap = stage.GetPrimAtPath(cpath).GetAttribute("horizontalAperture").Get()
    out["camera_external"] = {**world_pose(stage, cpath), "focal_mm": focal, "hap_mm": hap,
                              "hfov_deg": math.degrees(2 * math.atan(hap / (2 * focal)))}
    ok &= abs(focal - r["camera_focal_mm"]) < TOL * max(1, r["camera_focal_mm"])

    egop = str(scene["camera_ego"]._sensor_prims[0].GetPath())
    ego_f = stage.GetPrimAtPath(egop).GetAttribute("focalLength").Get()
    out["wrist_focal_mm"] = ego_f
    ok &= abs(ego_f - r["wrist_focal_mm"]) < TOL * 15

    ex = stage.GetPrimAtPath(LIGHT).GetAttribute("inputs:exposure").Get()
    out["exposure_ev"] = ex
    ok &= abs(ex - r["exposure_ev"]) < TOL

    mq = stage.GetPrimAtPath(f"{ENV0}/Mat").GetAttribute("xformOp:orient").Get()
    w, (x, y, z) = mq.GetReal(), mq.GetImaginary()
    mat_yaw = math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z)) - math.pi / 2
    out["mat_yaw_rad"] = mat_yaw
    ok &= abs(mat_yaw - r["mat_yaw_rad"]) < TOL

    rk = scene["rack_left"]
    rp, rq = tl(rk.data.root_pos_w[0]), tl(rk.data.root_quat_w[0])
    exp_rp = [RACK_DEFAULT[0] + r["rack"]["x"], RACK_DEFAULT[1] + r["rack"]["y"], RACK_DEFAULT[2]]
    rack_yaw = math.atan2(2 * (rq[0] * rq[3] + rq[1] * rq[2]), 1 - 2 * (rq[2] ** 2 + rq[3] ** 2))
    e_r = max(abs(a - b) for a, b in zip(rp, exp_rp))
    out["rack"] = {"pos": rp, "quat_wxyz": rq, "yaw_rad": rack_yaw, "err_m": e_r,
                   "err_yaw_rad": abs(rack_yaw - r["rack"]["yaw"])}
    ok &= e_r < TOL and abs(rack_yaw - r["rack"]["yaw"]) < TOL
    out["vials"] = {v: {"pos": tl(scene[v].data.root_pos_w[0]), "quat_wxyz": tl(scene[v].data.root_quat_w[0])}
                    for v in ("vial_1", "vial_2", "vial_3")}
    if r["rack_placement_prob"] == 0:  # no vial pre-placed on the rack: all three at fixed_vial_z 0.05
        zs = [v["pos"][2] for v in out["vials"].values()]
        out["vials_on_mat_z_ok"] = all(abs(z - 0.05) < TOL for z in zs)
        ok &= out["vials_on_mat_z_ok"]
    out["pass"] = bool(ok)
    return out


def objects(scene):
    return {n: {"pos": tl(scene[n].data.root_pos_w[0]), "quat_wxyz": tl(scene[n].data.root_quat_w[0])}
            for n in ("rack_left", "vial_1", "vial_2", "vial_3")}


def save_png(path, arr):
    from PIL import Image
    Image.fromarray(arr).save(path)


def dump_frames(scene, d, stem, masks=False):
    os.makedirs(d, exist_ok=True)
    cam = scene["camera_external_D455"]
    save_png(f"{d}/{stem}_front.png", cam.data.output["rgb"][0].cpu().numpy().astype(np.uint8))
    save_png(f"{d}/{stem}_wrist.png", scene["camera_ego"].data.output["rgb"][0].cpu().numpy().astype(np.uint8))
    if masks and "instance_id_segmentation_fast" in cam.data.output:
        seg = cam.data.output["instance_id_segmentation_fast"][0].cpu().numpy().astype(np.uint8)
        save_png(f"{d}/{stem}_front_instance_rgba.png", seg)
        info = cam.data.info if isinstance(cam.data.info, dict) else cam.data.info[0]
        lab = (info.get("instance_id_segmentation_fast") or {}).get("idToLabels", {})
        with open(f"{d}/{stem}_front_instance_labels.json", "w") as f:
            json.dump({str(tuple(int(x) for x in k)) if isinstance(k, (tuple, list)) else str(k): v
                       for k, v in lab.items()}, f)


def vial_rack_local(scene):
    """Each vial origin in the rack's corner frame (success audit, R14)."""
    rk = scene["rack_left"]
    rp, rq = rk.data.root_pos_w[0:1], rk.data.root_quat_w[0:1]
    out = {}
    for v in ("vial_1", "vial_2", "vial_3"):
        p, _ = math_utils.subtract_frame_transforms(rp, rq, scene[v].data.root_pos_w[0:1], scene[v].data.root_quat_w[0:1])
        out[v] = tl(p[0])
    return out


class Jsonl:
    def __init__(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.f = open(path, "a")

    def write(self, row):
        self.f.write(json.dumps(row) + "\n")
        self.f.flush()
        os.fsync(self.f.fileno())


def heartbeat(path, **kw):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump({"utc": utc(), **kw}, f)
    os.replace(tmp, path)


def make_env(r_cfg_overrides):
    env_cfg = parse_env_cfg(args_cli.task, device=args_cli.device, num_envs=1, use_fabric=True)
    assets = "online"
    if not args_cli.online_assets:
        from local_assets import apply_local_assets
        assets = apply_local_assets(env_cfg)
    if args_cli.as_shipped:
        resolved = None
    else:
        resolved = OV.apply_to_cfg(env_cfg, r_cfg_overrides)
    env_cfg.seed = args_cli.seed_base
    env = gym.make(args_cli.task, cfg=env_cfg)
    return env, resolved, assets


def warmup(env, n):
    act = torch.tensor(INITIAL_ACTION, device=env.unwrapped.device).repeat(env.unwrapped.num_envs, 1)
    obs = None
    for _ in range(n):
        obs, _, _, _, _ = env.step(act)
    return obs


def run_probe():
    sets = load_json_arg(args_cli.probe)
    seeds = parse_seeds(args_cli.probe_seeds)
    env, _, assets = make_env(sets[0]["overrides"])
    scene = env.unwrapped.scene
    out = Jsonl(f"{args_cli.results}/{args_cli.cell_id}.jsonl")
    mdir = f"{args_cli.media}/{args_cli.cell_id}"
    for s in sets:
        r = OV.apply_to_env(env, s["overrides"])
        for k in seeds:
            reseed(k)
            with torch.inference_mode():
                env.reset()
                rb = readback(env, r)
                after_reset = objects(scene)
                warmup(env, 10)
                after10 = objects(scene)
                cam_w10 = world_pose(sim_utils.get_current_stage(),
                                     str(scene["camera_external_D455"]._sensor_prims[0].GetPath()))
                if not args_cli.no_frames:
                    dump_frames(scene, mdir, f"{s['name']}_seed{k:03d}", masks=True)
            out.write({"utc": utc(), "mode": "probe", "cell": args_cli.cell_id, "set": s["name"], "seed": k,
                       "overrides": s["overrides"], "resolved": r, "readback": rb,
                       "objects_after_reset": after_reset, "objects_after_warmup10": after10,
                       "camera_after_warmup10": cam_w10, "assets": "local" if assets != "online" else "online"})
            print(f"[PROBE] {s['name']} seed {k} readback_pass={rb['pass']}", flush=True)


def run_cell():
    ov = load_json_arg(args_cli.overrides)
    env, resolved, assets = make_env(ov)
    scene = env.unwrapped.scene
    out = Jsonl(f"{args_cli.results}/{args_cli.cell_id}.jsonl")
    mdir = f"{args_cli.media}/{args_cli.cell_id}"
    hb = f"{args_cli.results}/{args_cli.cell_id}.heartbeat"

    from sim_to_real_so101.utils.lerobot_interface import GR00TRemotePolicy, LeRobotSO101Interface
    cameras = {}
    for obj in scene.keys():
        if obj.startswith("camera_"):
            cc = getattr(scene.cfg, obj)
            cameras[obj.replace("camera_", "")] = {"height": cc.height, "width": cc.width}
    robot_iface = LeRobotSO101Interface(device=env.unwrapped.device, port=None, id="leader_arm_1", cameras=cameras,
                                        fps=30, kind="follower", rename_map=json.loads(args_cli.rename_map))
    robot_iface.init_device(visualize=False)
    policy = GR00TRemotePolicy(robot_iface=robot_iface, host=args_cli.policy_host, port=args_cli.policy_port,
                               action_horizon=args_cli.action_horizon, lang_instruction=args_cli.lang_instruction)

    # real timeouts on the course client (it stores timeout_ms but never applies it)
    ms = int(args_cli.policy_timeout_s * 1000)
    from sim_to_real_so101.gr00t_client import server_client as sc
    orig_init = sc.PolicyClient._init_socket

    def init_with_timeouts(self):
        orig_init(self)
        for opt, val in ((zmq.RCVTIMEO, ms), (zmq.SNDTIMEO, ms), (zmq.LINGER, 0)):
            self.socket.setsockopt(opt, val)
    sc.PolicyClient._init_socket = init_with_timeouts
    policy.connect()
    stats = {"queries": 0, "policy_s": 0.0}
    orig_get = policy._client.get_action

    def timed_get(*a, **k):
        t0 = time.perf_counter()
        res = orig_get(*a, **k)
        stats["queries"] += 1
        stats["policy_s"] += time.perf_counter() - t0
        return res
    policy._client.get_action = timed_get

    max_steps = int(env.unwrapped.max_episode_length)
    print(f"[CELL] {args_cli.cell_id} episodes {args_cli.start_episode}..{args_cli.n_episodes - 1} "
          f"resolved={json.dumps(resolved)}", flush=True)
    for ep in range(args_cli.start_episode, args_cli.n_episodes):
        if os.path.exists(args_cli.stop_file):
            print(f"[CELL] STOP file present, leaving before episode {ep}", flush=True)
            return 10
        seed = args_cli.seed_base + (ep % args_cli.seed_mod if args_cli.seed_mod else ep)
        heartbeat(hb, cell=args_cli.cell_id, episode=ep, step=0)
        stats.update(queries=0, policy_s=0.0)
        t0 = time.perf_counter()
        reseed(seed)
        with torch.inference_mode():
            obs, _ = env.reset()
            if args_cli.as_shipped:
                rb = readback(env, OV.resolve({}))
                rb["pass"] = None
                rb["note"] = "as shipped: the course randomizes these values; recorded, not checked"
            else:
                rb = readback(env, resolved)
            start_objects = objects(scene)
            policy.reset()
            if rb["pass"] is False:
                out.write({"utc": utc(), "cell": args_cli.cell_id, "episode": ep, "seed": seed, "status": "readback_fail",
                           "readback": rb, "resolved": resolved})
                print(f"[CELL] readback FAILED at episode {ep}", flush=True)
                return 2
            actions = torch.zeros(env.action_space.shape, device=env.unwrapped.device)
            init_a = torch.tensor(INITIAL_ACTION, device=env.unwrapped.device)
            step, grasped, success, status = 0, False, False, "ok"
            last = None
            while True:
                if step < 10:
                    actions[:] = init_a
                else:
                    if step == 10 and not args_cli.no_frames:
                        dump_frames(scene, mdir, f"ep{ep:04d}_step0", masks=(ep == args_cli.start_episode))
                    try:
                        actions[:] = policy.get_action(obs["policy"]["joint_pos_obs"][0].clone(), obs["visual"], log=False)
                    except (zmq.error.Again, zmq.error.ZMQError) as e:
                        status = f"policy_timeout: {e}"
                        break
                last = {"objects": objects(scene), "vial_rack_local": vial_rack_local(scene),
                        "front": scene["camera_external_D455"].data.output["rgb"][0].clone()}
                obs, _, terminated, truncated, _ = env.step(actions)
                step += 1
                g = obs.get("subtask_terms", {}).get("vial_grasped")
                if g is not None and bool(torch.as_tensor(g).any()):
                    grasped = True
                if step % 60 == 0:
                    heartbeat(hb, cell=args_cli.cell_id, episode=ep, step=step)
                te, tr = bool(terminated.any()), bool(truncated.any())
                if te or tr:
                    success = te and not tr
                    break
        wall = time.perf_counter() - t0
        if last is not None and not args_cli.no_frames:
            save_png(f"{mdir}/ep{ep:04d}_final_front.png", last["front"].cpu().numpy().astype(np.uint8))
        row = {"utc": utc(), "cell": args_cli.cell_id, "episode": ep, "seed": seed, "status": status,
               "as_shipped": bool(args_cli.as_shipped), "seed_mod": args_cli.seed_mod,
               "success": bool(success), "steps": step, "max_steps": max_steps, "grasped": grasped,
               "wall_s": round(wall, 3), "policy_s": round(stats["policy_s"], 3), "queries": stats["queries"],
               "resolved": resolved, "readback": rb, "start_objects": start_objects,
               "final_objects": last["objects"] if last else None,
               "final_vial_rack_local": last["vial_rack_local"] if last else None,
               "lang_instruction": args_cli.lang_instruction, "rename_map": json.loads(args_cli.rename_map),
               "checkpoint": args_cli.checkpoint, "task": args_cli.task, "assets": "local" if assets != "online" else "online",
               "gtc_git": os.environ.get("GTC_GIT", ""), "image": os.environ.get("GTC_IMAGE", "")}
        out.write(row)
        print(f"[EP] {args_cli.cell_id} ep {ep} seed {seed} success={success} steps={step} wall={wall:.1f}s "
              f"status={status}", flush=True)
        if status != "ok":
            return 3
    return 0


if __name__ == "__main__":
    code = 1
    try:
        code = 0 if args_cli.probe else None
        if args_cli.probe:
            run_probe()
        else:
            code = run_cell()
    except Exception:
        import traceback
        traceback.print_exc()
        code = 1
    print(f"[EXIT] code {code} at {utc()}", flush=True)
    sys.stdout.flush()
    os._exit(code)
