#!/usr/bin/env python3
"""Minimal V4L2 control access through ioctl (stdlib only; v4l2-ctl is not installed on this PC).

Only the four control ioctls are used: VIDIOC_QUERYCTRL, VIDIOC_QUERYMENU, VIDIOC_G_CTRL, VIDIOC_S_CTRL.
Struct layouts and ioctl numbers follow /usr/include/linux/videodev2.h; tests/test_v4l2_abi.py compiles a C
program against that header and checks every number and size below.

Control names are made the way v4l2-ctl makes them (lower case, every run of other characters -> "_"),
e.g. "Focus, Automatic Continuous" -> focus_automatic_continuous. The lock code addresses controls by CID,
so kernel naming differences ("focus_auto" on older kernels) do not matter.
"""
import fcntl
import os
import re
import struct

# --- ioctl numbers: _IOWR('V', nr, struct) = (3 << 30) | (size << 16) | (ord('V') << 8) | nr
def _iowr(nr, size):
    return (3 << 30) | (size << 16) | (ord("V") << 8) | nr


QUERYCTRL_FMT = "=II32siiiiI2I"      # struct v4l2_queryctrl, 68 bytes
CONTROL_FMT = "=Ii"                   # struct v4l2_control, 8 bytes
QUERYMENU_FMT = "=II32sI"             # struct v4l2_querymenu (packed), 44 bytes; union read as name[32]
VIDIOC_G_CTRL = _iowr(27, struct.calcsize(CONTROL_FMT))
VIDIOC_S_CTRL = _iowr(28, struct.calcsize(CONTROL_FMT))
VIDIOC_QUERYCTRL = _iowr(36, struct.calcsize(QUERYCTRL_FMT))
VIDIOC_QUERYMENU = _iowr(37, struct.calcsize(QUERYMENU_FMT))

CTRL_FLAG_DISABLED, CTRL_FLAG_READ_ONLY, CTRL_FLAG_INACTIVE = 0x0001, 0x0004, 0x0010
CTRL_FLAG_NEXT_CTRL = 0x80000000
TYPE_INTEGER, TYPE_BOOLEAN, TYPE_MENU, TYPE_BUTTON, TYPE_CTRL_CLASS, TYPE_INTEGER_MENU = 1, 2, 3, 4, 6, 9

# --- control IDs (linux/v4l2-controls.h)
_USER, _CAMERA = 0x00980900, 0x009A0900
CID = {
    "brightness": _USER + 0, "contrast": _USER + 1, "saturation": _USER + 2,
    "white_balance_automatic": _USER + 12,       # V4L2_CID_AUTO_WHITE_BALANCE
    "gain": _USER + 19,
    "power_line_frequency": _USER + 24,          # menu: 0 disabled, 1 50 Hz, 2 60 Hz
    "white_balance_temperature": _USER + 26,
    "sharpness": _USER + 27,
    "backlight_compensation": _USER + 28,
    "auto_exposure": _CAMERA + 1,                # menu: 1 manual, 3 aperture priority
    "exposure_time_absolute": _CAMERA + 2,       # 100 us units
    "exposure_dynamic_framerate": _CAMERA + 3,   # V4L2_CID_EXPOSURE_AUTO_PRIORITY
    "pan_absolute": _CAMERA + 8, "tilt_absolute": _CAMERA + 9,
    "focus_absolute": _CAMERA + 10,
    "focus_automatic_continuous": _CAMERA + 12,  # V4L2_CID_FOCUS_AUTO
    "zoom_absolute": _CAMERA + 13,
}
NAME_OF = {v: k for k, v in CID.items()}
EXPOSURE_MANUAL, POWER_LINE_60HZ = 1, 2


def v4l2_name(kernel_name):
    return re.sub(r"[^a-z0-9]+", "_", kernel_name.lower()).strip("_")


class Device:
    """Control access to one V4L2 node. Opening the node does not start a stream."""

    def __init__(self, path):
        self.path = path
        self.fd = os.open(path, os.O_RDWR | os.O_NONBLOCK)

    def close(self):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def query(self, cid):
        buf = bytearray(struct.pack(QUERYCTRL_FMT, cid, 0, b"", 0, 0, 0, 0, 0, 0, 0))
        fcntl.ioctl(self.fd, VIDIOC_QUERYCTRL, buf)
        cid, typ, name, lo, hi, step, default, flags, _, _ = struct.unpack(QUERYCTRL_FMT, buf)
        return {"id": cid, "type": typ, "kernel_name": name.split(b"\0")[0].decode(errors="replace"),
                "min": lo, "max": hi, "step": step, "default": default, "flags": flags}

    def menu(self, q):
        items = {}
        for i in range(q["min"], q["max"] + 1):
            buf = bytearray(struct.pack(QUERYMENU_FMT, q["id"], i, b"", 0))
            try:
                fcntl.ioctl(self.fd, VIDIOC_QUERYMENU, buf)
            except OSError:
                continue
            _, idx, name, _ = struct.unpack(QUERYMENU_FMT, buf)
            items[idx] = name.split(b"\0")[0].decode(errors="replace") if q["type"] == TYPE_MENU else \
                struct.unpack("=q", name[:8])[0]
        return items

    def list_controls(self):
        """Every control the driver reports (VIDIOC_QUERYCTRL with NEXT_CTRL), with its current value."""
        out, cid = [], CTRL_FLAG_NEXT_CTRL
        while True:
            try:
                q = self.query(cid)
            except OSError:
                break
            cid = q["id"] | CTRL_FLAG_NEXT_CTRL
            if q["type"] == TYPE_CTRL_CLASS or q["flags"] & CTRL_FLAG_DISABLED:
                continue
            q["name"] = NAME_OF.get(q["id"], v4l2_name(q["kernel_name"]))
            if q["type"] in (TYPE_MENU, TYPE_INTEGER_MENU):
                q["menu"] = self.menu(q)
            q["value"] = None if q["type"] == TYPE_BUTTON else self.get(q["id"])
            out.append(q)
        return out

    def has(self, cid):
        try:
            return not self.query(cid)["flags"] & CTRL_FLAG_DISABLED
        except OSError:
            return False

    def get(self, cid):
        buf = bytearray(struct.pack(CONTROL_FMT, cid, 0))
        fcntl.ioctl(self.fd, VIDIOC_G_CTRL, buf)
        return struct.unpack(CONTROL_FMT, buf)[1]

    def set(self, cid, value):
        buf = bytearray(struct.pack(CONTROL_FMT, cid, int(value)))
        fcntl.ioctl(self.fd, VIDIOC_S_CTRL, buf)
