#!/usr/bin/env python3
"""Live overlay (T20): the simulated reference drawn over the undistorted live C920x view.

    .venv/bin/python -I calib/overlay.py                              # C920x at S1 vs the sim nominal; D455 values
    .venv/bin/python -I calib/overlay.py --intrinsics config/c920_intrinsics.json
    .venv/bin/python -I calib/overlay.py --ref sim_r0 ...             # the sim render at the R0 pose (Nov 3)
    .venv/bin/python -I calib/overlay.py --camera wrist [--intrinsics config/wrist_intrinsics.json]   # V19
Keys: e edges on/off, b blend the sim image on/off, +/- blend amount, s save a snapshot, q quit.

The live frame is remapped into the sim camera (pinhole fx = fy = 514.67 px, centre (320, 240), from the C1
dump) with cv2.initUndistortRectifyMap(K_c920, dist, None, K_sim): distortion removed and the C920x focal and
principal point replaced by the sim's, pose unchanged (B 3.6, with Kp = K_sim so it lines up with the D455
render). Without --intrinsics the frame is shown as is, i.e. as if the C920x had the D455's intrinsics.
Reference edges come from the sim instance masks: walls and floor, mat, rack, robot, vials.
"""
import argparse
import ast
import datetime as dt
import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))  # sibling modules (python -I skips the script dir)

import capture  # noqa: E402
import live  # noqa: E402

GTC = Path(__file__).resolve().parents[1]
REFS = {"sim_nominal": GTC / "results" / "c1" / "nominal_front",
        "sim_r0": GTC / "results" / "overlay_refs" / "sim_r0_front",
        "sim_wrist": GTC / "results" / "c1" / "nominal_wrist"}         # wrist at the sim start pose (after warm-up)
SIM_CAMERA = {"front": "camera_external_D455", "wrist": "camera_ego"}
# (name, label substring, colour, outline each instance separately) - each box panel separately, so the
# floor-wall lines show
CLASSES = [("walls/floor", "/LightStudio/LightBox/", (255, 0, 255), True), ("mat", "/Mat/", (0, 220, 255), False),
           ("rack", "/Rack_Left/", (0, 60, 255), False), ("robot", "/Robot/", (255, 40, 0), False),
           ("vials", "/Vial_", (60, 255, 60), False)]


def k_sim(camera="front"):
    """The sim camera's pinhole K from the C1 dump: front fx 514.67, wrist fx 412.31 (centred, 640x480)."""
    f = json.loads((GTC / "results" / "c1" / "frames_sim.json").read_text())
    return np.array(f[SIM_CAMERA[camera]]["tiled_camera"]["intrinsic_matrices"], dtype=np.float64)


def load_ref(stem):
    stem = Path(stem)
    rgb_p = next(p for p in (Path(f"{stem}_rgb.png"), Path(f"{stem}.png")) if p.exists())
    rgb = capture.load_rgb(rgb_p)
    seg = cv2.cvtColor(cv2.imread(f"{stem}_instance_rgba.png", cv2.IMREAD_UNCHANGED), cv2.COLOR_BGRA2RGBA)
    labels = json.loads(Path(f"{stem}_instance_labels.json").read_text())
    edges = np.zeros_like(rgb)
    for _, tag, color, each in CLASSES:
        masks = [np.all(seg == np.array(ast.literal_eval(key), np.uint8), axis=2).astype(np.uint8)
                 for key, path in labels.items() if tag in path and "camera_mount" not in path]
        if not each and masks:
            masks = [np.bitwise_or.reduce(masks)]
        for m in masks:
            cs, _ = cv2.findContours(m, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
            cv2.drawContours(edges, cs, -1, color, 1)
    return rgb, edges


class Undistorter:
    def __init__(self, intrinsics_path, K_target):
        self.K_target = K_target
        if intrinsics_path:
            j = json.loads(Path(intrinsics_path).read_text())
            self.K, self.dist = np.array(j["K"]), np.array(j["dist"])
            self.maps = cv2.initUndistortRectifyMap(self.K, self.dist, None, K_target, (640, 480), cv2.CV_32FC1)
            self.label = f"intrinsics {Path(intrinsics_path).name} -> sim pinhole fx {K_target[0, 0]:.1f}"
        else:
            self.maps, self.label = None, f"no intrinsics yet: frame shown as if it had the sim values (fx {K_target[0, 0]:.1f})"

    def __call__(self, rgb):
        return rgb if self.maps is None else cv2.remap(rgb, *self.maps, cv2.INTER_LINEAR)


def compose(frame_u, ref_rgb, edges, show_edges=True, blend=0.0):
    out = frame_u.astype(np.float32)
    if blend > 0:
        out = (1 - blend) * out + blend * ref_rgb.astype(np.float32)
    out = out.astype(np.uint8)
    if show_edges:
        m = edges.any(-1)
        out[m] = edges[m]
    return out


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--camera", default="front", choices=["front", "wrist"])
    ap.add_argument("--ref", default=None, help="sim_nominal (front default), sim_r0, sim_wrist (wrist default), or a path stem")
    ap.add_argument("--intrinsics", default=None)
    ap.add_argument("--source", default=None, help="default camera:<camera>")
    ap.add_argument("--headless-frames", type=int, default=None)
    ap.add_argument("--save", default=None, help="headless: write the last composed frame here")
    a = ap.parse_args(argv)
    a.ref = a.ref or ("sim_wrist" if a.camera == "wrist" else "sim_nominal")
    a.source = a.source or f"camera:{a.camera}"
    ref_rgb, edges = load_ref(REFS.get(a.ref, a.ref))
    und = Undistorter(a.intrinsics, k_sim(a.camera))
    src = capture.open_source(a.source)
    st = {"edges": True, "blend": 0.0, "last": None, "raw": None}

    def step():
        st["raw"] = src.read()
        st["last"] = compose(und(st["raw"]), ref_rgb, edges, st["edges"], st["blend"])
        lines = [f"ref {a.ref}; {und.label}", f"blend {st['blend']:.1f}   e edges  b blend  +/-  s save  q quit"]
        return live.put_lines(st["last"], lines, scale=0.45), lines

    def save():
        stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        d = GTC / "results" / "overlay"
        capture.save_rgb(d / f"overlay_{a.ref}_{stamp}.png", st["last"])
        capture.save_rgb(GTC / "media" / "overlay" / f"raw_{stamp}.png", st["raw"])
        print(f"saved {d}/overlay_{a.ref}_{stamp}.png")

    keys = {"e": lambda: st.__setitem__("edges", not st["edges"]),
            "b": lambda: st.__setitem__("blend", 0.0 if st["blend"] else 0.5),
            "+": lambda: st.__setitem__("blend", min(1.0, st["blend"] + 0.1)),
            "-": lambda: st.__setitem__("blend", max(0.0, st["blend"] - 0.1)), "s": save, "q": lambda: "quit"}
    try:
        live.run(step, keys, f"overlay {a.ref}", headless=a.headless_frames is not None, max_frames=a.headless_frames)
    finally:
        src.close()
    if a.save and st["last"] is not None:
        capture.save_rgb(a.save, st["last"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
