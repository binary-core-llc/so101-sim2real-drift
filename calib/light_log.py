#!/usr/bin/env python3
"""Light drift log (E_premortem V20): the floor brightness in the locked C920x image every 5 min for >= 2 h,
plus a rolling-band check.

    systemd-run --user --unit=gtc-light-log --working-directory=$HOME/gtc2027/gtc \
        .venv/bin/python -I calib/light_log.py run --hours 2.5          # in the background; survives closing the terminal
    .venv/bin/python -I calib/light_log.py report                       # any time; PASS/FAIL once >= 2 h are logged
    systemctl --user stop gtc-light-log                                 # stop early
Start it after the C920x lock (the exposure must be fixed). It changes no camera setting itself; opening the
camera re-applies the saved lock if the stream start changed it (capture.Camera, B 2.4).

A V4L2 camera can be opened by one program at a time: each sample opens the C920x (found by its USB identity) for
about 1.5 s. If another tool is using it, the sample waits and retries every 20 s, and a gap is logged. Per sample:
mean RGB of the floor patch beside the mat (the C1 dump's V04 patch, --roi to change), the median of the brightest
30 % of pixels (floor-dominated, robust to the patch being covered), the frame mean, the lock readback, and a
rolling-band index (std of the frame-to-frame change of the row means, % of the mean).
report: PASS if >= 2 h are covered and the floor drift (max - min of the 3-sample running median, % of the mean)
is <= 2 % (V20); band index > 0.5 % is flagged [P]. Writes results/light/light_log_<date>.jsonl.
"""
import argparse
import datetime as dt
import io
import json
import statistics as st
import sys
import time
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))  # sibling modules (python -I skips the script dir)

import camera_lock  # noqa: E402
import capture  # noqa: E402

GTC = Path(__file__).resolve().parents[1]
C1 = GTC / "results" / "c1" / "c1_checks.json"


def default_roi():
    p = json.loads(C1.read_text())["V04_patches"]["floor_beside_mat"]["interior_patch"]
    (x, y), s = p["center_xy"], p["size_px"]
    return max(0, x - s), max(0, y - s), 2 * s, min(s + 1, 480 - max(0, y - s))


def measure(frames, roi):
    x, y, w, h = roi
    f = np.stack(frames).astype(np.float64)
    m = f.mean(0)
    patch = m[y:y + h, x:x + w].reshape(-1, 3).mean(0)
    grey = m.mean(-1).ravel()
    bright = float(np.median(np.sort(grey)[int(0.7 * grey.size):]))
    rows = f.mean(-1).mean(-1)                                 # per-frame row means (n_frames x height)
    band = float(np.mean([np.std(rows[i] - rows[i - 1]) for i in range(1, len(rows))]) / max(grey.mean(), 1e-6) * 100)
    return {"floor_patch_rgb": patch.round(2).tolist(), "floor_patch_mean": float(patch.mean()),
            "bright30_median": bright, "frame_mean": float(grey.mean()), "band_index_pct": round(band, 4)}


def sample(source, roi, n_frames=10):
    try:
        src = capture.open_source(source)
    except SystemExit as e:
        return None, str(e)
    try:
        frames = [src.read() for _ in range(n_frames)]
    except SystemExit as e:
        return None, str(e)
    finally:
        src.close()
    rec = measure(frames, roi)
    if source.startswith("camera:"):
        with redirect_stdout(io.StringIO()):
            rec["lock_readback_ok"] = camera_lock.cmd_apply(source.split(":", 1)[1], write=False) == 0
    return rec, None


def run(a):
    roi = tuple(int(v) for v in a.roi.split(",")) if a.roi else default_roi()
    out = Path(a.out or GTC / "results" / "light" / f"light_log_{dt.date.today()}.jsonl")
    out.parent.mkdir(parents=True, exist_ok=True)
    t_end, n = time.time() + a.hours * 3600, 0
    print(f"light log -> {out} every {a.every_s:.0f} s for {a.hours} h, floor ROI {roi}", flush=True)
    while time.time() < t_end and (a.samples is None or n < a.samples):
        t_slot = time.time()
        rec, why = sample(a.source, roi)
        while rec is None and time.time() - t_slot < a.every_s - 20:
            time.sleep(min(20, a.every_s))
            rec, why = sample(a.source, roi)
        row = {"utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "roi": roi, **(rec or {"gap": why})}
        with open(out, "a") as fh:
            fh.write(json.dumps(row) + "\n")
        print(json.dumps(row), flush=True)
        n += 1
        time.sleep(max(0.0, a.every_s - (time.time() - t_slot)))
    return 0


def report(a):
    p = Path(a.out or GTC / "results" / "light" / f"light_log_{dt.date.today()}.jsonl")
    rows = [json.loads(l) for l in open(p)]
    ok = [r for r in rows if "floor_patch_mean" in r]
    if len(ok) < 3:
        print(f"{len(ok)} samples so far ({len(rows) - len(ok)} gaps)")
        return 1
    t = [dt.datetime.fromisoformat(r["utc"]).timestamp() for r in ok]
    span_h = (t[-1] - t[0]) / 3600
    res = {}
    for key in ("floor_patch_mean", "bright30_median"):
        v = [r[key] for r in ok]
        med3 = [st.median(v[max(0, i - 1):i + 2]) for i in range(len(v))]
        res[key] = {"drift_pct": (max(med3) - min(med3)) / st.mean(v) * 100, "first": v[0], "last": v[-1],
                    "trend_pct_per_h": (np.polyfit(np.array(t) / 3600, v, 1)[0] / st.mean(v) * 100) if span_h > 0 else 0.0}
    band = max(r["band_index_pct"] for r in ok)
    locks = sum(r.get("lock_readback_ok") is False for r in ok)
    passed = span_h >= 2.0 and res["floor_patch_mean"]["drift_pct"] <= 2.0 and not locks
    for k, r in res.items():
        print(f"  {k:18s} drift {r['drift_pct']:.2f} %  trend {r['trend_pct_per_h']:+.2f} %/h  ({r['first']:.1f} -> {r['last']:.1f})")
    print(f"  {len(ok)} samples over {span_h:.2f} h, {len(rows) - len(ok)} gaps; max band index {band:.3f} % "
          f"({'possible rolling bands, look at a frame' if band > 0.5 else 'no bands'}); lock readback failures {locks}")
    print(f"LIGHT DRIFT {'PASS' if passed else ('IN PROGRESS' if span_h < 2.0 else 'FAIL')} (V20: >= 2 h, floor drift <= 2 %)")
    return 0 if passed else 1


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "report"])
    ap.add_argument("--source", default="camera:front")
    ap.add_argument("--every-s", type=float, default=300.0)
    ap.add_argument("--hours", type=float, default=2.5)
    ap.add_argument("--samples", type=int, default=None, help="test only: stop after N samples")
    ap.add_argument("--roi", default=None, help="x,y,w,h of a white-floor patch (default: the C1 V04 floor patch)")
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    return run(a) if a.cmd == "run" else report(a)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
