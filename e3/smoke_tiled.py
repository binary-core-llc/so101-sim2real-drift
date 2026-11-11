# T24b: E3 smoke test (D_software C12). Our own scene with N envs, one camera per env (TiledCamera needs
# exactly one per env, tiled_camera.py:154-159), built from the dumped D455 intrinsics at low resolution.
# Checks: N envs render; ID -> label mapping lands in the right env; pose write -> mask latency (frames);
# env-0 mask at the nominal pose vs the C1 render (rack IoU); throughput.
#
#   sim/run_sim.sh gtc-t24b python /workspace/gtc/e3/smoke_tiled.py --headless [--num_envs 16] [--res 160 120]
import argparse
import json
import os
import time

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser()
parser.add_argument("--num_envs", type=int, default=16)
parser.add_argument("--res", type=int, nargs=2, default=[160, 120])
parser.add_argument("--frames", type=str, default="/workspace/gtc/results/c1/frames_sim.json")
parser.add_argument("--c1", type=str, default="/workspace/gtc/results/c1")
parser.add_argument("--out", type=str, default="/workspace/gtc/results/t24b")
AppLauncher.add_app_launcher_args(parser)
args = parser.parse_args()
args.enable_cameras = True
app = AppLauncher(args).app

import numpy as np  # noqa: E402
import torch  # noqa: E402
from PIL import Image  # noqa: E402

import isaaclab.sim as sim_utils  # noqa: E402
from isaaclab.assets import AssetBaseCfg  # noqa: E402
from isaaclab.scene import InteractiveScene, InteractiveSceneCfg  # noqa: E402
from isaaclab.sensors import TiledCameraCfg  # noqa: E402
from isaaclab.utils import configclass  # noqa: E402

from sim_to_real_so101.assets.so101 import SO101_CFG  # noqa: E402

WRAP = "/workspace/gtc/assets/local"
COURSE = "/workspace/Sim-to-Real-SO-101-Workshop/source/sim_to_real_so101/assets/usd"
W, H = args.res
frames = json.load(open(args.frames))
K = frames["camera_external_D455"]["tiled_camera"]["intrinsic_matrices"]
s = W / 640.0
fx, fy, cx, cy = K[0][0] * s, K[1][1] * s, K[0][2] * s, K[1][2] * s
cam_pos0 = frames["camera_external_D455"]["world_usd"]["pos"]
cam_q0 = frames["camera_external_D455"]["tiled_camera"]["quat_w_ros"]
rack_z = frames["objects_after_warmup10"]["rack_left"]["pos"][2]


@configclass
class E3SceneCfg(InteractiveSceneCfg):
    lightstudio = AssetBaseCfg(prim_path="{ENV_REGEX_NS}/LightStudio",
                               spawn=sim_utils.UsdFileCfg(usd_path=f"{WRAP}/lightbox-simple.local.usda"),
                               init_state=AssetBaseCfg.InitialStateCfg(pos=(-0.1, 0, 0.0257)))
    mat = AssetBaseCfg(prim_path="{ENV_REGEX_NS}/Mat", spawn=sim_utils.UsdFileCfg(usd_path=f"{WRAP}/mat.local.usda"),
                       init_state=AssetBaseCfg.InitialStateCfg(pos=(0.22, 0, 0.032), rot=(0.70710678, 0, 0, 0.70710678)))
    rack = AssetBaseCfg(prim_path="{ENV_REGEX_NS}/Rack_Left",
                        spawn=sim_utils.UsdFileCfg(usd_path=f"{COURSE}/Vial_rack_simple.usda"),
                        init_state=AssetBaseCfg.InitialStateCfg(pos=(0.18, 0.08, rack_z)))
    robot = SO101_CFG.replace(prim_path="{ENV_REGEX_NS}/Robot",
                              spawn=SO101_CFG.spawn.replace(usd_path=f"{WRAP}/SO-ARM101-USD.local.usda"))
    e3cam = TiledCameraCfg(
        prim_path="{ENV_REGEX_NS}/E3Cam", update_period=0.0, height=H, width=W,
        data_types=["instance_id_segmentation_fast"], colorize_instance_id_segmentation=False,
        spawn=sim_utils.PinholeCameraCfg.from_intrinsic_matrix(
            intrinsic_matrix=[fx, 0, cx, 0, fy, cy, 0, 0, 1], width=W, height=H, clipping_range=(0.01, 10.0)),
        offset=TiledCameraCfg.OffsetCfg(pos=(0.0, 0.0, 0.0), rot=(1.0, 0.0, 0.0, 0.0), convention="ros"))


def masks(cam):
    return cam.data.output["instance_id_segmentation_fast"][..., 0].clone()   # (N, H, W) uint32 ids


def render(sim, cam, n=1):
    for _ in range(n):
        sim.render()
    cam.update(0.0, force_recompute=True)
    return masks(cam)


def make_setpose(cam, origins):
    from pxr import Gf, Sdf
    from isaaclab.utils.math import convert_camera_frame_orientation_convention as conv
    prims = [p.GetPrim() for p in cam._sensor_prims]
    t_attr = [p.GetAttribute("xformOp:translate") for p in prims]
    o_attr = [p.GetAttribute("xformOp:orient") for p in prims]
    quat_t = Gf.Quatd if "quatd" in str(o_attr[0].GetTypeName()) else Gf.Quatf

    def setpose(pos_w, q_ros):
        q_gl = conv(q_ros, origin="ros", target="opengl").cpu().tolist()
        loc = (pos_w - origins).cpu().tolist()
        with Sdf.ChangeBlock():
            for i in range(len(prims)):
                t_attr[i].Set(Gf.Vec3d(*loc[i]))
                o_attr[i].Set(quat_t(q_gl[i][0], Gf.Vec3d(*q_gl[i][1:]) if quat_t is Gf.Quatd else Gf.Vec3f(*q_gl[i][1:])))
    return setpose, str(o_attr[0].GetTypeName())


def id2label(cam):
    info = cam.data.info if isinstance(cam.data.info, dict) else cam.data.info[0]
    lab = (info.get("instance_id_segmentation_fast") or {}).get("idToLabels", {})
    return {int(k): v for k, v in lab.items()}


def main():
    os.makedirs(args.out, exist_ok=True)
    res = {"num_envs": args.num_envs, "res": [W, H], "K_scaled": [fx, fy, cx, cy]}
    free0, total = torch.cuda.mem_get_info()
    sim = sim_utils.SimulationContext(sim_utils.SimulationCfg(dt=1 / 120, device="cuda:0"))
    scene = InteractiveScene(E3SceneCfg(num_envs=args.num_envs, env_spacing=4.0))
    sim.reset()
    cam = scene["e3cam"]
    origins = scene.env_origins
    N = args.num_envs
    q0 = torch.tensor(cam_q0, device=origins.device).repeat(N, 1)
    p0 = origins + torch.tensor(cam_pos0, device=origins.device)

    # 0) record whether Camera.set_world_poses (Fabric path in Isaac Lab 2.3.2) takes effect
    m_before = render(sim, cam, 2)
    cam.set_world_poses(p0, q0, convention="ros")
    m_after = render(sim, cam, 3)
    res["set_world_poses_changed_masks"] = int(sum(not torch.equal(m_before[i], m_after[i]) for i in range(N)))
    setpose, orient_type = make_setpose(cam, origins)
    res["pose_write_method"] = f"USD xformOp:translate/orient on the camera prims ({orient_type}), env-local, Sdf.ChangeBlock"

    # 1) all envs at the nominal pose
    setpose(p0, q0)
    m_nom = render(sim, cam, 5)
    lab = id2label(cam)
    # debug readback: where are the cameras really, and what do they see
    pw, qw = cam._view.get_world_poses()
    from isaaclab.utils.math import convert_camera_frame_orientation_convention as conv
    res["debug"] = {"requested_pos_env0": p0[0].tolist(), "actual_pos_env0": pw[0].tolist(),
                    "requested_q_ros_env0": q0[0].tolist(),
                    "actual_q_ros_env0": conv(qw[0:1], origin="opengl", target="ros")[0].tolist(),
                    "env_origin0": origins[0].tolist(),
                    "env0_ids_labels": {int(t): lab.get(int(t), "?") for t in torch.unique(m_nom[0]).tolist()},
                    "n_labels": len(lab)}
    res["masks_shape"] = list(m_nom.shape)
    res["dtype"] = str(m_nom.dtype)

    # 2) ID -> label lands in the right env
    wrong, rack_px = 0, []
    for i in range(N):
        ids = torch.unique(m_nom[i]).tolist()
        paths = [lab.get(int(t), "") for t in ids]
        for pth in paths:
            if pth.startswith("/World/envs/env_") and not pth.startswith(f"/World/envs/env_{i}/"):
                wrong += 1
        rack_px.append(int(sum((m_nom[i] == t).sum().item() for t in ids if "/Rack_Left/" in lab.get(int(t), ""))))
    res["labels_in_wrong_env"] = wrong
    res["rack_pixels_per_env"] = rack_px

    # 3) env 0 at nominal vs the C1 640x480 render, rack IoU after nearest-downsampling the C1 mask
    try:
        info = json.load(open(f"{args.c1}/nominal_front_instance_labels.json"))
        ids_c1 = np.array(Image.open(f"{args.c1}/nominal_front_instance_ids.png"))
        raw = {tuple(int(x) for x in k.strip("()").split(",")): v for k, v in info["idToLabels_raw"].items()}
        rack_idx = [int(i) for i, e in info["instance_labels"].items() if "/Rack_Left/" in (raw.get(tuple(e["rgba"])) or "")]
        c1_rack = np.isin(ids_c1, rack_idx)
        c1_small = np.array(Image.fromarray(c1_rack.astype(np.uint8) * 255).resize((W, H), Image.NEAREST)) > 0
        e0 = m_nom[0].cpu().numpy()
        e3_rack = np.isin(e0, [t for t, pth in lab.items() if "/Rack_Left/" in pth])
        res["env0_rack_iou_vs_c1"] = float((c1_small & e3_rack).sum() / max((c1_small | e3_rack).sum(), 1))
    except Exception as e:  # report, don't fail the smoke test
        res["env0_rack_iou_vs_c1"] = f"error: {e}"

    # 4) pose write -> mask latency: env i moves i*4 mm toward the back wall (env +x) and tilts nothing
    dp = torch.zeros_like(p0)
    dp[:, 0] = torch.arange(N, device=p0.device) * 0.004
    setpose(p0 + dp, q0)
    seq = [render(sim, cam, 1) for _ in range(4)]
    m_new = render(sim, cam, 5)
    lat = []
    for i in range(1, N):
        k = next((j + 1 for j, m in enumerate(seq) if torch.equal(m[i], m_new[i])), None)
        lat.append(k)
    res["frames_until_new_mask"] = lat
    res["moved_masks_differ_from_nominal"] = int(sum(not torch.equal(m_new[i], m_nom[i]) for i in range(1, N)))

    # 5) throughput: random small pose changes for every env, write + render + fetch
    g = torch.Generator(device=p0.device).manual_seed(0)
    torch.cuda.synchronize()
    for _ in range(3):  # warm-up
        setpose(p0 + 0.01 * torch.randn(p0.shape, generator=g, device=p0.device), q0)
        render(sim, cam, 1)
    reps, ts = 20, []
    for _ in range(reps):
        t0 = time.perf_counter()
        setpose(p0 + 0.01 * torch.randn(p0.shape, generator=g, device=p0.device), q0)
        render(sim, cam, 1)
        torch.cuda.synchronize()
        ts.append(time.perf_counter() - t0)
    res["iter_ms_median"] = 1000 * float(np.median(ts))
    res["candidates_per_s"] = N / float(np.median(ts))
    free1, _ = torch.cuda.mem_get_info()
    res["vram_used_by_process_mib_approx"] = (free0 - free1) / 2**20
    res["note_latency"] = "1 = the first render after the pose write already shows the new mask"

    # mosaic of the nominal masks
    rows = []
    cols = int(np.ceil(np.sqrt(N)))
    tiles = [(m_nom[i].cpu().numpy().astype(np.uint64) * 2654435761 % 2**24) for i in range(N)]
    tiles += [np.zeros_like(tiles[0])] * (cols * cols - N)
    for r in range(cols):
        rows.append(np.hstack(tiles[r * cols:(r + 1) * cols]))
    mos = np.vstack(rows)
    rgb = np.stack([(mos >> 16) & 255, (mos >> 8) & 255, mos & 255], -1).astype(np.uint8)
    Image.fromarray(rgb).save(f"{args.out}/nominal_masks_mosaic.png")
    json.dump(res, open(f"{args.out}/t24b.json", "w"), indent=1)
    print("[T24B]", json.dumps(res), flush=True)


if __name__ == "__main__":
    code = 0
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        code = 1
    os._exit(code)
