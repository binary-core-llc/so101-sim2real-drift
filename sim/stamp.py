#!/usr/bin/env python3
"""Prefix every line of stdin with a UTC timestamp. Treats '\\r' (tqdm) as a line end.
    some_command 2>&1 | python3 -I -u sim/stamp.py > run.log
"""
import datetime as dt
import sys

buf = ""
while True:
    ch = sys.stdin.read(1)
    if not ch:
        break
    if ch in "\r\n":
        if buf.strip():
            ts = dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds")
            sys.stdout.write(f"{ts} {buf}\n")
            sys.stdout.flush()
        buf = ""
    else:
        buf += ch
if buf.strip():
    sys.stdout.write(f"{dt.datetime.now(dt.timezone.utc).isoformat(timespec='milliseconds')} {buf}\n")
