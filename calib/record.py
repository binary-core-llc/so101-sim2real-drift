#!/usr/bin/env python3
"""Record rig readings (tape, gauge, yes/no answers) with a UTC time, one line per call.

    .venv/bin/python -I calib/record.py course_35cm_measured_cm=35.4 course_35cm_photo=IMG_2041
    .venv/bin/python -I calib/record.py --show
Appends to results/rig/measurements.jsonl; values are kept as typed (numbers parsed when they are numbers).
"""
import datetime as dt
import json
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "results" / "rig" / "measurements.jsonl"


def value(v):
    try:
        return float(v)
    except ValueError:
        return v


def main(argv):
    if not argv or argv == ["--show"]:
        for line in open(OUT) if OUT.exists() else []:
            print(line.rstrip())
        return 0
    bad = [a for a in argv if "=" not in a]
    if bad:
        raise SystemExit(f"STOP: use key=value, not {bad}")
    rec = {"utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           **{k: value(v) for k, v in (a.split("=", 1) for a in argv)}}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "a") as fh:
        fh.write(json.dumps(rec) + "\n")
    print(f"recorded {rec}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
