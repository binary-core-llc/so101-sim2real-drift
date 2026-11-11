#!/usr/bin/env python3
"""Live light view (Nov 6): the box light now against a reference, overall and by part of the view, so the light (and
any room light leaking in) can be set back to the reference's state. The runner's light check allows +-5 % overall.

    .venv/bin/python -I calib/light_view.py --ref N04-R0_R0_old_20261107T010503Z     # this morning's; q quits
Ratios are means over the reference's static pixels (outside the current block reference's ignore zones), mean of the
last 5 frames. Parts: left third (camera-wall side, back wall), middle, right third (robot and door side), and the
light-log patch (450,40,15,15). The inset is the ratio map: blue darker, green equal, red brighter.
"""
import argparse
import collections
import sys
from pathlib import Path

import cv2
import numpy as np

GTC = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(GTC / "calib")]

import capture  # noqa: E402
import live  # noqa: E402


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", default="N04-R0_R0_old_20261107T010503Z")
    ap.add_argument("--mask-ref", default="N04-R0_R0", help="reference whose ignore zones are left out")
    ap.add_argument("--source", default="camera:front")
    ap.add_argument("--headless-frames", type=int)
    a = ap.parse_args(argv)
    refs = GTC / "media" / "real" / "refs"
    ref = capture.load_rgb(refs / a.ref / "ref_front_median.png").astype(np.float32)
    keep = ~(cv2.imread(str(refs / a.mask_ref / "ignore_mask.png"), cv2.IMREAD_GRAYSCALE) > 0)
    h, w = keep.shape
    parts = {"left": np.s_[:, : w // 3], "middle": np.s_[:, w // 3: 2 * w // 3], "right": np.s_[:, 2 * w // 3:]}
    roi = np.s_[40:55, 450:465]
    src = capture.open_source(a.source)
    hist = collections.deque(maxlen=5)
    st = {"lines": []}

    def step():
        f = src.read()
        g = f.astype(np.float32)
        r = {"all": g[keep].mean() / ref[keep].mean(), "patch": g[roi].mean() / ref[roi].mean()}
        for k, s in parts.items():
            m = keep[s]
            r[k] = g[s][m].mean() / ref[s][m].mean()
        hist.append(r)
        mr = {k: float(np.mean([x[k] for x in hist])) for k in r}
        ok = abs(mr["all"] - 1) <= 0.02 and all(abs(mr[k] - 1) <= 0.03 for k in parts)
        lines = [f"overall {mr['all']:.3f}   (runner check: within 0.95-1.05)",
                 f"left {mr['left']:.3f}   middle {mr['middle']:.3f}   right {mr['right']:.3f}   patch {mr['patch']:.3f}",
                 "MATCHES THE REFERENCE (overall within 2 %, each part within 3 %)" if ok else
                 ("brighter than the reference: extra light (room lamps, roof slot or hole, door)" if mr["all"] > 1.02 else
                  "darker than the reference" if mr["all"] < 0.98 else "overall close; parts differ: light placed or aimed differently")]
        ratio = (g.mean(axis=2) + 1) / (ref.mean(axis=2) + 1)
        heat = cv2.applyColorMap(np.clip((ratio - 0.5) / 1.5 * 255, 0, 255).astype(np.uint8), cv2.COLORMAP_JET)
        out = f.copy()
        small = cv2.cvtColor(cv2.resize(heat, (w // 3, h // 3)), cv2.COLOR_BGR2RGB)
        out[h - h // 3:, w - w // 3:] = small
        st["lines"] = lines
        return live.put_lines(out, lines + ["q quit"], scale=0.5), lines

    try:
        live.run(step, {"q": lambda: "quit"}, f"light view against {a.ref}", headless=a.headless_frames is not None,
                 max_frames=a.headless_frames)
    finally:
        src.close()
        print("\n".join(st["lines"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
