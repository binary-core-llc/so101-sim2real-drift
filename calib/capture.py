#!/usr/bin/env python3
"""Frame sources for the calibration tools: the study cameras (by USB identity) or recorded/rendered images.

Camera(role) opens the device found by usbcam.find(role) the way LeRobot 0.4.1's OpenCVCamera does
(lerobot/cameras/opencv/camera_opencv.py: VideoCapture, then FOURCC, then width/height, then FPS, then a
1 s warm-up), and returns RGB like LeRobot's default color_mode. The V4L2 backend is named explicitly here
(LeRobot passes CAP_ANY); test T19 compares a frame from each path.

Source("path/to/dir_or_file_or_video") replays recorded or rendered frames (RGB), for dry runs.
open_source(spec): "camera:front", "camera:wrist", or a path.
"""
import glob
import io
import time
from contextlib import redirect_stdout
from pathlib import Path

import cv2
import numpy as np

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))  # sibling modules (python -I skips the script dir)

import usbcam

WIDTH, HEIGHT, FPS, FOURCC = 640, 480, 30, "MJPG"


def fourcc_str(code):
    code = int(code)
    return "".join(chr((code >> 8 * i) & 0xFF) for i in range(4))


class Camera:
    def __init__(self, role, fourcc=FOURCC, width=WIDTH, height=HEIGHT, fps=FPS, warmup_s=1.0, keep_lock=True):
        self.role = role
        self.dev = usbcam.find(role)                      # stops if the registered device is not connected
        self.node = self.dev["node"]
        self.cap = cv2.VideoCapture(self.node, cv2.CAP_V4L2)
        if not self.cap.isOpened():
            raise SystemExit(f"STOP: could not open {role} at {self.node}")
        ok = self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*fourcc))
        got = fourcc_str(self.cap.get(cv2.CAP_PROP_FOURCC))
        if not ok or got != fourcc:
            raise SystemExit(f"STOP: {role} refused fourcc {fourcc} (got {got})")
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_FPS, float(fps))
        self.settings = {"fourcc": fourcc_str(self.cap.get(cv2.CAP_PROP_FOURCC)),
                         "width": int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                         "height": int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                         "fps": self.cap.get(cv2.CAP_PROP_FPS)}
        if (self.settings["width"], self.settings["height"]) != (width, height):
            raise SystemExit(f"STOP: {role} gives {self.settings['width']}x{self.settings['height']}, not {width}x{height}")
        self.cap.read()                                   # OpenCV starts the stream at the first read
        self.lock_state = self._keep_lock() if keep_lock else "not checked"
        t0 = time.time()
        while time.time() - t0 < warmup_s:
            self.cap.read()

    def _keep_lock(self):
        """B 2.4: a stream start can change locked controls (the C920x sets its exposure to 312 when streaming starts,
        Nov 5; once its gain to 255, Nov 6, which one write while streaming did not fix), so the role's saved lock, if
        any, is read back here and written again, up to 3 times, if it drifted."""
        import camera_lock
        if "values" not in camera_lock.load_lock().get(self.role, {}):
            return "no lock saved"
        with redirect_stdout(io.StringIO()):
            if camera_lock.cmd_apply(self.role, write=False) == 0:
                return "held"
            for k in range(3):
                if camera_lock.cmd_apply(self.role, write=True) == 0:
                    return "re-applied" if k == 0 else f"re-applied ({k + 1} writes)"
                self.cap.read()
                time.sleep(0.2)
        raise SystemExit(f"STOP: the {self.role} camera lock does not read back after the stream opened (B 2.4)")

    def read(self):
        ok, bgr = self.cap.read()
        if not ok or bgr is None:
            raise SystemExit(f"STOP: {self.role} returned no frame")
        return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

    def close(self):
        self.cap.release()

    @property
    def identity(self):
        return {k: self.dev.get(k) for k in ("product", "vid", "pid", "serial", "manufacturer", "usb_path", "node", "by_id")}


class Source:
    """Recorded or rendered frames (RGB), looping; a directory of images, one image, or a video file."""

    def __init__(self, path, loop=True):
        p = Path(path)
        self.role, self.node, self.loop, self.i = f"file:{p.name}", str(p), loop, 0
        if p.is_dir():
            self.files = sorted(f for f in glob.glob(str(p / "*")) if f.lower().endswith((".png", ".jpg", ".jpeg")))
            self.cap = None
        elif p.suffix.lower() in (".png", ".jpg", ".jpeg"):
            self.files, self.cap = [str(p)], None
        else:
            self.files, self.cap = [], cv2.VideoCapture(str(p))
        if self.cap is None and not self.files:
            raise SystemExit(f"STOP: no images in {p}")
        self.settings = {"fourcc": "file", "width": WIDTH, "height": HEIGHT, "fps": FPS}

    def read(self):
        if self.cap is not None:
            ok, bgr = self.cap.read()
            if not ok and self.loop:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ok, bgr = self.cap.read()
            if not ok:
                raise SystemExit("STOP: end of recording")
            return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        if self.i >= len(self.files):
            if not self.loop:
                raise SystemExit("STOP: end of recording")
            self.i = 0
        bgr = cv2.imread(self.files[self.i], cv2.IMREAD_COLOR)
        self.i += 1
        return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

    def close(self):
        if self.cap is not None:
            self.cap.release()

    @property
    def identity(self):
        return {"product": "recorded/rendered frames", "node": self.node}


def open_source(spec, **kw):
    return Camera(spec.split(":", 1)[1], **kw) if spec.startswith("camera:") else Source(spec)


def save_rgb(path, rgb):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))


def load_rgb(path):
    bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if bgr is None:
        raise SystemExit(f"STOP: cannot read {path}")
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)


def mean_frames(src, n):
    acc = None
    for _ in range(n):
        f = src.read().astype(np.float64)
        acc = f if acc is None else acc + f
    return (acc / n).round().astype(np.uint8)
