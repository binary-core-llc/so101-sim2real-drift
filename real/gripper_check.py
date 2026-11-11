#!/usr/bin/env python3
"""Gripper still matches the follower calibration? Read-only: no write, no torque change, no motion (Nov 5).

    real/run_real.sh python /workspace/gtc/real/gripper_check.py
After the gripper motor was taken out and put back (wrist camera adapter, Nov 5): the gripper servo's
Homing_Offset and Torque_Enable, then Present_Position averaged over 20 reads with the jaw held fully closed by
hand, then fully open, against range_min / range_max of the archived calibration
(results/robot/orange_robot_follower_2026-11-05T051834+0000.json). Match band: 17 counts per stop, the spread of
the gripper range over the three follower calibrations of Nov 4 (1419, 1435, 1436 counts). Same bus access as
robot_health.py (LeRobot FeetechMotorsBus, closed with disable_torque=False so nothing is written).
Writes results/robot/gripper_check_<utc>.json. Exit 0 MATCH, 1 MISMATCH, 3 STOP.
"""
import datetime as dt
import json
import statistics
import sys
import time
from pathlib import Path

GTC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GTC / "calib"))
sys.path.insert(0, str(GTC / "real"))
import usbcam  # noqa: E402
from robot_health import LerobotBus  # noqa: E402

CALIB = GTC / "results" / "robot" / "orange_robot_follower_2026-11-05T051834+0000.json"
BAND = 17


def held(bus, n=20):
    vals = []
    for _ in range(n):
        vals.append(bus.read("Present_Position", "gripper"))
        time.sleep(0.05)
    return {"mean": statistics.mean(vals), "min": min(vals), "max": max(vals)}


def main():
    cal = json.loads(CALIB.read_text())["gripper"]
    try:
        dev = usbcam.find("follower")
    except usbcam.DeviceError as e:
        print(e, file=sys.stderr)
        return 3
    try:
        bus = LerobotBus(dev["node"])
    except Exception as e:  # noqa: BLE001
        print(f"STOP: cannot open the follower bus at {dev['node']}: {e}", file=sys.stderr)
        return 3
    rec = {"utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "port": dev,
           "calibration": {"file": CALIB.name, **cal}, "band_counts": BAND}
    try:
        rec["homing_offset"] = bus.read("Homing_Offset", "gripper")
        rec["torque_enable"] = bus.read("Torque_Enable", "gripper")
        print(f"gripper servo: Homing_Offset {rec['homing_offset']} (calibration {cal['homing_offset']}), "
              f"Torque_Enable {rec['torque_enable']} (0 = off)")
        if rec["torque_enable"] != 0:
            print("STOP: gripper torque is on; this check only reads with torque off", file=sys.stderr)
            return 3
        input("Hold the jaw FULLY CLOSED by hand (gently, to its stop), then Enter ")
        rec["closed"] = held(bus)
        input("Now hold the jaw FULLY OPEN by hand (gently, to its stop), then Enter ")
        rec["open"] = held(bus)
    finally:
        bus.close()
    ends = sorted([("closed", rec["closed"]["mean"]), ("open", rec["open"]["mean"])], key=lambda x: x[1])
    lo, hi = ends[0][1], ends[1][1]
    rec["d_min"], rec["d_max"] = lo - cal["range_min"], hi - cal["range_max"]
    rec["range_now"], rec["range_cal"] = hi - lo, cal["range_max"] - cal["range_min"]
    ok = rec["homing_offset"] == cal["homing_offset"] and abs(rec["d_min"]) <= BAND and abs(rec["d_max"]) <= BAND
    rec["result"] = "MATCH" if ok else "MISMATCH"
    out = GTC / "results" / "robot" / f"gripper_check_{rec['utc'].replace(':', '')}.json"
    out.write_text(json.dumps(rec, indent=1))
    for name, r in (("closed", rec["closed"]), ("open", rec["open"])):
        print(f"  {name:6s} {r['mean']:7.1f} counts (reads {r['min']}-{r['max']})")
    print(f"  low stop ({ends[0][0]}) {lo:.1f} vs range_min {cal['range_min']}: {rec['d_min']:+.1f}; high stop "
          f"({ends[1][0]}) {hi:.1f} vs range_max {cal['range_max']}: {rec['d_max']:+.1f}; range {rec['range_now']:.0f} "
          f"vs {rec['range_cal']} (band {BAND} counts per stop)")
    print(f"GRIPPER {rec['result']} -> {out.relative_to(GTC)}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
