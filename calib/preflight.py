#!/usr/bin/env python3
"""Camera preflight (D_software C5, tests T16/T17): both cameras by USB identity, 640x480 at 30 fps in the
chosen fourcc, both streaming at once, lock re-applied before and read back after the streams open.

    .venv/bin/python -I calib/preflight.py [--fourcc MJPG] [--wrist-fourcc MJPG] [--seconds 5] [--ping]
Writes results/preflight/<utc>.json and a labelled side-by-side PNG. Exit 0 = PASS.
PASS: both cameras found; fourcc as asked; 640x480 RGB frames; >= 29 fps each while both stream (T16 [P]);
lock readback equal to config/camera_lock.json after the streams are open (B 2.4); calibration files hashed.
"""
import argparse
import datetime as dt
import hashlib
import json
import subprocess
import sys
import threading
import time
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))  # sibling modules (python -I skips the script dir)

import camera_lock
import capture
import usbcam

GTC = Path(__file__).resolve().parents[1]
MIN_FPS = 29.0
HASHED = ["config/devices.json", "config/camera_lock.json", "config/c920_intrinsics.json", "config/board_in_E.json"]


def measure(sources, seconds):
    """Frames per second for each source while all of them stream at once."""
    counts, last, errors = {}, {}, {}

    def worker(name, src):
        n, t0 = 0, time.time()
        try:
            while time.time() - t0 < seconds:
                last[name] = src.read()
                n += 1
        except SystemExit as e:
            errors[name] = str(e)
        counts[name] = n / max(time.time() - t0, 1e-6)

    th = [threading.Thread(target=worker, args=(k, s)) for k, s in sources.items()]
    for t in th:
        t.start()
    for t in th:
        t.join()
    return counts, last, errors


def side_by_side(frames):
    tiles = []
    for name, f in frames.items():
        t = f.copy()
        cv2.putText(t, name.upper(), (10, 34), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 0, 0), 5, cv2.LINE_AA)
        cv2.putText(t, name.upper(), (10, 34), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (255, 255, 0), 2, cv2.LINE_AA)
        tiles.append(t)
    return np.hstack(tiles)


def sha(p):
    p = GTC / p
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None


def run(sources, seconds, want_fourcc, readback_fn=None):
    rec = {"utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "checks": {}}
    fps, last, errors = measure(sources, seconds)
    for name, src in sources.items():
        f = last.get(name)
        rec["checks"][name] = {
            "identity": src.identity, "settings": src.settings, "fps": round(fps.get(name, 0.0), 2),
            "shape": list(f.shape) if f is not None else None,
            "fourcc_ok": src.settings["fourcc"] in (want_fourcc[name], "file"),
            "size_ok": f is not None and f.shape == (480, 640, 3),
            "fps_ok": fps.get(name, 0.0) >= MIN_FPS, "error": errors.get(name),
            "mean_rgb": None if f is None else f.reshape(-1, 3).mean(0).round(1).tolist()}
    rec["lock_readback_after_open"] = readback_fn() if readback_fn else None
    rec["hashes"] = {p: sha(p) for p in HASHED}
    rec["pass"] = all(c["fourcc_ok"] and c["size_ok"] and c["fps_ok"] and not c["error"] for c in rec["checks"].values()) \
        and rec["lock_readback_after_open"] in (0, None)
    return rec, last


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--fourcc", default="MJPG")
    ap.add_argument("--wrist-fourcc", default=None)
    ap.add_argument("--seconds", type=float, default=5.0)
    ap.add_argument("--ping", action="store_true", help="also ping the GR00T server (sim/server_ping.py)")
    ap.add_argument("--sources", default=None, help="test only: front=PATH,wrist=PATH (recorded/rendered frames)")
    a = ap.parse_args(argv)
    want = {"front": a.fourcc, "wrist": a.wrist_fourcc or a.fourcc}
    try:
        if a.sources:
            sources = {k: capture.Source(v) for k, v in (x.split("=", 1) for x in a.sources.split(","))}
            readback = None
        else:
            for role in ("front", "wrist"):
                usbcam.find(role)                         # stop early, before touching anything
            if camera_lock.cmd_apply("all", write=True) != 0:
                raise SystemExit("STOP: the camera lock does not read back (before opening the streams)")
            sources = {r: capture.Camera(r, fourcc=want[r]) for r in ("front", "wrist")}
            readback = lambda: camera_lock.cmd_apply("all", write=False)   # noqa: E731
    except usbcam.DeviceError as e:
        print(e, file=sys.stderr)
        return 3
    try:
        rec, last = run(sources, a.seconds, want, readback)
    finally:
        for s in sources.values():
            s.close()
    if a.ping:
        r = subprocess.run([sys.executable, "-I", str(GTC / "sim" / "server_ping.py"), "--timeout", "5"],
                           capture_output=True, text=True)
        rec["server_ping"] = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr.strip()
        rec["pass"] &= r.returncode == 0
    out = GTC / "results" / "preflight" / f"{rec['utc'].replace(':', '')}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec, indent=1))
    if all(k in last for k in sources):
        capture.save_rgb(out.with_suffix(".png"), side_by_side({k: last[k] for k in sources}))
    for name, c in rec["checks"].items():
        print(f"  {name:6s} {c['identity'].get('product')!s:28s} {c['settings']['fourcc']} {c['shape']} {c['fps']:5.1f} fps  "
              f"{'ok' if c['fourcc_ok'] and c['size_ok'] and c['fps_ok'] and not c['error'] else 'FAIL ' + str(c['error'] or '')}")
    print(f"lock readback after open: {rec['lock_readback_after_open']}   ping: {rec.get('server_ping', 'not asked')}")
    print(f"PREFLIGHT {'PASS' if rec['pass'] else 'FAIL'}  ({out.relative_to(GTC)})")
    return 0 if rec["pass"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
