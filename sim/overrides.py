"""Sweep overrides: every randomization fixed at its centre; only the cell's factor changes.

An override dict (all keys optional; missing = centre):
  camera:        {"x","y","z" (m), "roll","pitch","yaw" (rad)}  code-level camera_mount offsets
                 (translation in the LightBox frame, rotation about the mount's local axes,
                 resets.py:173-188). Physical names come from the T06 sign table.
  camera_focal_mm: external D455 focal length (USD value 1.93 mm; HFOV 63.74 deg at hAp 2.4 mm)
  exposure_ev:   box light exposure (Eval range -3..+1; centre -1)
  mat_yaw_rad:   (Eval range +-0.1; centre 0)
  wrist_focal_mm:(Eval range 12-15; centre 13.5)
  rack:          {"x","y" (m), "yaw" (rad)} offsets of the rack's corner origin from (0.18, 0.08)
  rack_placement_prob: (course default 0.33; centre/sweep 0)
  vials:         "eval" (default: the course vial pose ranges, drawn per seed = the layout) or "fixed"

Terms are never deleted: a fixed value is a degenerate range (v, v), so every cell draws the
same random numbers in the same order (common random numbers, D_software C3).
"""
import copy

CENTRE = {
    "camera": {"x": 0.0, "y": 0.0, "z": 0.0, "roll": 0.0, "pitch": 0.0, "yaw": 0.0},
    "camera_focal_mm": 1.93,
    "exposure_ev": -1.0,
    "mat_yaw_rad": 0.0,
    "wrist_focal_mm": 13.5,
    "rack": {"x": 0.0, "y": 0.0, "yaw": 0.0},
    "rack_placement_prob": 0.0,
    "vials": "eval",
}
EVAL_VIAL_RANGE = {"x": (-0.04, 0.04), "y": (-0.01, 0.01), "roll": (-0.3, 0.3), "yaw": (0.0, 0.0)}
EXT_FOCAL_TERM = "reset_camera_external_focal"


def resolve(ov):
    """Merge an override dict onto the centre; unknown keys are an error."""
    out = copy.deepcopy(CENTRE)
    for k, v in (ov or {}).items():
        if k not in out:
            raise KeyError(f"unknown override key {k!r}")
        if isinstance(out[k], dict):
            bad = set(v) - set(out[k])
            if bad:
                raise KeyError(f"unknown {k} keys {bad}")
            out[k].update(v)
        else:
            out[k] = v
    return out


def add_external_focal_term(env_cfg):
    """Add the external-camera focal EventTerm (every cell has it, so RNG order is shared)."""
    from isaaclab.managers import EventTermCfg as EventTerm
    from isaaclab.managers import SceneEntityCfg
    from sim_to_real_so101.mdp import randomize_camera_focal_length
    setattr(env_cfg.events, EXT_FOCAL_TERM, EventTerm(
        func=randomize_camera_focal_length, mode="reset",
        params={"focal_length_range": (1.93, 1.93), "asset_cfg": SceneEntityCfg("camera_external_D455")}))


def write_params(get, r):
    """Write resolved overrides into event-term params. get(name) -> the term's params dict."""
    c = r["camera"]
    p = get("reset_camera_external_pose")
    p["pos_range"] = {k: (c[k], c[k]) for k in ("x", "y", "z")}
    p["rot_range"] = {k: (c[k], c[k]) for k in ("roll", "pitch", "yaw")}
    get(EXT_FOCAL_TERM)["focal_length_range"] = (r["camera_focal_mm"],) * 2
    get("reset_lightbox_light_exposure")["exposure_range"] = (r["exposure_ev"],) * 2
    get("reset_mat_rotation")["yaw_range"] = (r["mat_yaw_rad"],) * 2
    get("reset_camera_ego_fov")["focal_length_range"] = (r["wrist_focal_mm"],) * 2
    v = get("reset_vials_setup")
    v["rack_pose_range"] = {k: (r["rack"][k], r["rack"][k]) for k in ("x", "y", "yaw")}
    v["rack_placement_prob"] = r["rack_placement_prob"]
    if r["vials"] == "eval":
        v["pose_range"] = copy.deepcopy(EVAL_VIAL_RANGE)
    elif r["vials"] == "fixed":
        v["pose_range"] = {k: (0.0, 0.0) for k in EVAL_VIAL_RANGE}
    else:
        raise ValueError(f"vials must be 'eval' or 'fixed', got {r['vials']!r}")


def apply_to_cfg(env_cfg, ov):
    """Before gym.make: add the focal term and write the resolved overrides into the cfg."""
    add_external_focal_term(env_cfg)
    r = resolve(ov)
    write_params(lambda name: getattr(env_cfg.events, name).params, r)
    return r


def apply_to_env(env, ov):
    """At runtime (probe mode): same params, written into the live event manager's term cfgs."""
    r = resolve(ov)
    em = env.unwrapped.event_manager
    write_params(lambda name: em.get_term_cfg(name).params, r)
    return r
