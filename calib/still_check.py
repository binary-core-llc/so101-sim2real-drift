#!/usr/bin/env python3
"""Camera-still check across a box change (Nov 5, D12): the C920x's view of an untouched ChArUco board before and
after, e.g. the roof going back on after the R0 gauge setting. Image space only, so it needs no intrinsics.

    .venv/bin/python -I calib/still_check.py before --tag r0_roof [--square-mm SQ]
    .venv/bin/python -I calib/still_check.py after --tag r0_roof

before: freezes the C920x's autofocus at its current value (so a refocus can't look like a move), averages the
ChArUco corners over 20 frames, saves them and the mean frame. after: the same capture, then the displacement of
every corner seen both times (max, median) and a similarity fit (shift, rotation, scale); then the autofocus goes
back as it was found. Exposure stays automatic (the roof changes the light; corners don't depend on it).
Verdict as drift_check.py and B 8 step 2: max displacement <= 1.0 px PASS (still), 1-2 px WARN, > 2 px FAIL; on
WARN or FAIL the camera counts as moved and is set again. A box shift moves the board too and reads as a move.
Shows no target and no sim view (R0 is set by tape and gauge only, G8).
Writes results/still/<tag>_{before,after}.json and media/still/<tag>_{before,after}.png.
"""
import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))  # sibling modules (python -I skips the script dir)

import capture  # noqa: E402
import charuco as C  # noqa: E402
import v4l2  # noqa: E402

GTC = Path(__file__).resolve().parents[1]
_TEST = os.environ.get("GTC_STILL_DIR")                          # override: tests only
OUT, MEDIA = (Path(_TEST), Path(_TEST) / "media") if _TEST else (GTC / "results" / "still", GTC / "media" / "still")
PASS_PX, WARN_PX, MIN_COMMON = 1.0, 2.0, 15     # drift_check.py / B 8 step 2 bands


def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def freeze_focus(node):
    """Autofocus off at its current value; returns what to restore (None if the camera has no autofocus)."""
    with v4l2.Device(node) as dev:
        af, fa = v4l2.CID["focus_automatic_continuous"], v4l2.CID["focus_absolute"]
        if not (dev.has(af) and dev.has(fa)):
            return None
        was = {"focus_automatic_continuous": dev.get(af), "focus_absolute": dev.get(fa)}
        dev.set(af, 0)
        dev.set(fa, was["focus_absolute"])
        return was


def restore_focus(node, was):
    with v4l2.Device(node) as dev:
        dev.set(v4l2.CID["focus_automatic_continuous"], was["focus_automatic_continuous"])


def grab(src, n, square_mm):
    frames = [src.read() for _ in range(n)]
    avg = C.average_corners([C.Detector(square_mm).detect(f) for f in frames], min_frac=0.75)
    if avg is None or len(avg["ids"]) < MIN_COMMON:
        raise SystemExit(f"STOP: the board is not seen well enough (fewer than {MIN_COMMON} corners in 75 % of the "
                         "frames): hands, arm, glare or the board out of view?")
    mean = np.mean(frames, axis=0).round().astype(np.uint8)
    return {"ids": avg["ids"].tolist(), "img": avg["img"].tolist(), "corner_frame_sd_px": avg["frame_sd_px"],
            "n_frames": n, "n_frames_detected": avg["n_frames"]}, mean


def compare(a, b):
    ia, ib = dict(zip(a["ids"], a["img"])), dict(zip(b["ids"], b["img"]))
    common = sorted(set(ia) & set(ib))
    if len(common) < MIN_COMMON:
        raise SystemExit(f"STOP: only {len(common)} corners seen both times (need {MIN_COMMON})")
    pa, pb = np.array([ia[i] for i in common]), np.array([ib[i] for i in common])
    d = np.linalg.norm(pb - pa, axis=1)
    M, _ = cv2.estimateAffinePartial2D(pa, pb, method=cv2.LMEDS)
    res = {"n_common": len(common), "max_px": float(d.max()), "median_px": float(np.median(d)),
           "worst_corner_id": int(common[int(d.argmax())])}
    if M is not None:
        s = float(np.hypot(M[0, 0], M[1, 0]))
        res.update({"fit_shift_px": [float(M[0, 2]), float(M[1, 2])], "fit_rotation_deg": float(np.degrees(np.arctan2(M[1, 0], M[0, 0]))),
                    "fit_scale": s})
    res["verdict"] = "PASS" if res["max_px"] <= PASS_PX else "WARN" if res["max_px"] <= WARN_PX else "FAIL"
    return res


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["before", "after"])
    ap.add_argument("--tag", required=True)
    ap.add_argument("--source", default="camera:front")
    ap.add_argument("--frames", type=int, default=20)
    ap.add_argument("--square-mm", type=float, default=30.0)
    a = ap.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    first = OUT / f"{a.tag}_before.json"
    if a.cmd == "after" and not first.exists():
        raise SystemExit(f"STOP: no {first.relative_to(GTC)}; run 'before' first")
    src = capture.open_source(a.source)
    camera = a.source.startswith("camera:")
    rec = {"utc": utc(), "tag": a.tag, "step": a.cmd, "source": src.identity, "square_mm": a.square_mm}
    try:
        if camera and a.cmd == "before":
            rec["focus_frozen_from"] = freeze_focus(src.node)
            for _ in range(10):                            # let the new focus setting take effect
                src.read()
        got, mean = grab(src, a.frames, a.square_mm)
        rec.update(got)
        if a.cmd == "after":
            b0 = json.loads(first.read_text())
            rec["compare"] = compare(b0, rec)
            if camera and b0.get("focus_frozen_from"):
                restore_focus(src.node, b0["focus_frozen_from"])
                rec["focus_restored"] = b0["focus_frozen_from"]
    finally:
        src.close()
    (OUT / f"{a.tag}_{a.cmd}.json").write_text(json.dumps(rec, indent=1))
    capture.save_rgb(MEDIA / f"{a.tag}_{a.cmd}.png", mean)
    if a.cmd == "before":
        print(f"{a.tag} before: {len(rec['ids'])} corners, frame noise {rec['corner_frame_sd_px']:.3f} px; autofocus "
              f"{'frozen at ' + str(rec['focus_frozen_from']['focus_absolute']) if rec.get('focus_frozen_from') else 'not touched'}."
              " Don't touch the board until 'after'.")
        return 0
    c = rec["compare"]
    fit = (f"; fit shift ({c['fit_shift_px'][0]:+.2f}, {c['fit_shift_px'][1]:+.2f}) px, rotation "
           f"{c['fit_rotation_deg']:+.3f} deg, scale {c['fit_scale']:.5f}") if "fit_scale" in c else ""
    word = {"PASS": "camera still", "WARN": "moved a little: set it again", "FAIL": "moved: set it again"}[c["verdict"]]
    print(f"{a.tag}: {c['n_common']} corners, max {c['max_px']:.2f} px (corner {c['worst_corner_id']}), median "
          f"{c['median_px']:.2f} px{fit}")
    print(f"STILL {c['verdict']}: {word} (PASS <= {PASS_PX:g} px)")
    return {"PASS": 0, "WARN": 1, "FAIL": 2}[c["verdict"]]


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
