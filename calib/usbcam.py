#!/usr/bin/env python3
"""Find the study's USB devices by USB identity only (product string + VID:PID, and serial when it has one).

    python3 -I calib/usbcam.py list                      # read-only: sysfs only, no device node is opened
    python3 -I calib/usbcam.py register front            # record the C920x (role "front")
    python3 -I calib/usbcam.py register wrist            # record the robot's wrist camera
    python3 -I calib/usbcam.py register follower|leader  # record the arms' serial adapters
    python3 -I calib/usbcam.py find front                # print the device node, or stop with the reason

Roles and identities live in config/devices.json. find() returns a device only when exactly one connected
device matches the registered identity; otherwise it stops (SystemExit) with a message. It never falls back to
another device and never uses integer indices. Cameras resolve to their video-index0 capture node.
"""
import datetime as dt
import glob
import json
import os
import sys
from pathlib import Path

GTC = Path(__file__).resolve().parents[1]
REGISTRY = GTC / "config" / "devices.json"
CAMERA_ROLES = {"front": "C920", "wrist": None}          # role -> required substring of the product string
SERIAL_ROLES = ("follower", "leader")
ID_KEYS = ("vid", "pid", "product", "serial")


class DeviceError(SystemExit):
    pass


def _read(p):
    try:
        return Path(p).read_text().strip()
    except OSError:
        return ""


def _usb_parent(sysdev):
    d = Path(os.path.realpath(sysdev))
    while d != d.parent:
        if (d / "idVendor").exists():
            return d
        d = d.parent
    return None


def _identity(usb):
    return {"vid": _read(usb / "idVendor"), "pid": _read(usb / "idProduct"), "product": _read(usb / "product"),
            "manufacturer": _read(usb / "manufacturer"), "serial": _read(usb / "serial"), "usb_path": usb.name}


def _by_id(prefix, dev):
    for link in glob.glob(f"{prefix}/*"):
        if os.path.realpath(link) == os.path.realpath(dev):
            return link
    return ""


def list_cameras():
    out = []
    for v in sorted(glob.glob("/sys/class/video4linux/video*")):
        usb = _usb_parent(f"{v}/device")
        if usb is None:
            continue
        dev = f"/dev/{Path(v).name}"
        out.append({"node": dev, "index": _read(f"{v}/index"), "name": _read(f"{v}/name"),
                    "by_id": _by_id("/dev/v4l/by-id", dev), **_identity(usb)})
    return out


def list_serial():
    out = []
    for t in sorted(glob.glob("/sys/class/tty/ttyACM*") + glob.glob("/sys/class/tty/ttyUSB*")):
        usb = _usb_parent(f"{t}/device")
        if usb is None:
            continue
        dev = f"/dev/{Path(t).name}"
        out.append({"node": dev, "by_id": _by_id("/dev/serial/by-id", dev), **_identity(usb)})
    return out


def load_registry():
    return json.loads(REGISTRY.read_text()) if REGISTRY.exists() else {}


def _matches(dev, ident):
    if any(dev[k] != ident[k] for k in ("vid", "pid", "product")):
        return False
    return not ident.get("serial") or dev["serial"] == ident["serial"]


def find(role, registry=None, devices=None):
    """The one connected device for this role, or DeviceError explaining why not."""
    reg = load_registry() if registry is None else registry
    kind = "cameras" if role in CAMERA_ROLES else "serial" if role in SERIAL_ROLES else None
    if kind is None:
        raise DeviceError(f"unknown role {role!r}")
    ident = reg.get(kind, {}).get(role)
    if not ident:
        raise DeviceError(f"STOP: role {role!r} is not registered in {REGISTRY.relative_to(GTC)}. "
                          f"Plug it in and run: python3 -I calib/usbcam.py register {role}")
    devs = (list_cameras() if kind == "cameras" else list_serial()) if devices is None else devices
    if kind == "cameras":
        devs = [d for d in devs if d["index"] == "0"]
    hits = [d for d in devs if _matches(d, ident)]
    if len(hits) > 1 and ident.get("usb_path"):
        hits = [d for d in hits if d["usb_path"] == ident["usb_path"]]
    want = f"{ident['product']!r} {ident['vid']}:{ident['pid']}" + (f" serial {ident['serial']}" if ident.get("serial") else "")
    if not hits:
        seen = ", ".join(f"{d['product']!r} {d['vid']}:{d['pid']}" for d in devs) or "nothing"
        raise DeviceError(f"STOP: {role} ({want}) is not connected. Connected: {seen}. "
                          "No other device will be used.")
    if len(hits) > 1:
        raise DeviceError(f"STOP: {len(hits)} devices match {role} ({want}); unplug the extra one(s).")
    return hits[0]


def register(role, pick=None, force=False):
    kind = "cameras" if role in CAMERA_ROLES else "serial" if role in SERIAL_ROLES else None
    if kind is None:
        raise DeviceError(f"unknown role {role!r}; use one of {list(CAMERA_ROLES) + list(SERIAL_ROLES)}")
    devs = list_cameras() if kind == "cameras" else list_serial()
    if kind == "cameras":
        devs = [d for d in devs if d["index"] == "0"]
    if not devs:
        raise DeviceError(f"STOP: no {kind[:-1] if kind == 'cameras' else 'serial'} device is connected")
    for i, d in enumerate(devs):
        print(f"  [{i}] {d['node']}  {d['product']!r}  {d['vid']}:{d['pid']}  serial {d['serial'] or '-'}  "
              f"manufacturer {d['manufacturer']!r}  usb {d['usb_path']}")
    if pick is None:
        pick = int(input(f"which one is the {role}? number: "))
    d = devs[pick]
    need = CAMERA_ROLES.get(role)
    if need and need.lower() not in d["product"].lower() and not force:
        raise DeviceError(f"STOP: product {d['product']!r} does not contain {need!r}; this is not the study camera. "
                          "Use --force only if you are sure.")
    reg = load_registry()
    same = [r for k, r in reg.get(kind, {}).items() if k != role and all(r.get(x) == d[x] for x in ID_KEYS)]
    ident = {k: d[k] for k in ("vid", "pid", "product", "manufacturer", "serial", "usb_path")}
    if same and not d["serial"]:
        print("note: another role has the same identity and there is no serial; the USB port path is kept to tell them apart")
    else:
        ident["usb_path"] = ident["usb_path"] if same else ""
    ident["registered_utc"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    reg.setdefault(kind, {})[role] = ident
    REGISTRY.write_text(json.dumps(reg, indent=1) + "\n")
    print(f"registered {role}: {json.dumps(ident)}")
    return ident


def main(argv):
    if not argv or argv[0] not in ("list", "register", "find"):
        print(__doc__)
        return 2
    if argv[0] == "list":
        out = {"cameras": list_cameras(), "serial": list_serial()}
        print(json.dumps(out, indent=1))
        return 0
    try:
        if argv[0] == "find":
            d = find(argv[1])
            print(d["node"], d.get("by_id", ""))
        else:
            pick = int(argv[argv.index("--pick") + 1]) if "--pick" in argv else None
            register(argv[1], pick, "--force" in argv)
    except DeviceError as e:
        print(e, file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
