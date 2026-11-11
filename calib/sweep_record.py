#!/usr/bin/env python3
"""V24 / V29 (E_premortem): record the front and wrist cameras side by side while the arm is swept by teleop, with
a live view for the operator.

    .venv/bin/python -I calib/sweep_record.py --tag v24_v29          # q ends it
Each camera opens through capture.Camera (registered USB identity, saved lock re-applied, B 2.4). Writes
media/sweep/<tag>_<utc>_{front,wrist}.avi (MJPG, the frames as read) and results/rig/sweep_<tag>_<utc>.json
(frame counts, duration, fps, lock states). Reviewed afterwards for anything extra in view (coins on the mark
locations, the judge hole, the phone).
"""
import argparse
import datetime as dt
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))  # sibling modules (python -I skips the script dir)

import capture  # noqa: E402
import live  # noqa: E402

GTC = Path(__file__).resolve().parents[1]


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="v24_v29")
    ap.add_argument("--headless-frames", type=int)
    a = ap.parse_args(argv)
    utc = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    stem = f"{a.tag}_{utc.replace(':', '')}"
    media = GTC / "media" / "sweep"
    media.mkdir(parents=True, exist_ok=True)
    cams = {r: capture.Camera(r) for r in ("front", "wrist")}
    writers = {r: cv2.VideoWriter(str(media / f"{stem}_{r}.avi"), cv2.VideoWriter_fourcc(*"MJPG"), 30.0,
                                  (capture.WIDTH, capture.HEIGHT)) for r in cams}
    st = {"n": 0, "t0": time.time()}

    def step():
        frames = {r: c.read() for r, c in cams.items()}
        for r, f in frames.items():
            writers[r].write(cv2.cvtColor(f, cv2.COLOR_RGB2BGR))
        st["n"] += 1
        dt_s = time.time() - st["t0"]
        lines = [f"REC {dt_s:5.0f} s  {st['n'] / max(dt_s, 1e-3):4.1f} fps   front | wrist", "q stop"]
        return live.put_lines(np.hstack([frames["front"], frames["wrist"]]), lines, scale=0.6), lines

    try:
        live.run(step, {"q": lambda: "quit"}, f"{a.tag} sweep recording", headless=a.headless_frames is not None,
                 max_frames=a.headless_frames, period_ms=1)
    finally:
        dur = time.time() - st["t0"]
        for w in writers.values():
            w.release()
        rec = {"utc": utc, "tag": a.tag, "frames": st["n"], "seconds": round(dur, 1), "fps": round(st["n"] / max(dur, 1e-3), 1),
               "lock": {r: c.lock_state for r, c in cams.items()},
               "videos": [str((media / f"{stem}_{r}.avi").relative_to(GTC)) for r in cams]}
        for c in cams.values():
            c.close()
        out = GTC / "results" / "rig" / f"sweep_{stem}.json"
        out.write_text(json.dumps(rec, indent=1))
        print(f"{st['n']} frame pairs in {dur:.0f} s ({rec['fps']} fps) -> {out.relative_to(GTC)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
