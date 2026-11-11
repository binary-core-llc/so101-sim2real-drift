#!/usr/bin/env python3
"""First-chunk cross-check (V28-01 follow-up, Nov 6): no robot, no cameras. Sends the GR00T server the first policy
input of the real run and of the sim trace with images and state swapped, and compares the first action chunks.

    docker run --rm --network host -v ~/gtc2027/gtc:/workspace/gtc -w /Isaac-GR00T real-robot \
        /Isaac-GR00T/.venv/bin/python /workspace/gtc/real/xcheck_first_chunk.py \
        --real V28-01_a1 --sim L00_nominal_r0 --n 10

Combinations (images front+wrist | state): SS sim|sim, RR real|real, SR sim|real (a), RS real|sim (b); and, one
camera at a time, Rf+Sw|real and Sf+Rw|real. Each is sent --n times (the policy samples noise), with a server
reset before each call, as at an episode start. Inputs are the exact ones logged: the real keyframes chunk_000
(PNG, written from the arrays sent) with steps chunk 0 joints, and the sim trace's first_input.npz.
Writes results/real/shakedown/xcheck_<real>_<sim>.json. Units: LeRobot joint values (-100..100; gripper 0..100).
"""
import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import cv2
import numpy as np

GTC = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(GTC / "real")]
import pilot  # noqa: E402  (patched_client: real ZMQ timeouts, LANG)

J = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]


def rgb(path):
    return cv2.cvtColor(cv2.imread(str(path), cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)


def model_input(front, wrist, state, lang):
    s = np.asarray(state, dtype=np.float32)
    return {"video": {"front": front[None, None], "wrist": wrist[None, None]},
            "state": {"single_arm": s[None, None, :5], "gripper": s[None, None, 5:6]},
            "language": {"annotation.human.task_description": [[lang]]}}


def chunk_array(chunk):
    return np.concatenate([chunk["single_arm"][0], chunk["gripper"][0]], axis=1).astype(float)   # (T, 6)


def logged_array(actions):
    return np.array([[a[f"{j}.pos"] for j in J] for a in actions], dtype=float)


def summary(arrs, state):
    a = np.stack(arrs)                                        # (n, T, 6)
    d_end = a[:, -1, :] - np.asarray(state)[None, :]          # change over the chunk, per call
    return {"delta_end_mean": dict(zip(J, np.round(d_end.mean(0), 2).tolist())),
            "delta_end_sd": dict(zip(J, np.round(d_end.std(0, ddof=1), 2).tolist())) if len(a) > 1 else None,
            "delta_end_min_max": {j: [round(float(d_end[:, i].min()), 2), round(float(d_end[:, i].max()), 2)]
                                  for i, j in enumerate(J)},
            "mean_chunk": np.round(a.mean(0), 2).tolist()}


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--real", default="V28-01_a1")
    ap.add_argument("--sim", default="L00_nominal_r0")
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--host", default="localhost")
    ap.add_argument("--port", type=int, default=5555)
    ap.add_argument("--timeout_s", type=float, default=10.0)
    a = ap.parse_args(argv)

    kf = GTC / "media/real/shakedown" / a.real / "kf"
    real_row = json.loads((GTC / "results/real/shakedown/steps" / f"{a.real}.jsonl").open().readline())
    R = {"front": rgb(kf / "chunk_000_front.png"), "wrist": rgb(kf / "chunk_000_wrist.png"),
         "state": [real_row["joints"][f"{j}.pos"] for j in J], "logged": logged_array(real_row["actions"])}
    tag, rep = a.sim.rsplit("_r", 1)
    z = np.load(GTC / "results/sim/trace" / f"{a.sim}_first_input.npz")
    sim_row = next(r for r in map(json.loads, (GTC / "results/sim/trace" / f"{tag}.jsonl").open())
                   if r.get("rep") == int(rep) and r.get("chunk") == 0)
    S = {"front": z["front"][0, 0], "wrist": z["wrist"][0, 0],
         "state": np.concatenate([z["single_arm"][0, 0], z["gripper"][0, 0]]).astype(float).tolist(),
         "logged": logged_array(sim_row["actions"])}
    combos = {"SS": (S["front"], S["wrist"], S["state"]), "RR": (R["front"], R["wrist"], R["state"]),
              "SR_a": (S["front"], S["wrist"], R["state"]), "RS_b": (R["front"], R["wrist"], S["state"]),
              "RfSw_R": (R["front"], S["wrist"], R["state"]), "SfRw_R": (S["front"], R["wrist"], R["state"])}

    client = pilot.patched_client(a.host, a.port, a.timeout_s)
    if not client.ping():
        raise SystemExit("STOP: policy server does not answer")
    out = {"utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "real": a.real, "sim": a.sim,
           "n": a.n, "lang": pilot.LANG, "units": "LeRobot joint values (-100..100; gripper 0..100)",
           "image_shapes": {"real": [list(R["front"].shape), list(R["wrist"].shape)],
                            "sim": [list(S["front"].shape), list(S["wrist"].shape)]},
           "state": {"real": dict(zip(J, np.round(R["state"], 2).tolist())), "sim": dict(zip(J, np.round(S["state"], 2).tolist()))},
           "logged_first_chunk": {"real": summary([R["logged"]], R["state"]), "sim": summary([S["logged"]], S["state"])},
           "combos": {}}
    for name, (f, w, s) in combos.items():
        arrs = []
        for _ in range(a.n):
            client.reset()
            chunk, _info = client.get_action(model_input(f, w, s, pilot.LANG))
            arrs.append(chunk_array(chunk))
        out["combos"][name] = summary(arrs, s)
        m = out["combos"][name]["delta_end_mean"]
        print(f"{name:7s} " + "  ".join(f"{j[:6]} {m[j]:+6.1f}" for j in J))
    for k in ("real", "sim"):
        m = out["logged_first_chunk"][k]["delta_end_mean"]
        print(f"log {k:4s}" + "  ".join(f"{j[:6]} {m[j]:+6.1f}" for j in J))
    p = GTC / "results/real/shakedown" / f"xcheck_{a.real}_{a.sim}.json"
    p.write_text(json.dumps(out, indent=1))
    print(f"-> {p.relative_to(GTC)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
