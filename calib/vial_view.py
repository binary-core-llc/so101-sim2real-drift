#!/usr/bin/env python3
"""Live tube placement view (Nov 8): the trial runner's own tube check (shift method, entry 2's 8c: 7.5 mm across and
along, cover 85 %, cap at the right end) on the live front camera against the block reference, per tube in mm, and
which way to slide each tube, until all three pass.

    .venv/bin/python -I calib/vial_view.py --layout L01 [--ref N04-G1_R1] [--pose s1]     # q quits
Why (N04-011): the stencil sits on the mat, and at S1 the mat is about 6.7 mm away from the robot at its front-right
corner and turned 1.44 deg against E, so a stencil-placed tube lands up to about 5 mm off its E target along the tube
(most for the tubes nearest the right wall); with the hand's own scatter the far tube missed 7.5 mm three times.
Place the tubes with the stencil, take the stencil out, then slide each tube as shown here (door off is fine; the
runner's check with the door on stays the one that counts). Push words follow B's E axes: E x + away from the robot,
E y + toward the camera wall; the shift is the tube now minus its target. AIM = within --aim mm both ways (margin for
the door re-seat and the runner's frame). On quit: results/rig/vial_view_last.json and vial_view_last.png.
"""
import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np

GTC = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(GTC / "calib"), str(GTC / "real")]

import camera_lock  # noqa: E402
import capture  # noqa: E402
import live  # noqa: E402
import vial_check as V  # noqa: E402


def push_words(dx, dy, min_mm=1.0):
    """E shift (tube minus target, mm) -> the slide that removes it."""
    out = []
    if abs(dx) >= min_mm:
        out.append(f"{abs(dx):.1f} mm {'toward the robot' if dx > 0 else 'away from the robot'}")
    if abs(dy) >= min_mm:
        out.append(f"{abs(dy):.1f} mm {'toward the right wall' if dy > 0 else 'toward the camera wall'}")
    return ", ".join(out) or "stay"


def tube_lines(res, aim):
    lines, all_aim = [], res.get("pass") is True
    for k, v in res.get("vials", {}).items():
        if "along_mm" not in v:
            lines.append(f"{k}: not found (cover {v.get('cover')})")
            all_aim = False
            continue
        inside = abs(v["along_mm"]) <= aim and abs(v["across_mm"]) <= aim
        all_aim &= inside and v["pass"]
        cap = v.get("cap_frac")
        state = "AIM" if inside and v["pass"] else "pass" if v["pass"] else "FAIL"
        lines.append(f"{k} {state}: along {v['along_mm']:+.1f}, across {v['across_mm']:+.1f} mm, cover {v['cover']:.2f}, "
                     f"cap {'-' if cap is None else f'{cap:.2f}'} -> slide {push_words(*v['shift_E_mm'])}")
    return lines, all_aim


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--layout", required=True)
    ap.add_argument("--ref", default="N04-G1_R1")
    ap.add_argument("--pose", default="s1")
    ap.add_argument("--source", default="camera:front")
    ap.add_argument("--aim", type=float, default=3.0, help="mm both ways shown as AIM (the limits are 7.5 mm)")
    ap.add_argument("--poses-dir", default=str(GTC / "results" / "poses"))
    ap.add_argument("--intrinsics", default=str(GTC / "config" / "c920_intrinsics.json"))
    ap.add_argument("--layouts", default=str(GTC / "config" / "layouts.json"))
    ap.add_argument("--measurements", default=str(GTC / "results" / "rig" / "measurements.jsonl"))
    ap.add_argument("--headless-frames", type=int)
    ap.add_argument("--out", default=str(GTC / "results" / "rig" / "vial_view_last"))
    a = ap.parse_args(argv)
    rdir = GTC / "media" / "real" / "refs" / a.ref
    ref = capture.load_rgb(rdir / "ref_front_median.png")
    sd = np.load(rdir / "ref_front_sd.npy").astype(np.float32)
    cam = V.load_camera(Path(a.poses_dir) / f"{a.pose}.json", a.intrinsics)
    layout = V.find_layout(a.layout, a.layouts)
    model = V.vial_model(a.measurements)
    th = {**V.TH, "method": "shift"}
    if a.source.startswith("camera:"):
        if camera_lock.cmd_apply(a.source.split(":", 1)[1], write=True) != 0:
            raise SystemExit("STOP: camera lock does not read back")
    src = capture.open_source(a.source)
    st = {"rec": None, "view": None}

    def step():
        f = src.read()
        res, vis = V.check(f, ref, sd, layout, cam, model, th)
        lines, ok = tube_lines(res, a.aim)
        head = (f"{a.layout} vs {a.ref} at {a.pose}: " + ("ALL AIM - ready (door on, then the runner)" if ok else
                "runner check PASS (outside AIM)" if res.get("pass") else "runner check FAIL"))
        st["rec"] = {"utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "layout": a.layout,
                     "ref": a.ref, "pose": a.pose, "aim_mm": a.aim, "all_aim": ok, "check": res}
        st["view"] = np.vstack([vis, live.text_panel([head] + lines + ["q quit"], vis.shape[1])])
        if a.headless_frames is not None:
            print("\n".join([head] + lines))
        return st["view"], []

    try:
        live.run(step, {"q": lambda: "quit"}, f"vial view {a.layout}", headless=a.headless_frames is not None,
                 max_frames=a.headless_frames)
    finally:
        src.close()
        if st["rec"] is not None:
            Path(a.out).parent.mkdir(parents=True, exist_ok=True)
            Path(a.out + ".json").write_text(json.dumps(st["rec"], indent=1, default=str))
            capture.save_rgb(a.out + ".png", st["view"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
