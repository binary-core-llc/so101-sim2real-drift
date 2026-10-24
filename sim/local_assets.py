"""T32: load the course scene through our wrapper layers so nothing is fetched from NVIDIA's S3.

The wrappers (assets/local/*.local.usda, made by tools/make_local_wrappers.py) sublayer the
unmodified course USDs and point their remote MDLs and the D455 payload at the local mirror
(~/sim2real/assets_mirror, mounted at /workspace/assets_mirror by sim/run_sim.sh).
"""
import os

WRAPPERS = "/workspace/gtc/assets/local"
MIRROR = "/workspace/assets_mirror"


def apply_local_assets(env_cfg):
    """Point every scene asset that has remote references at its local wrapper. Returns a log dict."""
    if not os.path.isdir(MIRROR):
        raise FileNotFoundError(f"asset mirror not mounted at {MIRROR} (see sim/run_sim.sh)")
    s = env_cfg.scene
    targets = {
        "lightstudio": (s.lightstudio.spawn, "lightbox-simple.local.usda"),
        "mat": (s.mat.spawn, "mat.local.usda"),
        "robot": (s.robot.spawn, "SO-ARM101-USD.local.usda"),
        "vial_1": (s.vial_1.spawn, "Vial_opaque.local.usda"),
        "vial_2": (s.vial_2.spawn, "Vial_opaque.local.usda"),
        "vial_3": (s.vial_3.spawn, "Vial_opaque.local.usda"),
    }
    log = {}
    for name, (spawn, wrapper) in targets.items():
        old = spawn.usd_path
        expect = os.path.basename(old).rsplit(".", 1)[0]
        assert wrapper.startswith(expect), f"{name}: course file {old} does not match wrapper {wrapper}"
        spawn.usd_path = f"{WRAPPERS}/{wrapper}"
        log[name] = {"course": old, "wrapper": spawn.usd_path}
    return log
