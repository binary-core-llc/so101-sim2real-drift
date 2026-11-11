#!/usr/bin/env python3
"""E3 renderer benchmark and agreement: render.py (numpy, CPU) against render_gpu.py (CUDA PyTorch).

    python bench.py --frames frames_sim.json --cache cache/scene.npz [--n 64] [--out bench.json]
Same N random camera poses around the simulation's camera (lens-frame sd 12 mm, 4 deg) and N random rack poses; per
resolution: renders per second for each backend (GPU synchronised, one warm-up pass excluded, median of 3 passes) and
the share of pixels where the two class images agree.
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import estimate as E  # noqa: E402
import render as Rn  # noqa: E402


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", required=True)
    ap.add_argument("--cache", required=True)
    ap.add_argument("--n", type=int, default=64)
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    import torch
    import render_gpu as G
    scene, rig = Rn.load_scene(a.frames, cache=a.cache)
    R0, C0 = rig.lens(np.zeros(6))
    rng = np.random.default_rng(1)
    P = rng.standard_normal((a.n, 6)) * [12, 12, 12, 4, 4, 2.5]
    Q = rng.standard_normal((a.n, 3)) * [20, 20, 8]
    cpu, gpu = E.NumpyBackend(scene), G.TorchBackend(scene)
    out = {"n": a.n, "device": torch.cuda.get_device_name(0), "levels": {}}
    for w, h in E.LEVELS:
        f = 630.62 * w / 640
        row = {}
        for name, be in (("cpu", cpu), ("gpu", gpu)):
            for kind, fn in (("camera", lambda: be.camera_images(R0, C0, P, f, w, h)),
                             ("rack", lambda: be.rack_images(R0, C0, Q, f, w, h))):
                fn()                                             # warm-up
                ts = []
                for _ in range(3):
                    torch.cuda.synchronize()
                    t = time.time()
                    ims = fn()
                    torch.cuda.synchronize()
                    ts.append(time.time() - t)
                row[f"{kind}_{name}_renders_per_s"] = round(a.n / float(np.median(ts)), 1)
                row[f"_{kind}_{name}"] = ims
        for kind in ("camera", "rack"):
            A, B = row.pop(f"_{kind}_cpu"), row.pop(f"_{kind}_gpu")
            row[f"{kind}_pixel_agreement"] = round(float(np.mean([np.mean(x == y) for x, y in zip(A, B)])), 6)
            row[f"{kind}_speedup"] = round(row[f"{kind}_gpu_renders_per_s"] / row[f"{kind}_cpu_renders_per_s"], 1)
        out["levels"][f"{w}x{h}"] = row
        print(f"{w}x{h}: " + ", ".join(f"{k} {v}" for k, v in row.items()))
    if a.out:
        Path(a.out).write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
