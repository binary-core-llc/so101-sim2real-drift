#!/usr/bin/env python3
"""Ping the GR00T policy server with a real timeout (test T02).

The course PolicyClient stores timeout_ms but never applies it
(course gr00t_client/server_client.py:169,177,217-218; Isaac-GR00T ead52833
gr00t/policy/server_client.py:162,170,210-211), so a dead server hangs it forever.
This client speaks the same msgpack-over-ZMQ REQ protocol but sets
RCVTIMEO/SNDTIMEO and LINGER=0, and opens a fresh socket per attempt.

    .venv/bin/python -I sim/server_ping.py [--host localhost] [--port 5555]
        [--timeout 10] [--wait 600] [--modality]

Exit 0 = ping answered ok; 1 = no answer within the limits.
--wait keeps retrying (for a server that is still loading) up to that many seconds.
"""
import argparse
import json
import sys
import time

import msgpack
import zmq


def call(host, port, endpoint, timeout_s):
    ctx = zmq.Context.instance()
    s = ctx.socket(zmq.REQ)
    s.setsockopt(zmq.LINGER, 0)
    s.setsockopt(zmq.RCVTIMEO, int(timeout_s * 1000))
    s.setsockopt(zmq.SNDTIMEO, int(timeout_s * 1000))
    s.connect(f"tcp://{host}:{port}")
    try:
        s.send(msgpack.packb({"endpoint": endpoint}))
        # unknown custom classes (ModalityConfig, ndarray) stay plain dicts here
        return msgpack.unpackb(s.recv(), strict_map_key=False)
    finally:
        s.close(0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="localhost")
    ap.add_argument("--port", type=int, default=5555)
    ap.add_argument("--timeout", type=float, default=10.0, help="seconds per attempt")
    ap.add_argument("--wait", type=float, default=0.0, help="keep retrying for this many seconds")
    ap.add_argument("--modality", action="store_true", help="also fetch get_modality_config")
    a = ap.parse_args()

    t0 = time.time()
    attempt = 0
    while True:
        attempt += 1
        ts = time.time()
        try:
            r = call(a.host, a.port, "ping", a.timeout)
            ok = isinstance(r, dict) and r.get("status") == "ok"
            out = {"ok": ok, "response": r, "attempt": attempt,
                   "rtt_ms": round((time.time() - ts) * 1000, 1),
                   "waited_s": round(time.time() - t0, 1)}
            if ok and a.modality:
                m = call(a.host, a.port, "get_modality_config", a.timeout)
                out["modality_keys"] = {k: (v.get("as_json", v) if isinstance(v, dict) else v)
                                        for k, v in m.items()} if isinstance(m, dict) else m
            print(json.dumps(out, default=str))
            return 0 if ok else 1
        except zmq.error.Again:
            err = f"timeout after {a.timeout}s"
        except zmq.error.ZMQError as e:
            err = f"zmq error: {e}"
        if time.time() - t0 + a.timeout > a.wait:
            print(json.dumps({"ok": False, "error": err, "attempt": attempt,
                              "waited_s": round(time.time() - t0, 1)}))
            return 1
        time.sleep(2)


if __name__ == "__main__":
    sys.exit(main())
