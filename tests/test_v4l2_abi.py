#!/usr/bin/env python3
"""T-ABI: check calib/v4l2.py against the kernel headers, without opening any device.

    python3 -I tests/test_v4l2_abi.py
Compiles a small C program with /usr/include/linux/videodev2.h, prints the ioctl numbers, struct sizes and
control IDs, and compares them with the Python constants. Exit 0 = all equal.
"""
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

GTC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GTC / "calib"))
import v4l2  # noqa: E402

MACROS = {"brightness": "V4L2_CID_BRIGHTNESS", "contrast": "V4L2_CID_CONTRAST", "saturation": "V4L2_CID_SATURATION",
          "white_balance_automatic": "V4L2_CID_AUTO_WHITE_BALANCE", "gain": "V4L2_CID_GAIN",
          "power_line_frequency": "V4L2_CID_POWER_LINE_FREQUENCY",
          "white_balance_temperature": "V4L2_CID_WHITE_BALANCE_TEMPERATURE", "sharpness": "V4L2_CID_SHARPNESS",
          "backlight_compensation": "V4L2_CID_BACKLIGHT_COMPENSATION", "auto_exposure": "V4L2_CID_EXPOSURE_AUTO",
          "exposure_time_absolute": "V4L2_CID_EXPOSURE_ABSOLUTE",
          "exposure_dynamic_framerate": "V4L2_CID_EXPOSURE_AUTO_PRIORITY", "pan_absolute": "V4L2_CID_PAN_ABSOLUTE",
          "tilt_absolute": "V4L2_CID_TILT_ABSOLUTE", "focus_absolute": "V4L2_CID_FOCUS_ABSOLUTE",
          "focus_automatic_continuous": "V4L2_CID_FOCUS_AUTO", "zoom_absolute": "V4L2_CID_ZOOM_ABSOLUTE"}
OTHER = {"VIDIOC_G_CTRL": v4l2.VIDIOC_G_CTRL, "VIDIOC_S_CTRL": v4l2.VIDIOC_S_CTRL,
         "VIDIOC_QUERYCTRL": v4l2.VIDIOC_QUERYCTRL, "VIDIOC_QUERYMENU": v4l2.VIDIOC_QUERYMENU,
         "V4L2_CTRL_FLAG_NEXT_CTRL": v4l2.CTRL_FLAG_NEXT_CTRL, "V4L2_CTRL_FLAG_DISABLED": v4l2.CTRL_FLAG_DISABLED,
         "V4L2_CTRL_FLAG_READ_ONLY": v4l2.CTRL_FLAG_READ_ONLY, "V4L2_CTRL_FLAG_INACTIVE": v4l2.CTRL_FLAG_INACTIVE,
         "V4L2_EXPOSURE_MANUAL": v4l2.EXPOSURE_MANUAL,
         "V4L2_CID_POWER_LINE_FREQUENCY_60HZ": v4l2.POWER_LINE_60HZ,
         "V4L2_CTRL_TYPE_MENU": v4l2.TYPE_MENU, "V4L2_CTRL_TYPE_CTRL_CLASS": v4l2.TYPE_CTRL_CLASS,
         "V4L2_CTRL_TYPE_INTEGER_MENU": v4l2.TYPE_INTEGER_MENU, "V4L2_CTRL_TYPE_BUTTON": v4l2.TYPE_BUTTON}
SIZES = {"struct v4l2_queryctrl": "=II32siiiiI2I", "struct v4l2_control": "=Ii", "struct v4l2_querymenu": "=II32sI"}


def main():
    lines = ['#include <stdio.h>', '#include <linux/videodev2.h>', 'int main(void){']
    for name in list(MACROS.values()) + list(OTHER):
        lines.append(f'printf("{name} %lu\\n", (unsigned long)({name}));')
    for s in SIZES:
        lines.append(f'printf("sizeof({s}) %lu\\n", (unsigned long)sizeof({s}));')
    lines.append("return 0;}")
    with tempfile.TemporaryDirectory() as d:
        src, exe = Path(d) / "abi.c", Path(d) / "abi"
        src.write_text("\n".join(lines))
        subprocess.run(["gcc", "-o", str(exe), str(src)], check=True)
        got = dict(l.rsplit(" ", 1) for l in subprocess.run([str(exe)], capture_output=True, text=True,
                                                            check=True).stdout.splitlines())
    want = {m: v4l2.CID[k] for k, m in MACROS.items()}
    want.update(OTHER)
    want.update({f"sizeof({s})": struct.calcsize(f) for s, f in SIZES.items()})
    bad = [(k, want[k], int(got[k])) for k in want if int(got[k]) != want[k]]
    for k in want:
        print(f"  {'ok ' if int(got[k]) == want[k] else 'BAD'} {k:42s} {int(got[k]):#x}")
    print(f"{len(want) - len(bad)}/{len(want)} equal to the kernel header")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
