#!/usr/bin/env python3
"""Framing check on probe frames: is the rack and every vial fully inside the front image after warm-up?

    .venv/bin/python -I tools/framing_check.py results/explore_v1/probe_explore_v1_framing.jsonl \
        media/explore_v1/probe_explore_v1_framing [out.json]

Per probe row (set, seed) and object (rack, vial_1..3), from the instance mask:
  in      visible, no mask pixel on the image border
  cut     visible and touching the border (partly out of frame)
  out     no mask pixels and the object origin projects outside the image (or behind the camera)
  hidden  no mask pixels but the origin projects inside the image (occluded, e.g. by the arm)
The projection uses the camera's world pose after warm-up (camera_after_warmup10) and a pinhole with
fx = fy = focal / horizontalAperture * width, centre at the image centre; it is a cross-check, the mask decides.
"""
import ast
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import cv2
import numpy as np

OBJ = {"rack_left": "/Rack_Left/", "vial_1": "/Vial_1/", "vial_2": "/Vial_2/", "vial_3": "/Vial_3/"}


def rot(q):
    w, x, y, z = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
                     [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
                     [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)]])


def project(p, cam, fx, W, H):
    c = rot(cam["quat_wxyz"]).T @ (np.array(p) - np.array(cam["pos"]))  # USD camera: -Z forward, +Y up
    if c[2] >= 0:
        return None
    return (W / 2 + fx * c[0] / -c[2], H / 2 - fx * c[1] / -c[2])


def masks(stem):
    seg = cv2.cvtColor(cv2.imread(f"{stem}_front_instance_rgba.png", cv2.IMREAD_UNCHANGED), cv2.COLOR_BGRA2RGBA)
    lab = json.load(open(f"{stem}_front_instance_labels.json"))
    out = {o: np.zeros(seg.shape[:2], bool) for o in OBJ}
    for key, path in lab.items():
        for o, tag in OBJ.items():
            if tag in path:
                out[o] |= np.all(seg == np.array(ast.literal_eval(key), np.uint8), axis=2)
    return out


def main(jsonl, media, dst=None):
    rows = [json.loads(l) for l in open(jsonl)]
    res = []
    for r in rows:
        m = masks(f"{media}/{r['set']}_seed{r['seed']:03d}")
        H, W = next(iter(m.values())).shape
        rb = r["readback"]["camera_external"]
        fx = rb["focal_mm"] / rb["hap_mm"] * W
        rec = {"set": r["set"], "seed": r["seed"]}
        for o, mk in m.items():
            uv = project(r["objects_after_warmup10"][o]["pos"], r["camera_after_warmup10"], fx, W, H)
            inside = uv is not None and 0 <= uv[0] < W and 0 <= uv[1] < H
            if mk.any():
                ys, xs = np.nonzero(mk)
                margin = int(min(xs.min(), ys.min(), W - 1 - xs.max(), H - 1 - ys.max()))
                state = "in" if margin > 0 else "cut"
                bbox = [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]
            else:
                margin, bbox, state = None, None, "hidden" if inside else "out"
            rec[o] = {"state": state, "px": int(mk.sum()), "margin_px": margin, "bbox": bbox,
                      "proj_uv": [round(uv[0], 1), round(uv[1], 1)] if uv else None}
        rec["all_in"] = all(rec[o]["state"] == "in" for o in OBJ)
        res.append(rec)
    by = defaultdict(list)
    for rec in res:
        by[rec["set"]].append(rec)
    summary = {}
    print(f"{'set':24s} seeds all-in | " + " | ".join(f"{o}: in/cut/out/hidden, min margin" for o in OBJ))
    for s, recs in by.items():
        line = {"seeds": len(recs), "all_in": sum(r["all_in"] for r in recs),
                "seeds_not_all_in": [r["seed"] for r in recs if not r["all_in"]]}
        cells = []
        for o in OBJ:
            c = Counter(r[o]["state"] for r in recs)
            mg = [r[o]["margin_px"] for r in recs if r[o]["margin_px"] is not None]
            line[o] = {**{k: c.get(k, 0) for k in ("in", "cut", "out", "hidden")}, "min_margin_px": min(mg) if mg else None}
            cells.append(f"{c.get('in', 0)}/{c.get('cut', 0)}/{c.get('out', 0)}/{c.get('hidden', 0)}, {line[o]['min_margin_px']}")
        summary[s] = line
        print(f"{s:24s} {len(recs):5d} {line['all_in']:6d} | " + " | ".join(f"{x:>26s}" for x in cells))
    if dst:
        Path(dst).write_text(json.dumps({"source": str(jsonl), "summary": summary, "rows": res}, indent=1))
    return summary


if __name__ == "__main__":
    main(*sys.argv[1:4])
