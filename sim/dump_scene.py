# C1 scene dump (tests T04, T30 inputs; V01-V06). Runs inside the course sim image:
#
#   sim/run_sim.sh gtc-c1 python /workspace/gtc/sim/dump_scene.py --headless \
#       [--out /workspace/gtc/results/c1] [--media /workspace/gtc/media/c1] [--seeds 0-9]
#
# Builds Lerobot-So101-Teleop-Vials-To-Rack-Eval once with every DR range made
# degenerate at its centre (terms are frozen, never deleted, so RNG draw order is kept):
#   light exposure -1 EV (range -3..+1), mat yaw 0, wrist focal 13.5 mm (12..15),
#   external camera mount offsets 0, rack offsets 0 and rack_placement_prob 0.
# Phase "nominal": vial offsets 0 too -> frames_sim.json, front/wrist PNGs, instance masks.
# Phase "seeds": vial offsets back to the Eval ranges; for seed k, RNGs are re-seeded with k
#   immediately before env.reset() (seed convention v0), then the course's 10 warm-up steps
#   (lerobot_eval.py:159-162, 183-184) -> rack/vial poses after reset, after 10 and 60 steps.
# Nothing in the course folder is modified; the env config is changed in memory only.
import argparse
import json
import os

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser(description="GTC C1 scene dump")
parser.add_argument("--task", default="Lerobot-So101-Teleop-Vials-To-Rack-Eval")
parser.add_argument("--out", default="/workspace/gtc/results/c1")
parser.add_argument("--media", default="/workspace/gtc/media/c1")
parser.add_argument("--seeds", default="0-9")
parser.add_argument("--online_assets", action="store_true",
                    help="load the course USDs as they are (remote MDLs + D455 from S3) instead of the T32 local wrappers")
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()
args_cli.enable_cameras = True
app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

import copy  # noqa: E402
import datetime as dt  # noqa: E402
import hashlib  # noqa: E402
import math  # noqa: E402
import random  # noqa: E402

import gymnasium as gym  # noqa: E402
import numpy as np  # noqa: E402
import torch  # noqa: E402
from pxr import Gf, Usd, UsdGeom, UsdPhysics, UsdShade  # noqa: E402

import isaaclab.sim as sim_utils  # noqa: E402
import isaaclab_tasks  # noqa: E402,F401
from isaaclab_tasks.utils import parse_env_cfg  # noqa: E402

import sim_to_real_so101.tasks  # noqa: E402,F401

ENV0 = "/World/envs/env_0"
CAM_EXT = f"{ENV0}/LightStudio/LightBox/camera_mount/rsd455/RSD455/Camera_OmniVision_OV9782_Right"
MOUNT = f"{ENV0}/LightStudio/LightBox/camera_mount"
LIGHT = f"{ENV0}/LightStudio/LightBox/RectLight"
PANELS = ["Base", "Back", "Left", "Right", "Top"]
INITIAL_ACTION = [-0.2736, -0.6109, -0.0745, 1.5148, -1.6034, -0.1465]  # lerobot_eval.py:159-162
CENTRE = {"exposure": -1.0, "wrist_focal_mm": 13.5}


def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def tl(x):
    """tensor/array/Gf -> plain nested lists of float."""
    if isinstance(x, torch.Tensor):
        return x.detach().cpu().double().tolist()
    if isinstance(x, np.ndarray):
        return x.astype(float).tolist()
    if isinstance(x, (Gf.Matrix4d, Gf.Matrix3d)):
        return [list(r) for r in x]
    if isinstance(x, (Gf.Vec3d, Gf.Vec3f, Gf.Vec2f, Gf.Vec2d, Gf.Vec4f)):
        return list(x)
    if isinstance(x, (Gf.Quatd, Gf.Quatf)):
        return [x.GetReal(), *x.GetImaginary()]
    return x


def val(v):
    """USD attribute value -> JSON-able."""
    if v is None or isinstance(v, (bool, int, float, str)):
        return v
    if isinstance(v, np.generic):
        return v.item()
    r = tl(v)
    if r is not v:
        return r
    if hasattr(v, "__len__"):
        try:
            return f"<array len {len(v)}>" if len(v) >= 64 else [val(x) for x in v]
        except Exception:
            pass
    return str(v)


def quat_wxyz_to_rpy_deg(q):
    w, x, y, z = q
    roll = math.atan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y))
    pitch = math.asin(max(-1.0, min(1.0, 2 * (w * y - z * x))))
    yaw = math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))
    return [math.degrees(roll), math.degrees(pitch), math.degrees(yaw)]


def prim_attrs(prim):
    out = {}
    for a in prim.GetAttributes():
        n = a.GetName()
        if n in ("points", "normals", "faceVertexIndices", "faceVertexCounts") or n.startswith("primvars:st"):
            continue
        try:
            out[n] = {"value": val(a.Get()), "authored": a.HasAuthoredValue(), "type": str(a.GetTypeName())}
        except Exception as e:  # pragma: no cover
            out[n] = {"error": str(e)}
    return out


def world_xf(prim):
    m = UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(Usd.TimeCode.Default())
    t = m.ExtractTranslation()
    rot = m.RemoveScaleShear().ExtractRotationQuat()
    axes = [list(Gf.Vec3d(m.GetRow3(i)).GetNormalized()) for i in range(3)]
    return {"matrix_row_major_usd": tl(m), "pos": list(t), "quat_wxyz": tl(rot),
            "rpy_deg_xyz": quat_wxyz_to_rpy_deg(tl(rot)),
            "axis_x_world": axes[0], "axis_y_world": axes[1], "axis_z_world": axes[2]}


def rigid(asset):
    p = asset.data.root_pos_w[0]
    q = asset.data.root_quat_w[0]
    return {"pos": tl(p), "quat_wxyz": tl(q), "rpy_deg_xyz": quat_wxyz_to_rpy_deg(tl(q))}


def camera_block(stage, scene, name, prim_path):
    cam = scene[name]
    cam._update_poses(cam._ALL_INDICES)  # update_latest_camera_pose is False by default (see notes)
    sensor_path = str(cam._sensor_prims[0].GetPath())  # the prim the TiledCamera actually renders
    if prim_path is None:
        prim_path = sensor_path
    assert prim_path == sensor_path, f"{prim_path} != sensor prim {sensor_path}"
    prim = stage.GetPrimAtPath(prim_path)
    gcam = UsdGeom.Camera(prim)
    gf = gcam.GetCamera(Usd.TimeCode.Default())
    xf = world_xf(prim)
    fwd = [-c for c in xf["axis_z_world"]]  # USD camera looks along -Z
    b = {
        "prim_path": prim_path,
        "type": prim.GetTypeName(),
        "applied_schemas": list(prim.GetAppliedSchemas()),
        "usd": {k: val(getattr(gcam, f"Get{k[0].upper()}{k[1:]}Attr")().Get()) for k in [
            "focalLength", "horizontalAperture", "verticalAperture", "horizontalApertureOffset",
            "verticalApertureOffset", "clippingRange", "projection", "fStop", "focusDistance"]},
        "gf_camera_fov_deg": {"horizontal": gf.GetFieldOfView(Gf.Camera.FOVHorizontal),
                              "vertical": gf.GetFieldOfView(Gf.Camera.FOVVertical)},
        "all_attributes": prim_attrs(prim),
        "world_usd": xf,
        "optical_axis_world": fwd,
        "optical_axis_deg_below_horizontal": math.degrees(math.asin(-fwd[2])),
        "tiled_camera": {
            "intrinsic_matrices": tl(cam.data.intrinsic_matrices[0]),
            "image_shape": list(cam.data.image_shape),
            "pos_w": tl(cam.data.pos_w[0]),
            "quat_w_ros": tl(cam.data.quat_w_ros[0]),
            "quat_w_opengl": tl(cam.data.quat_w_opengl[0]),
            "quat_w_world": tl(cam.data.quat_w_world[0]),
            "cfg_update_latest_camera_pose": bool(cam.cfg.update_latest_camera_pose),
            "cfg_data_types": list(cam.cfg.data_types),
        },
    }
    return b


def save_png(path, arr):
    from PIL import Image
    Image.fromarray(arr).save(path)


def save_camera_images(scene, name, out_dir, stem, masks=True, depth=False):
    cam = scene[name]
    rgb = cam.data.output["rgb"][0].cpu().numpy().astype(np.uint8)
    save_png(os.path.join(out_dir, f"{stem}_rgb.png"), rgb)
    info = {}
    if masks and "instance_id_segmentation_fast" in cam.data.output:
        seg = cam.data.output["instance_id_segmentation_fast"][0].cpu().numpy()
        raw_info = cam.data.info
        if isinstance(raw_info, list):
            raw_info = raw_info[0]
        seg_info = (raw_info or {}).get("instance_id_segmentation_fast") or {}
        # keys may be tuples (colorized) or ints; normalise to "(r, g, b, a)" / "id" strings
        id2lab = {str(tuple(int(x) for x in k)) if isinstance(k, (tuple, list)) else str(k): v
                  for k, v in (seg_info.get("idToLabels", {}) or {}).items()}
        if seg.ndim == 3 and seg.shape[-1] == 4:  # colorized RGBA (course cfg colorizes)
            save_png(os.path.join(out_dir, f"{stem}_instance_rgba.png"), seg.astype(np.uint8))
            flat = seg.reshape(-1, 4).astype(np.uint32)
            keys = (flat[:, 0] << 24) | (flat[:, 1] << 16) | (flat[:, 2] << 8) | flat[:, 3]
            uniq, inv = np.unique(keys, return_inverse=True)
            ids = inv.reshape(seg.shape[:2]).astype(np.uint16)
            labels = {}
            for i, k in enumerate(uniq):
                rgba = (int(k >> 24) & 255, int(k >> 16) & 255, int(k >> 8) & 255, int(k) & 255)
                lab = id2lab.get(str(rgba)) or id2lab.get(str(tuple(rgba))) or id2lab.get(
                    "({}, {}, {}, {})".format(*rgba))
                labels[str(i)] = {"rgba": list(rgba), "label": lab, "pixels": int((inv == i).sum())}
        else:
            ids32 = seg.squeeze().astype(np.uint32)
            uniq, inv = np.unique(ids32, return_inverse=True)
            ids = inv.reshape(ids32.shape).astype(np.uint16)
            labels = {str(i): {"raw_id": int(u), "label": id2lab.get(str(int(u))),
                               "pixels": int((inv == i).sum())} for i, u in enumerate(uniq)}
        save_png(os.path.join(out_dir, f"{stem}_instance_ids.png"), ids)
        info = {"instance_labels": labels, "idToLabels_raw": {str(k): v for k, v in id2lab.items()},
                "seg_dtype_shape": [str(seg.dtype), list(seg.shape)]}
        with open(os.path.join(out_dir, f"{stem}_instance_labels.json"), "w") as f:
            json.dump(info, f, indent=1)
    if depth and "depth" in cam.data.output:
        np.save(os.path.join(out_dir, f"{stem}_depth.npy"),
                cam.data.output["depth"][0].cpu().numpy().astype(np.float32))
    return {"rgb_shape": list(rgb.shape), "rgb_mean": rgb.reshape(-1, 3).mean(0).tolist(), **(
        {"n_instances": len(info.get("instance_labels", {}))} if info else {})}


def reseed(k):
    random.seed(k)
    np.random.seed(k)
    torch.manual_seed(k)
    torch.cuda.manual_seed_all(k)


def warmup(env, n):
    act = torch.tensor(INITIAL_ACTION, device=env.unwrapped.device).repeat(env.unwrapped.num_envs, 1)
    obs = None
    for _ in range(n):
        obs, _, _, _, _ = env.step(act)
    return obs


def objects_block(scene):
    return {"rack_left": rigid(scene["rack_left"]),
            **{v: rigid(scene[v]) for v in ("vial_1", "vial_2", "vial_3")}}


def parse_seeds(s):
    if "-" in s:
        a, b = s.split("-")
        return list(range(int(a), int(b) + 1))
    return [int(x) for x in s.split(",")]


def layer_info(stage):
    layers = []
    for lyr in stage.GetUsedLayers():
        e = {"identifier": lyr.identifier, "realPath": lyr.realPath}
        if "rsd455" in lyr.identifier.lower():
            e["sha256_of_exported_text"] = hashlib.sha256(lyr.ExportToString().encode()).hexdigest()
        layers.append(e)
    return layers


def read_file(p):
    try:
        return open(p).read().strip()
    except OSError:
        return None


def main():
    os.makedirs(args_cli.out, exist_ok=True)
    seed_dir = os.path.join(args_cli.media, "seeds")
    os.makedirs(seed_dir, exist_ok=True)

    env_cfg = parse_env_cfg(args_cli.task, device=args_cli.device, num_envs=1, use_fabric=True)
    assets_log = "online (course USDs as they are)"
    if not args_cli.online_assets:
        from local_assets import apply_local_assets
        assets_log = apply_local_assets(env_cfg)
    ev = env_cfg.events
    eval_vial_range = copy.deepcopy(ev.reset_vials_setup.params["pose_range"])
    dr_original = {
        "exposure_range": ev.reset_lightbox_light_exposure.params["exposure_range"],
        "mat_yaw_range": ev.reset_mat_rotation.params["yaw_range"],
        "wrist_focal_range": ev.reset_camera_ego_fov.params["focal_length_range"],
        "camera_pos_range": copy.deepcopy(ev.reset_camera_external_pose.params["pos_range"]),
        "camera_rot_range": copy.deepcopy(ev.reset_camera_external_pose.params["rot_range"]),
        "rack_pose_range": copy.deepcopy(ev.reset_vials_setup.params["rack_pose_range"]),
        "rack_placement_prob": ev.reset_vials_setup.params.get("rack_placement_prob", "default 0.33 (resets.py:326)"),
        "vial_pose_range": eval_vial_range,
    }
    ev.reset_lightbox_light_exposure.params["exposure_range"] = (CENTRE["exposure"],) * 2
    ev.reset_mat_rotation.params["yaw_range"] = (0.0, 0.0)
    ev.reset_camera_ego_fov.params["focal_length_range"] = (CENTRE["wrist_focal_mm"],) * 2
    ev.reset_camera_external_pose.params["pos_range"] = {k: (0.0, 0.0) for k in ("x", "y", "z")}
    ev.reset_camera_external_pose.params["rot_range"] = {k: (0.0, 0.0) for k in ("roll", "pitch", "yaw")}
    ev.reset_vials_setup.params["rack_pose_range"] = {k: (0.0, 0.0) for k in ("x", "y", "yaw")}
    ev.reset_vials_setup.params["rack_placement_prob"] = 0.0
    ev.reset_vials_setup.params["pose_range"] = {k: (0.0, 0.0) for k in eval_vial_range}
    env_cfg.seed = 0

    env = gym.make(args_cli.task, cfg=env_cfg)
    scene = env.unwrapped.scene
    stage = sim_utils.get_current_stage()
    vial_term = env.unwrapped.event_manager.get_term_cfg("reset_vials_setup")

    # ---------------- nominal ----------------
    reseed(0)
    with torch.inference_mode():
        env.reset()
        after_reset = objects_block(scene)
        warmup(env, 10)
    robot = scene["robot"]
    frames = {
        "schema": "gtc frames_sim v0",
        "created_utc": utc(),
        "task": args_cli.task,
        "conventions": {
            "quat": "wxyz", "units": "m, deg unless named _rad",
            "matrix_row_major_usd": "USD row-vector convention: p_world = p_local * M; rows 0-2 = local axes in world, row 3 = translation",
            "camera_frames": "USD camera looks along -Z with +Y up; quat_w_ros = OpenCV/ROS (+Z forward, -Y up)",
            "poses_read": "after env.reset() and after the course's 10 warm-up steps (initial_action), unless labelled",
        },
        "dr_setting": {"original_ranges": dr_original,
                       "applied": "all ranges degenerate at centre: exposure -1 EV, mat yaw 0, wrist focal 13.5 mm, camera offsets 0, rack offsets 0, rack_placement_prob 0, vial offsets 0 (nominal phase)"},
        "versions": {
            "isaac_sim": read_file("/workspace/isaaclab/_isaac_sim/VERSION"),
            "isaac_lab": read_file("/workspace/isaaclab/VERSION"),
        },
        "sim": {"dt": env_cfg.sim.dt, "decimation": env_cfg.decimation,
                "episode_length_s": env_cfg.episode_length_s,
                "max_episode_length_steps": int(env.unwrapped.max_episode_length),
                "render_mode": str(env_cfg.sim.render.rendering_mode)},
        "assets": assets_log,
        "env_origin": tl(scene.env_origins[0]),
        "robot": {
            "root": rigid(robot),
            "joint_names": list(robot.joint_names),
            "joint_pos_rad": tl(robot.data.joint_pos[0]),
            "bodies": {n: {"pos": tl(robot.data.body_pos_w[0, i]), "quat_wxyz": tl(robot.data.body_quat_w[0, i])}
                       for i, n in enumerate(robot.body_names)},
        },
        "objects_after_reset": after_reset,
        "objects_after_warmup10": objects_block(scene),
    }

    # robot USD joints and mesh -> material (for the orange patch)
    joints, mesh_mat = {}, {}
    # the robot visuals are instanceable: walk instance proxies too, or the meshes are skipped
    for p in Usd.PrimRange(stage.GetPrimAtPath(f"{ENV0}/Robot"), Usd.TraverseInstanceProxies()):
        if p.IsA(UsdPhysics.Joint):
            j = UsdPhysics.Joint(p)
            joints[p.GetName()] = {
                "path": str(p.GetPath()), "type": p.GetTypeName(),
                "body0": [str(t) for t in j.GetBody0Rel().GetTargets()],
                "body1": [str(t) for t in j.GetBody1Rel().GetTargets()],
                "localPos0": val(j.GetLocalPos0Attr().Get()), "localRot0": val(j.GetLocalRot0Attr().Get()),
                "localPos1": val(j.GetLocalPos1Attr().Get()), "localRot1": val(j.GetLocalRot1Attr().Get())}
        if p.IsA(UsdGeom.Mesh):
            m = UsdShade.MaterialBindingAPI(p).ComputeBoundMaterial()[0]
            mesh_mat[str(p.GetPath())] = str(m.GetPath()) if m else None
    frames["robot"]["usd_joints"] = joints
    frames["robot"]["mesh_materials"] = mesh_mat

    # rack slots: static rack-local transform from USD, composed with the physics rack pose
    rack_prim = stage.GetPrimAtPath(f"{ENV0}/Rack_Left")
    rack_usd = UsdGeom.Xformable(rack_prim).ComputeLocalToWorldTransform(Usd.TimeCode.Default())
    rp = scene["rack_left"].data.root_pos_w[0].cpu().double().numpy()
    rq = scene["rack_left"].data.root_quat_w[0].cpu().double().numpy()
    rack_phys = Gf.Matrix4d().SetRotate(Gf.Quatd(*rq)) * Gf.Matrix4d().SetTranslate(Gf.Vec3d(*rp))
    slots = {}
    for p in Usd.PrimRange(rack_prim):
        if p.GetName().startswith("top_"):
            rel = UsdGeom.Xformable(p).ComputeLocalToWorldTransform(Usd.TimeCode.Default()) * rack_usd.GetInverse()
            slots[p.GetName()] = {"rack_local": list(rel.ExtractTranslation()),
                                  "world_after_warmup10": list((rel * rack_phys).ExtractTranslation())}
    frames["rack_slots"] = slots
    frames["rack_usd_bbox_local"] = [list(v) for v in (lambda r: (r.GetMin(), r.GetMax()))(
        UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default", "render"]).ComputeUntransformedBound(rack_prim).ComputeAlignedRange())]

    # mat, light, mount, cameras, lightbox panels
    frames["mat"] = {"world_usd": world_xf(stage.GetPrimAtPath(f"{ENV0}/Mat"))}
    lp = stage.GetPrimAtPath(LIGHT)
    frames["rect_light"] = {"world_usd": world_xf(lp), "attributes": prim_attrs(lp)}
    mp = stage.GetPrimAtPath(MOUNT)
    frames["camera_mount"] = {"local_ops": {a: val(mp.GetAttribute(a).Get()) for a in (
        "xformOp:translate", "xformOp:orient", "xformOp:scale")} | {"xformOpOrder": val(mp.GetAttribute("xformOpOrder").Get())},
        "world_usd": world_xf(mp)}
    frames["camera_external_D455"] = camera_block(stage, scene, "camera_external_D455", CAM_EXT)
    cm = UsdGeom.Xformable(mp).ComputeLocalToWorldTransform(Usd.TimeCode.Default())
    cc = UsdGeom.Xformable(stage.GetPrimAtPath(CAM_EXT)).ComputeLocalToWorldTransform(Usd.TimeCode.Default())
    rel = cc * cm.GetInverse()
    frames["camera_external_D455"]["camera_in_mount"] = {
        "matrix_row_major_usd": tl(rel), "pos": list(rel.ExtractTranslation()),
        "quat_wxyz": tl(rel.RemoveScaleShear().ExtractRotationQuat())}
    frames["camera_ego"] = camera_block(stage, scene, "camera_ego", None)
    bbc = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default", "render"])
    panels = {}
    for n in PANELS:
        p = stage.GetPrimAtPath(f"{ENV0}/LightStudio/LightBox/{n}")
        if not p:
            continue
        r = bbc.ComputeWorldBound(p).ComputeAlignedRange()
        m = UsdGeom.Xformable(p).ComputeLocalToWorldTransform(Usd.TimeCode.Default())
        pts = UsdGeom.Mesh(p).GetPointsAttr().Get() or []
        panels[n] = {"world_bbox_min": list(r.GetMin()), "world_bbox_max": list(r.GetMax()),
                     "n_points": len(pts),
                     "world_points": [list(m.Transform(Gf.Vec3d(*q))) for q in pts] if len(pts) <= 64 else None,
                     "visibility": UsdGeom.Imageable(p).ComputeVisibility()}
    frames["lightbox_panels"] = panels
    frames["used_layers"] = layer_info(stage)

    # nominal images
    frames["images_nominal"] = {
        "front": save_camera_images(scene, "camera_external_D455", args_cli.out, "nominal_front", depth=True),
        "wrist": save_camera_images(scene, "camera_ego", args_cli.out, "nominal_wrist", depth=False),
        "note": "rendered after the 10 warm-up steps, i.e. the first frame the policy sees",
    }

    # ---------------- seeds ----------------
    vial_term.params["pose_range"] = copy.deepcopy(eval_vial_range)
    seeds = {}
    for k in parse_seeds(args_cli.seeds):
        reseed(k)
        with torch.inference_mode():
            env.reset()
            rec = {"after_reset": objects_block(scene)}
            warmup(env, 10)
            rec["after_warmup10"] = objects_block(scene)
            save_camera_images(scene, "camera_external_D455", seed_dir, f"seed{k:02d}_front", masks=True)
            save_camera_images(scene, "camera_ego", seed_dir, f"seed{k:02d}_wrist", masks=False)
            warmup(env, 50)
            rec["after_warmup60"] = objects_block(scene)
        seeds[str(k)] = rec
        print(f"[C1] seed {k} done", flush=True)
    frames["seeds"] = {"convention": "v0: random/np/torch(+cuda) seeded with k immediately before env.reset(); "
                                     "vial pose_range = Eval ranges, every other DR at centre",
                       "vial_pose_range": eval_vial_range, "by_seed": seeds}
    frames["finished_utc"] = utc()

    path = os.path.join(args_cli.out, "frames_sim.json")
    with open(path, "w") as f:
        json.dump(frames, f, indent=1)
        f.flush()
        os.fsync(f.fileno())
    print(f"[C1] wrote {path}", flush=True)


if __name__ == "__main__":
    try:
        main()
        code = 0
    except Exception:
        import traceback
        traceback.print_exc()
        code = 1
    # the Kit app may not exit cleanly (cf. lerobot_eval.py:251-252); leave hard
    os._exit(code)
