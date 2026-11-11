#!/usr/bin/env python3
"""R0 pan aim and roll (Nov 5): the C920x's live view with its image centre and the ChArUco grid centre marked, and
the camera roll read from the board.

    .venv/bin/python -I calib/aim_view.py [--tag r0] [--source camera:front]
G8 (E_premortem, wins): R0 is "panned so the image centre falls on the mat centre". The board lies flat on the mat,
centred on the mat-centre mark, so its grid centre stands in for the mat centre. Shows no sim render, no pose and no
target (R0 is a reading: tape and gauge, then this pan; A step 10 forbids adjusting R0 to the sim). Pan only: the
gauge sets the tilt, so a vertical offset stays as it is. The grid centre comes from a homography of the corners
seen, so a hidden corner (the wrist) doesn't matter.
Roll (the gauge can't read it on the C920's 45-degree top: it shows "Erro"): the board's vanishing line, H^-T (0,0,1),
is the floor's horizon in the image, and its slope is the camera roll (B 1.3: atan2(-x.z, -y.z), + = clockwise seen
from behind) when pixels are square. It needs no focal length and no principal point. Lens distortion is not
removed (no C920 intrinsics before C3): on the made-up test lens that biases roll by about 0.1 deg
(tests/test_aim_view.py); the C3 PnP gives the true R0 roll afterwards.
On q, writes the last offset and roll to results/still/<tag>_aim.json.
"""
import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))  # sibling modules (python -I skips the script dir)

import capture  # noqa: E402
import charuco as C  # noqa: E402
import live  # noqa: E402

GTC = Path(__file__).resolve().parents[1]
CENTRE_OBJ = np.array([C.SPEC["cols"] * C.SPEC["square_m"] / 2, C.SPEC["rows"] * C.SPEC["square_m"] / 2])


def grid_centre(det):
    """The board's grid centre in the image, or None (needs 6 corners)."""
    if det is None or len(det["ids"]) < 6:
        return None
    H, _ = cv2.findHomography(det["obj"][:, :2], det["img"])
    if H is None:
        return None
    p = H @ np.array([*CENTRE_OBJ, 1.0])
    return p[:2] / p[2]


def horizon_roll(obj, img):
    """Camera roll (deg, B 1.3) from the board plane's vanishing line; None if too few points."""
    if len(obj) < 6:
        return None
    H, _ = cv2.findHomography(obj[:, :2], img)
    if H is None:
        return None
    a, b, _ = np.linalg.inv(H).T @ [0.0, 0.0, 1.0]
    if b > 0:                       # line sign: the camera looks down, so the image y axis points down the floor
        a, b = -a, -b
    return float(np.degrees(np.arctan2(-a, -b)))


def roll(det):
    return None if det is None else horizon_roll(det["obj"], det["img"])


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="r0")
    ap.add_argument("--source", default="camera:front")
    ap.add_argument("--headless-frames", type=int)
    a = ap.parse_args(argv)
    src = capture.open_source(a.source)
    det = C.Detector()
    hist, rolls, st = [], [], {"lines": ["board not seen"], "rec": None}

    def step():
        f = src.read()
        h, w = f.shape[:2]
        cx, cy = w / 2, h / 2
        out = f.copy()
        cv2.line(out, (int(cx), 0), (int(cx), h), (0, 255, 255), 1)
        cv2.line(out, (0, int(cy)), (w, int(cy)), (0, 255, 255), 1)
        d = det.detect(f)
        c = grid_centre(d)
        r = roll(d)
        if c is None or r is None:
            hist.clear()
            rolls.clear()
            st["lines"] = ["board not seen"]
        else:
            hist.append(c)
            rolls.append(r)
            del hist[:-10], rolls[:-10]
            m = np.mean(hist, axis=0)
            rr = float(np.mean(rolls))
            dx, dy = m[0] - cx, m[1] - cy
            cv2.drawMarker(out, (int(round(m[0])), int(round(m[1]))), (255, 0, 255), cv2.MARKER_CROSS, 24, 2)
            side = "left" if dx < 0 else "right"
            st["lines"] = [f"board centre {dx:+.0f} px ({side}), {dy:+.0f} px (+ = low)",   # one line each: 640 px wide
                           f"roll {rr:+.2f} deg (+ = clockwise from behind)"]
            st["rec"] = {"utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "tag": a.tag,
                         "source": src.identity, "image_size": [w, h], "grid_centre_px": m.tolist(),
                         "dx_px": float(dx), "dy_px": float(dy), "roll_deg": rr,
                         "frames_averaged": len(hist)}
        return live.put_lines(out, st["lines"] + ["q quit"], scale=0.6), st["lines"]

    try:
        live.run(step, {"q": lambda: "quit"}, f"{a.tag} pan aim + roll", headless=a.headless_frames is not None,
                 max_frames=a.headless_frames)
    finally:
        src.close()
    print("\n".join(st["lines"]))
    if st["rec"]:
        out = GTC / "results" / "still" / f"{a.tag}_aim.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(st["rec"], indent=1))
        print(f"-> {out.relative_to(GTC)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
