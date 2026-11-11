#!/usr/bin/env python3
"""Camera lock (B section 2): manual focus, exposure, gain, white balance, 60 Hz; saved and read back.

    .venv/bin/python -I calib/camera_lock.py controls front           # archive every control (names, ranges, defaults)
    .venv/bin/python -I calib/camera_lock.py tune front               # live: click the white floor; e/E g/G w/W adjust
    .venv/bin/python -I calib/camera_lock.py focus front              # autofocus off, sweep on the board at 3 distances
    .venv/bin/python -I calib/camera_lock.py lock front --exposure 83 --gain 0 --wb 4600 [--focus N]
    .venv/bin/python -I calib/camera_lock.py lock wrist --exposure 83 --gain 0 --wb 4600
    .venv/bin/python -I calib/camera_lock.py apply all                # after an unplug or reboot; exit 0 only if all read back
    .venv/bin/python -I calib/camera_lock.py check all                # read back only, writes nothing

The camera is found only by its registered USB identity (calib/usbcam.py); apply also refuses a camera whose
identity differs from the one saved in config/camera_lock.json. Order (B 2.2): autos off first, then manual
values, then read back every value. brightness/contrast/saturation/sharpness are set to the driver defaults
and recorded. A control the camera does not have is skipped and listed as missing.
"""
import argparse
import datetime as dt
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # sibling modules (python -I skips the script dir)

import usbcam
import v4l2

GTC = Path(__file__).resolve().parents[1]
LOCK = GTC / "config" / "camera_lock.json"
C1_CHECKS = GTC / "results" / "c1" / "c1_checks.json"
AUTOS_OFF = [("focus_automatic_continuous", 0), ("auto_exposure", v4l2.EXPOSURE_MANUAL),
             ("white_balance_automatic", 0), ("exposure_dynamic_framerate", 0)]
DEFAULTED = ("zoom_absolute", "pan_absolute", "tilt_absolute", "brightness", "contrast", "saturation", "sharpness")


def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def load_lock():
    return json.loads(LOCK.read_text()) if LOCK.exists() else {}


def plan(dev, exposure, gain, wb, focus):
    """Ordered (name, value) writes for this device; controls it lacks are reported, not written."""
    steps, missing = [], []
    manual = [("focus_absolute", focus), ("exposure_time_absolute", exposure), ("gain", gain),
              ("white_balance_temperature", wb), ("power_line_frequency", v4l2.POWER_LINE_60HZ),
              ("backlight_compensation", 0)]
    for name, val in AUTOS_OFF + [(n, v) for n, v in manual if v is not None]:
        if dev.has(v4l2.CID[name]):
            steps.append((name, val))
        else:
            missing.append(name)
    for name in DEFAULTED:
        if dev.has(v4l2.CID[name]):
            steps.append((name, dev.query(v4l2.CID[name])["default"]))
    return steps, missing


def write_and_read(dev, steps):
    for name, val in steps:
        q = dev.query(v4l2.CID[name])
        if not q["min"] <= val <= q["max"]:
            raise SystemExit(f"STOP: {name}={val} is outside the camera's range {q['min']}..{q['max']}")
        dev.set(v4l2.CID[name], val)
    time.sleep(0.2)
    back = {name: dev.get(v4l2.CID[name]) for name, _ in steps}
    bad = {n: (v, back[n]) for n, v in steps if back[n] != v}
    return back, bad


def identity_of(d):
    return {k: d.get(k, "") for k in ("product", "vid", "pid", "serial", "manufacturer")}


def cmd_controls(role):
    d = usbcam.find(role)
    with v4l2.Device(d["node"]) as dev:
        ctrls = dev.list_controls()
    out = GTC / "results" / "camera" / f"{role}_controls_{dt.date.today()}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"utc": utc(), "identity": identity_of(d), "node": d["node"], "controls": ctrls}, indent=1))
    for c in ctrls:
        menu = f" menu {c['menu']}" if c.get("menu") else ""
        print(f"  {c['name']:32s} value {c['value']!s:>6}  range {c['min']}..{c['max']} step {c['step']} "
              f"default {c['default']}{menu}")
    print(f"saved {out.relative_to(GTC)}")
    return 0


def cmd_lock(role, exposure, gain, wb, focus, focus_sweep=None):
    d = usbcam.find(role)
    lock = load_lock()
    prev = lock.get(role, {})
    if focus is None and prev.get("focus_sweep", {}).get("chosen") is not None:
        focus = prev["focus_sweep"]["chosen"]
    with v4l2.Device(d["node"]) as dev:
        steps, missing = plan(dev, exposure, gain, wb, focus)
        if focus is None and dev.has(v4l2.CID["focus_absolute"]):
            raise SystemExit("STOP: no focus value. Run the focus sweep first (camera_lock.py focus ROLE) or pass --focus.")
        back, bad = write_and_read(dev, steps)
        snapshot = dev.list_controls()
    rec = {"locked_utc": utc(), "identity": identity_of(d), "node_at_lock": d["node"], "by_id_at_lock": d.get("by_id"),
           "order": [n for n, _ in steps], "values": dict(steps), "missing_controls": missing,
           "readback": back, "readback_ok": not bad, "controls_snapshot": snapshot,
           "focus_sweep": focus_sweep or prev.get("focus_sweep")}
    lock[role] = rec
    LOCK.write_text(json.dumps(lock, indent=1) + "\n")
    report(role, steps, back, bad, missing)
    return 0 if not bad else 1


def report(role, steps, back, bad, missing):
    for name, val in steps:
        print(f"  {role:6s} {name:30s} set {val:>6}  read {back[name]:>6}  {'ok' if name not in bad else 'MISMATCH'}")
    if missing:
        print(f"  {role}: camera has no {', '.join(missing)} (skipped)")
    print(f"{role}: readback {'PASS' if not bad else 'FAIL ' + str(bad)}")


def cmd_apply(role, write=True):
    lock = load_lock()
    roles = [r for r in lock if "values" in lock[r]] if role == "all" else [role]
    if not roles or any("values" not in lock.get(r, {}) for r in roles):
        raise SystemExit(f"STOP: no saved lock for {role} in {LOCK.relative_to(GTC)} (a focus sweep alone is not a lock); "
                         "run camera_lock.py lock ROLE first")
    ok = True
    for r in roles:
        d = usbcam.find(r)
        if identity_of(d) != lock[r]["identity"]:
            raise SystemExit(f"STOP: the connected {r} camera {identity_of(d)} is not the locked one {lock[r]['identity']}")
        steps = [(n, lock[r]["values"][n]) for n in lock[r]["order"]]
        with v4l2.Device(d["node"]) as dev:
            if write:
                back, bad = write_and_read(dev, steps)
            else:
                back = {n: dev.get(v4l2.CID[n]) for n, _ in steps}
                bad = {n: (v, back[n]) for n, v in steps if back[n] != v}
        report(r, steps, back, bad, lock[r].get("missing_controls", []))
        ok &= not bad
    return 0 if ok else 1


# ---------------------------------------------------------------- focus sweep (B 2.3)
def board_roi(dets, shape):
    """Board region (padded bounding box of every corner detected during the sweep): the board does not move,
    so frames too blurred to detect it are still scored on the same pixels."""
    import numpy as np
    pts = np.vstack([d["img"] for d in dets if d is not None]) if any(d is not None for d in dets) else None
    if pts is None:
        raise SystemExit("STOP: the board was not found at any focus value; put it in view, centred, and repeat")
    (x0, y0), (x1, y1) = pts.min(0), pts.max(0)
    pad = 0.15 * max(x1 - x0, y1 - y0)
    return (int(max(0, x0 - pad)), int(max(0, y0 - pad)), int(min(shape[1], x1 + pad)), int(min(shape[0], y1 + pad)))


def sweep(cam, dev, values, det, wait_s=1.0, n_frames=5):
    """Focus value -> mean variance of the Laplacian on the board region (B 2.3)."""
    import cv2
    import numpy as np
    dev.set(v4l2.CID["focus_automatic_continuous"], 0)
    grabbed = []
    for v in values:
        dev.set(v4l2.CID["focus_absolute"], v)
        t0 = time.time()
        while time.time() - t0 < wait_s:
            cam.read()
        grays = [cv2.cvtColor(cam.read(), cv2.COLOR_RGB2GRAY) for _ in range(n_frames)]
        grabbed.append((v, grays, det.detect(grays[len(grays) // 2])))
    x0, y0, x1, y1 = board_roi([d for _, _, d in grabbed], grabbed[0][1][0].shape)
    out = []
    for v, grays, d in grabbed:
        score = float(np.mean([cv2.Laplacian(g[y0:y1, x0:x1], cv2.CV_64F).var() for g in grays]))
        out.append((v, score))
        print(f"    focus {v:4d}: sharpness {score:9.1f}{'' if d is not None else '  (board not detected)'}", flush=True)
    return out


def choose(sweeps):
    """B 2.3: per distance normalise by its maximum; pick the value that maximises the minimum."""
    vals = [v for v, _ in next(iter(sweeps.values()))]
    norm = {k: {v: s / (max(x for _, x in sw) or 1) for v, s in sw} for k, sw in sweeps.items()}
    return max(vals, key=lambda v: (min(norm[k][v] for k in norm), v))


def cmd_focus(role, vmax, distances, square_mm):
    import capture
    from charuco import Detector
    d = usbcam.find(role)
    cam = capture.Camera(role)
    det = Detector(square_mm)
    sweeps = {}
    try:
        with v4l2.Device(d["node"]) as dev:
            q = dev.query(v4l2.CID["focus_absolute"])
            step = max(1, q["step"])
            values = list(range(q["min"], min(vmax, q["max"]) + 1, step))
            for dist_m in distances:
                input(f"  Hold the board still about {dist_m:.2f} m from the camera, centred, then press Enter ")
                sweeps[f"{dist_m:.2f}"] = sweep(cam, dev, values, det)
            best = choose(sweeps)
            dev.set(v4l2.CID["focus_absolute"], best)
    finally:
        cam.close()
    print(f"chosen focus_absolute = {best} (B 2.3: maximises the minimum normalised sharpness over {list(sweeps)} m)")
    lock = load_lock()
    lock.setdefault(role, {})["focus_sweep"] = {"utc": utc(), "values": values, "scores": sweeps, "chosen": best,
                                                 "identity": identity_of(d), "square_mm": square_mm}
    LOCK.write_text(json.dumps(lock, indent=1) + "\n")
    print("now run: camera_lock.py lock", role, "--exposure E --gain G --wb W   (the focus is taken from the sweep)")
    return 0


# ---------------------------------------------------------------- tune exposure / gain / WB against the sim floor (G6)
def cmd_tune(role, source=None, headless_frames=None):
    import cv2
    import numpy as np
    import capture
    import live
    target = None
    if C1_CHECKS.exists():
        target = json.loads(C1_CHECKS.read_text())["V04_patches"]["floor_beside_mat"]["mean_rgb"]
    src = capture.open_source(source or f"camera:{role}")
    d = usbcam.find(role) if source is None else None
    dev = v4l2.Device(d["node"]) if d else None
    if dev:
        for name, val in AUTOS_OFF[1:]:
            if dev.has(v4l2.CID[name]):
                dev.set(v4l2.CID[name], val)
    st = {"roi": (300, 400), "frame": None}
    steps = {"e": ("exposure_time_absolute", -1), "E": ("exposure_time_absolute", 1), "g": ("gain", -1),
             "G": ("gain", 1), "w": ("white_balance_temperature", -100), "W": ("white_balance_temperature", 100)}

    def bump(name, delta):
        """delta +-1 = one control step; larger = that many units (white balance in K), kept on the step grid."""
        if not dev or not dev.has(v4l2.CID[name]):
            return
        q = dev.query(v4l2.CID[name])
        unit = max(q["step"], 1)
        inc = delta * unit if abs(delta) == 1 else round(delta / unit) * unit
        dev.set(v4l2.CID[name], min(q["max"], max(q["min"], dev.get(v4l2.CID[name]) + inc)))

    def step():
        f = src.read()
        st["frame"] = f
        x, y = st["roi"]
        p = f[max(0, y - 7):y + 8, max(0, x - 7):x + 8].reshape(-1, 3).mean(0)
        clip = float((f >= 250).any(-1).mean() * 100)
        lines = [f"ROI ({x},{y}) mean RGB {p.round(1).tolist()}  R/B {p[0] / max(p[2], 1):.3f}  clipped {clip:.1f}%"]
        if target:
            lines.append(f"sim white floor target {np.round(target, 1).tolist()} (+-5%): "
                         f"{'OK' if abs(p.mean() / np.mean(target) - 1) <= 0.05 else 'adjust'}")
        if dev:
            vals = {n: dev.get(v4l2.CID[n]) for n in ("exposure_time_absolute", "gain", "white_balance_temperature")
                    if dev.has(v4l2.CID[n])}
            lines.append("  ".join(f"{k} {v}" for k, v in vals.items()) + "   keys e/E g/G w/W, click = ROI, q = done")
        img = live.put_lines(f, lines)
        cv2.rectangle(img, (x - 7, y - 7), (x + 7, y + 7), (255, 0, 0), 1)
        return img, lines

    keys = {k: (lambda n=n, s=s: bump(n, s)) for k, (n, s) in steps.items()}
    keys["click"] = lambda x, y: st.__setitem__("roi", (int(x), int(y)))
    keys["q"] = lambda: "quit"
    live.run(step, keys, f"tune {role}", headless=headless_frames is not None, max_frames=headless_frames)
    if dev:
        vals = {n: dev.get(v4l2.CID[n]) for n in ("exposure_time_absolute", "gain", "white_balance_temperature")
                if dev.has(v4l2.CID[n])}
        print(f"lock with: camera_lock.py lock {role} --exposure {vals.get('exposure_time_absolute')} "
              f"--gain {vals.get('gain')} --wb {vals.get('white_balance_temperature')}")
        dev.close()
    src.close()
    return 0


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["controls", "lock", "apply", "check", "focus", "tune"])
    ap.add_argument("role", nargs="?", default="all")
    ap.add_argument("--exposure", type=int)
    ap.add_argument("--gain", type=int)
    ap.add_argument("--wb", type=int)
    ap.add_argument("--focus", type=int)
    ap.add_argument("--focus-max", type=int, default=80, help="B 2.3 sweeps 0..80")
    ap.add_argument("--distances", default="0.35,0.55,0.75")
    ap.add_argument("--square-mm", type=float, default=30.0)
    a = ap.parse_args(argv)
    try:
        if a.cmd == "controls":
            return cmd_controls(a.role)
        if a.cmd == "lock":
            if None in (a.exposure, a.gain, a.wb):
                raise SystemExit("STOP: lock needs --exposure, --gain and --wb (pick them with: camera_lock.py tune ROLE)")
            return cmd_lock(a.role, a.exposure, a.gain, a.wb, a.focus)
        if a.cmd in ("apply", "check"):
            return cmd_apply(a.role, write=a.cmd == "apply")
        if a.cmd == "focus":
            return cmd_focus(a.role, a.focus_max, [float(x) for x in a.distances.split(",")], a.square_mm)
        return cmd_tune(a.role)
    except usbcam.DeviceError as e:
        print(e, file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
