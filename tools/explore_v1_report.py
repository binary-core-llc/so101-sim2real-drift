#!/usr/bin/env python3
"""explore-v1 summary (added after seeing sweep v1, not part of prereg-v1); also used for explore-v2.

    python3 -I tools/explore_v1_report.py                      # explore-v1
    python3 -I tools/explore_v1_report.py explore_v2           # config/explore_v2_cells.csv, results/explore_v2
Per cell in config/explore_v1_cells.csv, from results/explore_v1/<cell>.jsonl: k/n successes (Wilson 95% CI),
difference from sweep v1 S0 nominal (results/sim/S0_nominal.jsonl, seeds 0-39 x 5) with a Newcombe 95% CI and a
two-sided Fisher p, grasps, median steps, readback status, and the split by framing (rack + 3 vials fully in frame at
that seed, results/explore_v1/framing_explore_v1.json) against S0 on the same seeds.
Writes results/explore_v1/explore_v1_summary.json and notes/explore_v1_summary.md. Stdlib only.
"""
import csv
import json
import math
import statistics as st
import sys
from pathlib import Path

GTC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GTC / "sim"))
from pilot_report import fisher_two_sided, wilson  # noqa: E402

TAGS = {"explore_v1": "explore-v1: added after seeing sweep v1, not part of prereg-v1",
        "explore_v2": "explore-v2: added after sweep v1 and explore-v1, not part of prereg-v1"}


def rows_of(p):
    return [r for r in (json.loads(l) for l in open(p)) if r.get("status") == "ok"] if p.exists() else []


def newcombe(k1, n1, k2, n2):
    """95% CI of p1 - p2 from the two Wilson intervals (Newcombe 1998, method 10)."""
    p1, p2 = k1 / n1, k2 / n2
    (l1, u1), (l2, u2) = wilson(k1, n1), wilson(k2, n2)
    d = p1 - p2
    return (round(d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2), 3), round(d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2), 3))


def readback_status(ok):
    v = [r.get("readback", {}).get("pass") for r in ok]
    if not v:
        return "no rows"
    if all(x is True for x in v):
        return "pass"
    if any(x is False for x in v):
        return f"FAIL ({sum(x is False for x in v)})"
    return "not checked"


def main(name="explore_v1"):
    TAG = TAGS[name]
    s0 = rows_of(GTC / "results" / "sim" / "S0_nominal.jsonl")
    k0, n0 = sum(r["success"] for r in s0), len(s0)
    s0_by_seed = {}
    for r in s0:
        s0_by_seed.setdefault(r["seed"], []).append(r["success"])
    fr = json.loads((GTC / "results" / name / f"framing_{name}.json").read_text())
    all_in = {(r["set"], r["seed"]): r["all_in"] for r in fr["rows"]}
    out = []
    for c in csv.DictReader(open(GTC / "config" / f"{name}_cells.csv")):
        cid = c["cell_id"]
        ok = rows_of(GTC / "results" / name / f"{cid}.jsonl")
        k, n = sum(r["success"] for r in ok), len(ok)
        rec = {"cell": cid, "overrides": json.loads(c["overrides_json"]), "n_requested": int(c["n_episodes"]), "n": n,
               "successes": k, "rate": round(k / n, 3) if n else None, "wilson95": wilson(k, n),
               "grasped": sum(r["grasped"] for r in ok), "median_steps": st.median([r["steps"] for r in ok]) if ok else None,
               "mean_wall_s": round(st.mean([r["wall_s"] for r in ok]), 2) if ok else None,
               "readback": readback_status(ok), "seeds": sorted(r["seed"] for r in ok)}
        if n:
            rec["vs_S0"] = {"S0": f"{k0}/{n0}", "diff": round(k / n - k0 / n0, 3), "newcombe95": newcombe(k, n, k0, n0),
                            "fisher_p": round(fisher_two_sided(k, n - k, k0, n0 - k0), 4)}
            split = {}
            # a cell with no scene overrides (e.g. only the instruction changes) has the nominal framing
            fkey = cid if (cid, 0) in all_in or json.loads(c["overrides_json"] or "{}") else "nominal"
            for label, want in (("all_in_frame", True), ("not_all_in_frame", False)):
                sub = [r for r in ok if all_in.get((fkey, r["seed"])) is want]
                ref = [x for r in sub for x in s0_by_seed.get(r["seed"], [])]
                if sub:
                    split[label] = {"seeds": len(sub), "k": sum(r["success"] for r in sub),
                                    "S0_same_seeds": f"{sum(ref)}/{len(ref)}"}
            rec["framing_split"] = split
        out.append(rec)
    (GTC / "results" / name / f"{name}_summary.json").write_text(json.dumps({"note": TAG, "cells": out}, indent=1))
    md = [f"# {name.replace('_', '-')} summary", "", f"_{TAG}._ Reference: sweep v1 S0 nominal {k0}/{n0} "
          f"({k0 / n0:.3f}, Wilson {wilson(k0, n0)[0]}-{wilson(k0, n0)[1]}). Seeds 0-39, all randomization at center except the listed factors.", "",
          "| cell | k/n | rate (Wilson 95%) | diff vs S0 (Newcombe 95%) | Fisher p | grasped | median steps | readback | in frame: k/seeds (S0 same seeds) | not in frame: k/seeds (S0 same seeds) |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for r in out:
        v, sp = r.get("vs_S0"), r.get("framing_split", {})
        cell = lambda s: f"{s['k']}/{s['seeds']} ({s['S0_same_seeds']})" if s else "-"
        md.append(f"| {r['cell']} | {r['successes']}/{r['n']} | {r['rate']} ({r['wilson95'][0]}-{r['wilson95'][1]}) | "
                  + (f"{v['diff']:+.3f} ({v['newcombe95'][0]:+.3f} to {v['newcombe95'][1]:+.3f}) | {v['fisher_p']} | " if v else "- | - | ")
                  + f"{r['grasped']}/{r['n']} | {r['median_steps']} | {r['readback']} | "
                  f"{cell(sp.get('all_in_frame'))} | {cell(sp.get('not_all_in_frame'))} |")
    (GTC / "notes" / f"{name}_summary.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main(*sys.argv[1:2])
