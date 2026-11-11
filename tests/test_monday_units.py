#!/usr/bin/env python3
"""Unit tests for the rig tools with fake devices (no camera, no robot is opened).

    .venv/bin/python -I tests/test_monday_units.py
usbcam: identity matching, refusal, ambiguity. camera_lock: write order (autos first), readback mismatch, missing
controls, identity check on apply, focus choice. preflight: frame/fps checks on recorded frames. robot_health:
verdicts on a fake bus. dev_photos: clean photo + ChArUco ground truth on rendered frames.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np

GTC = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(GTC / "calib"), str(GTC / "real"), str(GTC / "tests")]
import camera_lock  # noqa: E402
import capture  # noqa: E402
import charuco as C  # noqa: E402
import preflight  # noqa: E402
import robot_health  # noqa: E402
import usbcam  # noqa: E402
import v4l2  # noqa: E402
from make_synthetic_calib import DIST, K  # noqa: E402
from test_pose_synthetic import R_E_cv  # noqa: E402

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append(ok)
    print(f"  {'ok  ' if ok else 'FAIL'} {name} {detail}")


# ------------------------------------------------------------------ usbcam
C920 = {"node": "/dev/video4", "index": "0", "vid": "046d", "pid": "08e5", "product": "HD Pro Webcam C920",
        "manufacturer": "", "serial": "ABC123", "usb_path": "3-2", "by_id": "", "name": ""}
LENOVO = {"node": "/dev/video0", "index": "0", "vid": "17ef", "pid": "4831", "product": "Lenovo FHD Webcam Audio",
          "manufacturer": "Sonix", "serial": "SN0001", "usb_path": "1-1", "by_id": "", "name": ""}
REG = {"cameras": {"front": {k: C920[k] for k in ("vid", "pid", "product", "serial")}}}


def t_usbcam():
    check("usbcam finds the registered C920x", usbcam.find("front", REG, [LENOVO, C920])["node"] == "/dev/video4")
    for devs, why in (([LENOVO], "absent"), ([LENOVO, C920, dict(C920, node="/dev/video6")], "two matches")):
        try:
            usbcam.find("front", REG, devs)
            check(f"usbcam stops when the C920x is {why}", False)
        except usbcam.DeviceError as e:
            check(f"usbcam stops when the C920x is {why}", "STOP" in str(e), f"({str(e)[:70]}...)")
    other = dict(C920, serial="ZZZ")
    try:
        usbcam.find("front", REG, [other])
        check("usbcam refuses a C920 with another serial", False)
    except usbcam.DeviceError:
        check("usbcam refuses a C920 with another serial", True)
    try:
        usbcam.find("wrist", REG, [C920])
        check("usbcam stops for an unregistered role", False)
    except usbcam.DeviceError as e:
        check("usbcam stops for an unregistered role", "not registered" in str(e))


# ------------------------------------------------------------------ camera_lock with a fake V4L2 device
class FakeDevice:
    def __init__(self, missing=(), stuck=None):
        rng = {"focus_absolute": (0, 250, 5, 0), "exposure_time_absolute": (3, 2047, 1, 250), "gain": (0, 255, 1, 0),
               "white_balance_temperature": (2000, 6500, 1, 4000), "zoom_absolute": (100, 500, 1, 100),
               "pan_absolute": (-36000, 36000, 3600, 0), "tilt_absolute": (-36000, 36000, 3600, 0),
               "brightness": (0, 255, 1, 128), "contrast": (0, 255, 1, 128), "saturation": (0, 255, 1, 128),
               "sharpness": (0, 255, 1, 128), "backlight_compensation": (0, 1, 1, 0),
               "focus_automatic_continuous": (0, 1, 1, 1), "auto_exposure": (0, 3, 1, 3),
               "white_balance_automatic": (0, 1, 1, 1), "exposure_dynamic_framerate": (0, 1, 1, 0),
               "power_line_frequency": (0, 2, 1, 2)}
        self.c = {v4l2.CID[k]: dict(zip(("min", "max", "step", "default"), r), id=v4l2.CID[k], flags=0, type=1)
                  for k, r in rng.items() if k not in missing}
        self.v = {cid: q["default"] for cid, q in self.c.items()}
        self.log, self.stuck = [], stuck or {}

    def has(self, cid):
        return cid in self.c

    def query(self, cid):
        return self.c[cid]

    def get(self, cid):
        return self.v[cid]

    def set(self, cid, val):
        self.log.append(v4l2.NAME_OF[cid])
        self.v[cid] = self.stuck.get(v4l2.NAME_OF[cid], val)

    def list_controls(self):
        return [{"name": v4l2.NAME_OF[c], "value": v} for c, v in self.v.items()]

    def __enter__(self):
        return self

    def __exit__(self, *a):
        pass


def t_lock():
    tmp = Path(tempfile.mkdtemp())
    camera_lock.LOCK = tmp / "camera_lock.json"
    dev = FakeDevice()
    camera_lock.usbcam.find = lambda role: C920
    camera_lock.v4l2.Device = lambda path: dev
    rc = camera_lock.cmd_lock("front", 83, 0, 4600, 40)
    order = dev.log
    autos_first = max(order.index(n) for n in ("focus_automatic_continuous", "auto_exposure", "white_balance_automatic")) < \
        min(order.index(n) for n in ("focus_absolute", "exposure_time_absolute", "white_balance_temperature"))
    check("lock: autos are switched off before the manual values", autos_first, f"(order {order[:5]}...)")
    lk = json.loads(camera_lock.LOCK.read_text())["front"]
    check("lock: values read back and saved with the exact USB identity", rc == 0 and lk["readback_ok"]
          and lk["identity"]["product"] == "HD Pro Webcam C920" and lk["identity"]["pid"] == "08e5"
          and lk["values"]["power_line_frequency"] == 2 and lk["values"]["exposure_time_absolute"] == 83)
    dev2 = FakeDevice(stuck={"gain": 7})
    camera_lock.v4l2.Device = lambda path: dev2
    check("apply: a value that does not read back fails", camera_lock.cmd_apply("front", write=True) == 1)
    camera_lock.v4l2.Device = lambda path: FakeDevice()
    camera_lock.usbcam.find = lambda role: dict(C920, serial="OTHER")
    try:
        camera_lock.cmd_apply("front", write=True)
        check("apply: refuses a different camera", False)
    except SystemExit as e:
        check("apply: refuses a different camera", "not the locked one" in str(e))
    camera_lock.usbcam.find = lambda role: dict(LENOVO)
    dev3 = FakeDevice(missing=("focus_absolute", "focus_automatic_continuous", "white_balance_temperature"))
    camera_lock.v4l2.Device = lambda path: dev3
    rc = camera_lock.cmd_lock("wrist", 83, 0, 4600, None)
    lk = json.loads(camera_lock.LOCK.read_text())["wrist"]
    check("lock: controls the camera lacks are skipped and listed", rc == 0 and "white_balance_temperature" in lk["missing_controls"])


def t_focus():
    tex, H, _ = C.pdf_texture(200)
    T = C.look_at_pose([0.12, 0.09 - 0.25, -0.45], [0.12, 0.09, 0.0])
    sharp = C.render_view(tex, H, K, DIST, T, noise=0.0, blur=0.0)
    det = C.Detector(30.0)

    class Cam:
        def __init__(self, dev, best):
            self.dev, self.best = dev, best

        def read(self):
            s = 0.08 * abs(self.dev.get(v4l2.CID["focus_absolute"]) - self.best) + 0.3
            return np.repeat(cv2.GaussianBlur(sharp, (0, 0), s)[:, :, None], 3, 2)
    sweeps = {}
    for dist, best in (("0.35", 30), ("0.55", 40), ("0.75", 55)):
        dev = FakeDevice()
        sweeps[dist] = camera_lock.sweep(Cam(dev, best), dev, list(range(0, 81, 5)), det, wait_s=0.0, n_frames=1)
    got = camera_lock.choose(sweeps)
    check("focus: maximin choice over 3 distances (bests 30/40/55)", got in (40, 45), f"(chose {got})")


def t_preflight():
    tmp = Path(tempfile.mkdtemp())
    for role, src in (("front", GTC / "results/c1/nominal_front_rgb.png"), ("wrist", GTC / "results/c1/nominal_wrist_rgb.png")):
        (tmp / role).mkdir()
        img = capture.load_rgb(src)
        for i in range(3):
            capture.save_rgb(tmp / role / f"{i}.png", img)
    rec, last = preflight.run({r: capture.Source(tmp / r) for r in ("front", "wrist")}, 1.0, {"front": "MJPG", "wrist": "MJPG"})
    check("preflight: both streams, 640x480 RGB, fps measured", rec["pass"] and all(c["shape"] == [480, 640, 3] for c in rec["checks"].values()),
          f"({ {k: c['fps'] for k, c in rec['checks'].items()} } fps from files)")


class FakeBus:
    def __init__(self, ids=range(1, 7), temp=35, volt=121, status=0):
        self.ids, self.temp, self.volt, self.status = list(ids), temp, volt, status

    def ping(self):
        return {i: 777 for i in self.ids}

    def read(self, reg, name):
        return {"Present_Voltage": self.volt, "Present_Temperature": self.temp, "Status": self.status,
                "Max_Temperature_Limit": 70, "Max_Voltage_Limit": 140, "Min_Voltage_Limit": 45,
                "Present_Position": 2048, "Torque_Enable": 0}[reg]


def t_health():
    for name, bus, want in (("healthy arm", FakeBus(), 0), ("servo 4 silent", FakeBus(ids=[1, 2, 3, 5, 6]), 2),
                            ("hot servo (65 of 70 C)", FakeBus(temp=65), 1), ("supply sagging (4.0 V)", FakeBus(volt=40), 2),
                            ("status bits set", FakeBus(status=32), 1)):
        _, worst, _ = robot_health.check(bus)
        check(f"health: {name} -> {['PASS', 'WARN', 'FAIL'][want]}", worst == want)


def t_dev_photos():
    tmp = Path(tempfile.mkdtemp())
    r0 = json.loads((GTC / "config/r0_pose.json").read_text())
    (tmp / "board.json").write_text(json.dumps({"d_x_mm": 101.1, "d_y_mm": 89.2, "h_K_mm": 9.9, "yaw_deg": 0.0}))
    (tmp / "intr.json").write_text(json.dumps({"K": K.tolist(), "dist": DIST.tolist()}))
    T_E_K, _ = C.board_in_E(tmp / "board.json")
    T_cv_K = np.linalg.inv(C.T(R_E_cv(45.0, r0["target_heading_deg"], 0.0), r0["target_lens_env"])) @ T_E_K
    tex, H, _ = C.pdf_texture(300)
    (tmp / "board").mkdir()
    for i in range(4):
        capture.save_rgb(tmp / "board" / f"{i}.png", np.repeat(C.render_view(tex, H, K, DIST, T_cv_K, rng=np.random.default_rng(i))[:, :, None], 3, 2))
    r = subprocess.run([sys.executable, "-I", str(GTC / "calib/dev_photos.py"), "--id", "D99", "--desc", "dry run",
                        "--layout", "L00", "--clean-source", str(GTC / "results/overlay_refs/sim_r0_front_rgb.png"),
                        "--board-source", str(tmp / "board"), "--source", "file", "--intrinsics", str(tmp / "intr.json"),
                        "--board-in-e", str(tmp / "board.json"), "--yes", "--check", "--out-root", str(tmp)],
                       capture_output=True, text=True)
    meta = json.loads((tmp / "results/photoset_dev/D99.json").read_text()) if r.returncode == 0 else {}
    g = (meta.get("gt") or {}).get("camera_pose", {})
    err = 1000 * np.linalg.norm(np.subtract(g.get("C_E_m", [9, 9, 9]), r0["target_lens_env"]))
    check("dev photos: clean photo saved, GT pose = R0 target", r.returncode == 0 and err < 1.0 and
          abs(g["angles"]["depression_deg"] - 45) < 0.1 and (tmp / "media/photoset_dev/raw/D99/clean_1.png").exists(),
          f"(centre error {err:.2f} mm, depression {g.get('angles', {}).get('depression_deg', 0):.2f}; {r.stderr[-120:]})")


def main():
    for t in (t_usbcam, t_lock, t_focus, t_preflight, t_health, t_dev_photos):
        print(t.__name__[2:])
        t()
    print(f"UNIT TESTS {'PASS' if all(RESULTS) else 'FAIL'} ({sum(RESULTS)}/{len(RESULTS)})")
    return 0 if all(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
