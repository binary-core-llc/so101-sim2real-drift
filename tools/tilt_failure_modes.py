#!/usr/bin/env python3
"""Where the vial ended in the failed episodes at camera tilt down 12-15 deg (explore-v1/v2), from existing logs.

    python3 -I tools/tilt_failure_modes.py
Per failed episode: the vial that moved most from its start (moved = > 2 cm), and its final state from the logged
final poses (world, and rack-corner frame). The gripper pose is not logged, so "held" is inferred:
  at a rack slot: vial upright, its origin inside the success box (rack-local x, y in [0, 0.12] m, z < 0.10)
                  at the time limit; final frames show it still in the gripper at the slot (not confirmed);
  in the air:     outside the rack footprint and > 7 cm above the floor (a vial lying on the mat sits at 5 cm);
  above the rack: inside the footprint but above the slot entry (z >= 0.10 rack-local);
  lying in/across the rack: inside the success box but not upright;
  on the mat:     <= 7 cm; split by whether it ended within 5 cm of where it started.
Sweep v1 S0 nominal is shown for reference. Writes results/explore_v2/tilt_failure_modes.json and notes/tilt_failure_modes.md.
"""
import collections
import json
import math
from pathlib import Path

GTC = Path(__file__).resolve().parents[1]
FILES = {"S0 nominal (reference)": "results/sim/S0_nominal.jsonl", "tilt 12": "results/explore_v1/X_tilt_down_12.jsonl",
         "tilt 13": "results/explore_v2/Y_tilt_down_13.jsonl", "tilt 14": "results/explore_v2/Y_tilt_down_14.jsonl",
         "tilt 15": "results/explore_v1/X_tilt_down_15.jsonl"}
STATES = ["held upright at a rack slot at the time limit", "in the air outside the rack (likely still held)",
          "above the rack", "lying in/across the rack, not upright", "on the mat > 5 cm from its start (released or dropped)",
          "on the mat < 5 cm from its start (dropped near the pick)", "no vial moved"]


def upright(q):
    w, x, y, z = q
    return abs(1 - 2 * (x * x + y * y)) > 0.7          # the vial's axis (local z) close to world vertical


def classify(r):
    moved = sorted(((math.dist(r["start_objects"][v]["pos"], r["final_objects"][v]["pos"]), v)
                    for v in ("vial_1", "vial_2", "vial_3")), reverse=True)
    n_moved = sum(d > 0.02 for d, _ in moved)
    if not n_moved:
        return None, STATES[6], 0
    v = moved[0][1]
    lx, ly, lz = r["final_vial_rack_local"][v]
    in_box = 0 <= lx <= 0.12 and 0 <= ly <= 0.12
    if in_box and lz < 0.10 and upright(r["final_objects"][v]["quat_wxyz"]):
        return v, STATES[0], n_moved
    if in_box and lz >= 0.10:
        return v, STATES[2], n_moved
    if in_box:
        return v, STATES[3], n_moved
    if r["final_objects"][v]["pos"][2] > 0.07:
        return v, STATES[1], n_moved
    near = math.dist(r["start_objects"][v]["pos"][:2], r["final_objects"][v]["pos"][:2]) < 0.05
    return v, STATES[5] if near else STATES[4], n_moved


def main():
    out, md = {}, ["# Where the vial ended in failed episodes (camera tilt 12-15 deg)", "",
                   "_explore-v1/v2 logs (not part of prereg-v1); tools/tilt_failure_modes.py. Every failure ran to the "
                   "450-step limit. Counts of failed episodes._", "",
                   "| cell | failures | grasp flag | vial moved most | " + " | ".join(STATES) + " |",
                   "|---" * (4 + len(STATES)) + "|"]
    for name, f in FILES.items():
        rows = [json.loads(l) for l in open(GTC / f)]
        fails = [r for r in rows if r["status"] == "ok" and not r["success"]]
        vials, states = collections.Counter(), collections.Counter()
        for r in fails:
            v, s, _ = classify(r)
            vials[v or "none"] += 1
            states[s] += 1
        out[name] = {"failures": len(fails), "episodes": len(rows), "grasped_flag": sum(r["grasped"] for r in fails),
                     "timeouts": sum(r["steps"] >= r["max_steps"] for r in fails), "vial_moved_most": dict(vials),
                     "end_state": {s: states.get(s, 0) for s in STATES}}
        md.append(f"| {name} | {len(fails)}/{len(rows)} | {out[name]['grasped_flag']} | "
                  + ", ".join(f"{k} {n}" for k, n in vials.most_common()) + " | "
                  + " | ".join(str(states.get(s, 0)) for s in STATES) + " |")
    (GTC / "results" / "explore_v2" / "tilt_failure_modes.json").write_text(json.dumps(out, indent=1))
    (GTC / "notes" / "tilt_failure_modes.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
