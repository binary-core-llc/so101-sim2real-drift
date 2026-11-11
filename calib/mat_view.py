#!/usr/bin/env python3
"""Live mat placement view (Nov 6): the block reference's mat edges drawn over the live front image, each edge's
offset in px and which way to slide the mat, until every edge is within --target px (the trial check blocks at 1.5).

    .venv/bin/python -I calib/mat_view.py --ref N04-R0_R0          # q quits
Same edge measure as the trial runner's mat check (real/trial_runner.py mat_check): per scan line the strongest
mat/floor step near the reference line, a line fit per edge, the shift at two places. Mean of the last 5 frames.
Green = reference edge, magenta = edge seen now. Front view at R0: the robot is at the image's right (front edge =
robot side), the far edge is the mat's right edge (away from the camera wall), the back edge faces the back wall.
"""
import argparse
import collections
import datetime as dt
import json
import sys
from pathlib import Path

import cv2
import numpy as np

GTC = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(GTC / "calib"), str(GTC / "real")]

import capture  # noqa: E402
import live  # noqa: E402
import trial_runner as T  # noqa: E402

LABELS = {"back": ("back edge", "right end", "nearer the camera"),
          "front": ("front edge (robot side)", "right end", "nearer the camera"),
          "far": ("right edge (far)", "back part", "front part")}


def ref_lines(gray):
    out = {}
    for name, e in T.MAT_EDGES.items():
        m, q, _ = T.fit_edge(T.edge_points(gray, e))
        out[name] = (m, q)
    return out


def measure(gray, ref):
    res = {}
    for name, e in T.MAT_EDGES.items():
        m0, q0 = ref[name]
        p = T.edge_points(gray, e, guess=lambda s: m0 * s + q0)
        if len(p) < 0.5 * len(e["lines"]):
            res[name] = None
            continue
        m1, q1, _ = T.fit_edge(p)
        res[name] = ((m1, q1), [float((m1 * s + q1) - (m0 * s + q0)) for s in e["at"]])
    return res


def draw(img, e, line, color):
    m, q = line
    s0, s1 = e["lines"][0], e["lines"][-1]
    pts = [(m * s + q, s) for s in (s0, s1)] if e["axis"] == "row" else [(s, m * s + q) for s in (s0, s1)]
    cv2.line(img, tuple(int(round(v)) for v in pts[0]), tuple(int(round(v)) for v in pts[1]), color, 1, cv2.LINE_AA)


def advice(sh, target):
    """Plain directions from the mean shifts (px). Image +x = toward the robot; image +y = toward the camera wall."""
    tips = []
    u = [v for k in ("back", "front") if sh.get(k) for v in sh[k]]
    if u and abs(np.mean(u)) > target / 2:
        tips.append(f"slide {'AWAY FROM' if np.mean(u) > 0 else 'TOWARD'} the robot {abs(np.mean(u)):.1f} px")
    if sh.get("far") and abs(np.mean(sh["far"])) > target / 2:
        tips.append(f"slide toward the {'RIGHT' if np.mean(sh['far']) > 0 else 'LEFT (camera)'} wall "
                    f"{abs(np.mean(sh['far'])):.1f} px")
    turn = [a - b for k in ("back", "front") if sh.get(k) for a, b in [sh[k]]]
    if turn and abs(np.mean(turn)) > target / 2:
        tips.append(f"turn: right end {'AWAY FROM' if np.mean(turn) > 0 else 'TOWARD'} the robot")
    return tips


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", default="N04-R0_R0")
    ap.add_argument("--source", default="camera:front")
    ap.add_argument("--target", type=float, default=0.75)
    ap.add_argument("--headless-frames", type=int)
    a = ap.parse_args(argv)
    ref_rgb = capture.load_rgb(GTC / "media" / "real" / "refs" / a.ref / "ref_front_median.png")
    ref = ref_lines(cv2.cvtColor(ref_rgb, cv2.COLOR_RGB2GRAY))
    src = capture.open_source(a.source)
    hist = collections.deque(maxlen=5)
    st = {"rec": None, "lines": []}

    def step():
        f = src.read()
        out = f.copy()
        r = measure(cv2.cvtColor(f, cv2.COLOR_RGB2GRAY), ref)
        hist.append(r)
        sh, lines = {}, []
        for name, e in T.MAT_EDGES.items():
            draw(out, e, ref[name], (0, 255, 0))
            vals = [h[name][1] for h in hist if h.get(name)]
            if r.get(name):
                draw(out, e, r[name][0], (255, 0, 255))
            lab, p0, p1 = LABELS[name]
            if len(vals) < 3:
                lines.append(f"{lab}: not seen (hands in the way, or more than 12 px off: move the mat closer by eye)")
                continue
            sh[name] = list(np.mean(vals, axis=0))
            ok = max(abs(v) for v in sh[name]) <= a.target
            lines.append(f"{'OK ' if ok else '   '}{lab}: {p0} {sh[name][0]:+.2f}, {p1} {sh[name][1]:+.2f} px")
        done = len(sh) == 3 and all(max(abs(v) for v in s) <= a.target for s in sh.values())
        lines += ["ALL EDGES WITHIN %.2f px: hands out, door on" % a.target] if done else advice(sh, a.target)
        st["lines"] = lines
        st["rec"] = {"utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "ref": a.ref,
                     "shift_px": sh, "within_target": done, "target_px": a.target}
        return live.put_lines(out, lines + ["q quit"], scale=0.5), lines

    try:
        live.run(step, {"q": lambda: "quit"}, f"mat view against {a.ref}", headless=a.headless_frames is not None,
                 max_frames=a.headless_frames)
    finally:
        src.close()
        if st["rec"]:
            print("\n".join(st["lines"]))
            out = GTC / "results" / "rig" / "mat_view_last.json"
            out.write_text(json.dumps(st["rec"], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
