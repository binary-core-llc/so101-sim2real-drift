#!/usr/bin/env python3
"""Robot health check: servo scan, voltage, temperature, status. Read-only: no write, no torque change, no motion.

    real/run_real.sh python /workspace/gtc/real/robot_health.py --role follower    # then --role leader
The arm's serial adapter is found only by its registered USB identity (calib/usbcam.py; stops if absent).
LeRobot 0.4.1 FeetechMotorsBus at its default 1 Mbps; register addresses from lerobot/motors/feetech/tables.py
(Present_Voltage 62, Present_Temperature 63, Status 65, Max_Temperature_Limit 13, Max/Min_Voltage_Limit 14/15,
model 777 = sts3215). The port is closed with disconnect(disable_torque=False) so nothing is written.
PASS per servo: answers the ping as an STS3215; voltage within the servo's own Min..Max_Voltage_Limit; temperature
at least 10 C below its own Max_Temperature_Limit (WARN within 10 C, FAIL at the limit); Status 0 (else WARN,
value printed). Voltage registers are in 0.1 V (shown /10; check that the 12 V supply reads about 12 V).
Writes results/robot/health_<role>_<utc>.json. Exit 0 PASS, 1 WARN, 2 FAIL, 3 STOP (port not found / no reply).
"""
import argparse
import datetime as dt
import json
import sys
from pathlib import Path

GTC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GTC / "calib"))
import usbcam  # noqa: E402

JOINTS = {1: "shoulder_pan", 2: "shoulder_lift", 3: "elbow_flex", 4: "wrist_flex", 5: "wrist_roll", 6: "gripper"}
STS3215 = 777
REGS = ("Present_Voltage", "Present_Temperature", "Status", "Max_Temperature_Limit", "Max_Voltage_Limit",
        "Min_Voltage_Limit", "Present_Position", "Torque_Enable")


class LerobotBus:
    def __init__(self, port):
        from lerobot.motors import Motor, MotorNormMode
        from lerobot.motors.feetech import FeetechMotorsBus
        self.bus = FeetechMotorsBus(port, {n: Motor(i, "sts3215", MotorNormMode.RANGE_M100_100) for i, n in JOINTS.items()})
        self.bus.connect(handshake=False)

    def ping(self):
        return self.bus.broadcast_ping() or {}

    def read(self, reg, name):
        return int(self.bus.read(reg, name, normalize=False))

    def close(self):
        self.bus.disconnect(disable_torque=False)


def check(bus):
    found = bus.ping()
    rows, worst = [], 0
    for sid, name in JOINTS.items():
        r = {"id": sid, "joint": name, "model": found.get(sid)}
        if sid not in found:
            r.update(result="FAIL", why="no reply")
        elif found[sid] != STS3215:
            r.update(result="FAIL", why=f"model {found[sid]} is not STS3215 ({STS3215})")
        else:
            try:
                r.update({k: bus.read(k, name) for k in REGS})
            except Exception as e:  # noqa: BLE001
                r.update(result="FAIL", why=f"read error: {e}")
                rows.append(r)
                worst = 2
                continue
            why, res = [], "PASS"
            if not r["Min_Voltage_Limit"] <= r["Present_Voltage"] <= r["Max_Voltage_Limit"]:
                why.append(f"voltage {r['Present_Voltage'] / 10:.1f} V outside {r['Min_Voltage_Limit'] / 10:.1f}"
                           f"-{r['Max_Voltage_Limit'] / 10:.1f} V")
                res = "FAIL"
            if r["Present_Temperature"] >= r["Max_Temperature_Limit"]:
                why.append(f"temperature {r['Present_Temperature']} C at its limit {r['Max_Temperature_Limit']} C")
                res = "FAIL"
            elif r["Present_Temperature"] > r["Max_Temperature_Limit"] - 10:
                why.append(f"temperature {r['Present_Temperature']} C within 10 C of its limit")
                res = "WARN" if res == "PASS" else res
            if r["Status"] != 0:
                why.append(f"status register {r['Status']} (not 0)")
                res = "WARN" if res == "PASS" else res
            r.update(result=res, why="; ".join(why))
        worst = max(worst, {"PASS": 0, "WARN": 1, "FAIL": 2}[r["result"]])
        rows.append(r)
    extra = sorted(set(found) - set(JOINTS))
    return rows, worst, extra


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--role", default="follower", choices=["follower", "leader"])
    a = ap.parse_args(argv)
    try:
        dev = usbcam.find(a.role)
    except usbcam.DeviceError as e:
        print(e, file=sys.stderr)
        return 3
    try:
        bus = LerobotBus(dev["node"])
    except Exception as e:  # noqa: BLE001
        print(f"STOP: cannot open the {a.role} bus at {dev['node']}: {e}", file=sys.stderr)
        return 3
    try:
        rows, worst, extra = check(bus)
    finally:
        bus.close()
    utc = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    out = GTC / "results" / "robot" / f"health_{a.role}_{utc.replace(':', '')}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"utc": utc, "role": a.role, "port": dev, "servos": rows, "extra_ids": extra}, indent=1))
    for r in rows:
        v = f"{r['Present_Voltage'] / 10:5.1f} V  {r['Present_Temperature']:3d} C  status {r['Status']}" if "Present_Voltage" in r else ""
        print(f"  id {r['id']} {r['joint']:13s} {r['result']:4s} {v}  {r.get('why', '')}")
    if extra:
        print(f"  extra IDs on the bus: {extra}")
    print(f"{a.role.upper()} HEALTH {['PASS', 'WARN', 'FAIL'][worst]} -> {out.relative_to(GTC)}")
    return worst


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
