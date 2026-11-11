#!/usr/bin/env python3
"""E3 on a simulated scene set (e.g. gtc results/e1/selection_cases.json, the E1 selection renders): one process.

    python eval_simset.py --gtc <gtc root> --cases results/e1/selection_cases.json --truth results/e1/selection_truth.json \
        --out results/e3/simset_e3.json [--backend torch] [--scene-cache cache/scene.npz]
The nominal camera is the simulation's (the render prim at zero mount offsets, from the C1 dump); the scenes were
rendered with the C920's focal (fx in the truth file). Camera scenes: differential camera mode against the "nominal"
scene's render. Rack scenes: rack mode with the camera at the nominal pose. Writes one Appendix C estimate per scene.
"""
import argparse
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import estimate as E  # noqa: E402
import render as Rn  # noqa: E402
import segment as Sg  # noqa: E402


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--gtc", required=True)
    ap.add_argument("--cases", required=True)
    ap.add_argument("--truth", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--backend", choices=["numpy", "torch"], default="torch")
    ap.add_argument("--scene-cache", default=str(HERE / "cache" / "scene.npz"))
    a = ap.parse_args(argv)
    G = Path(a.gtc)
    tr = json.loads((G / a.truth).read_text())
    fx = float(tr["fx_px"])
    K = np.array([[fx, 0, 320.0], [0, fx, 240.0], [0, 0, 1.0]])       # the renders are ideal pinhole images
    dist = np.zeros(5)
    scene, rig = Rn.load_scene(G / "results" / "c1" / "frames_sim.json", cache=a.scene_cache)
    if a.backend == "torch":
        import render_gpu
        be = render_gpu.TorchBackend(scene)
    else:
        be = E.NumpyBackend(scene)
    R0, C0 = rig.lens(np.zeros(6))
    cases = {c["photo_id"]: c for c in json.loads((G / a.cases).read_text())}

    def cls(pid):
        rgb = cv2.imread(str(G / cases[pid]["photo"]))[:, :, ::-1]
        ri, inside = Sg.undistort(rgb, K, dist)
        return Sg.classify(ri, inside)
    t0 = time.time()
    Rr, Cr, _, _ = E.search_camera_cem(be, fx, R0, C0, cls("nominal"), log=lambda *z: None)
    out = {"backend": a.backend, "version_hash": E.version_hash(), "nominal_reference_vs_sim_pose": E.b13_delta(R0, C0, Rr, Cr),
           "estimates": {}}
    for pid, t in tr["truth"].items():
        ts = time.time()
        if t["rack_delta"] is not None:
            x, _ = E.search_rack_cem(be, fx, R0, C0, cls(pid), log=lambda *z: None)
            est = {"camera_delta": None, "rack_delta": {"x_m": x[0] / 1000, "y_m": x[1] / 1000, "yaw_deg": float(x[2])}}
        else:
            R, C, _, _ = E.search_camera_cem(be, fx, R0, C0, cls(pid), log=lambda *z: None)
            est = {"camera_delta": E.b13_delta(Rr, Cr, R, C), "rack_delta": None}
        est["seconds"] = round(time.time() - ts, 1)
        out["estimates"][pid] = est
        print(f"{pid:24s} {json.dumps({k: v for k, v in est.items() if v is not None}, default=float)[:150]}", flush=True)
    out["total_s"] = round(time.time() - t0, 1)
    (G / a.out).parent.mkdir(parents=True, exist_ok=True)
    (G / a.out).write_text(json.dumps(out, indent=1, default=float))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
