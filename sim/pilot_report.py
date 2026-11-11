#!/usr/bin/env python3
"""G3 pilot summary: per cell k/n successes (Wilson 95% CI), grasp rate, steps, s/episode, readback,
statuses, queue attempts and exit lags; extremes vs nominal with a two-sided Fisher exact test.

    python3 -I sim/pilot_report.py [config/cells_pilot.csv]
Writes results/sim/pilot_summary.json and notes/pilot_summary.md. Stdlib only.
"""
import csv
import json
import math
import statistics as st
import sys
from pathlib import Path

GTC = Path(__file__).resolve().parents[1]


def wilson(k, n, z=1.959964):
    if n == 0:
        return (None, None)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(c - h, 3), round(c + h, 3))


def fisher_two_sided(a, b, c, d):
    """2x2 [[a, b], [c, d]]; sum of hypergeometric probabilities <= the observed one."""
    n1, n2, m = a + b, c + d, a + c
    N = n1 + n2

    def pmf(x):
        return math.comb(n1, x) * math.comb(n2, m - x) / math.comb(N, m)
    p0 = pmf(a)
    lo, hi = max(0, m - n2), min(m, n1)
    return min(1.0, sum(pmf(x) for x in range(lo, hi + 1) if pmf(x) <= p0 * (1 + 1e-9)))


def main(cells_path):
    cells = list(csv.DictReader(open(cells_path)))
    state = json.loads((GTC / "queue" / "state.json").read_text()) if (GTC / "queue" / "state.json").exists() else {"cells": {}}
    out, nominal = [], None
    for c in cells:
        p = GTC / "results" / "sim" / f"{c['cell_id']}.jsonl"
        rows = [json.loads(l) for l in open(p)] if p.exists() else []
        ok = [r for r in rows if r.get("status") == "ok"]
        eps = [r["episode"] for r in ok]
        k, n = sum(r["success"] for r in ok), len(ok)
        att = state["cells"].get(c["cell_id"], {}).get("attempts", [])
        rbs = [r["readback"]["pass"] for r in ok]   # None when the cell does not check (as-shipped runs)
        rec = {"cell": c["cell_id"], "notes": c["notes"], "overrides": json.loads(c["overrides_json"] or "{}"),
               "n_requested": int(c["n_episodes"]), "n": n, "successes": k, "rate": round(k / n, 3) if n else None,
               "wilson95": wilson(k, n), "grasped": sum(r["grasped"] for r in ok),
               "median_steps": st.median([r["steps"] for r in ok]) if ok else None,
               "mean_wall_s": round(st.mean([r["wall_s"] for r in ok]), 2) if ok else None,
               "readback_all_pass": (None if not ok else "not checked" if all(v is None for v in rbs)
                                     else all(v is True for v in rbs)),
               "duplicate_episodes": len(eps) - len(set(eps)), "non_ok_rows": len(rows) - n,
               "attempts": len(att), "exit_lag_s": [a.get("exit_lag_s") for a in att],
               "watchdog": [a.get("watchdog") for a in att if a.get("watchdog")]}
        out.append(rec)
        if c["cell_id"].endswith("nominal"):
            nominal = rec
    if nominal:
        for r in out:
            if r is nominal or not r["n"]:
                continue
            # CRN: the first 10 nominal episodes use the same seeds/layouts as each extreme cell
            r["vs_nominal_all"] = {"diff": round(r["rate"] - nominal["rate"], 3),
                                   "fisher_p": round(fisher_two_sided(r["successes"], r["n"] - r["successes"],
                                                                      nominal["successes"], nominal["n"] - nominal["successes"]), 4)}
    (GTC / "results" / "sim" / f"{NAME}.json").write_text(json.dumps(out, indent=1))
    md = [f"# {NAME.replace('_', ' ')}", "", "| cell | k/n | rate (Wilson 95%) | vs nominal (Fisher p) | grasped | median steps | s/ep | readback | attempts, exit lag |",
          "|---|---|---|---|---|---|---|---|---|"]
    for r in out:
        vn = r.get("vs_nominal_all")
        md.append(f"| {r['cell']} | {r['successes']}/{r['n']} | {r['rate']} ({r['wilson95'][0]}-{r['wilson95'][1]}) | "
                  f"{(str(vn['diff']) + ' (p ' + str(vn['fisher_p']) + ')') if vn else '-'} | {r['grasped']}/{r['n']} | "
                  f"{r['median_steps']} | {r['mean_wall_s']} | {'pass' if r['readback_all_pass'] is True else r['readback_all_pass']} | "
                  f"{r['attempts']}, {r['exit_lag_s']} |")
    (GTC / "notes" / f"{NAME}.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    NAME = sys.argv[2] if len(sys.argv) > 2 else "pilot_summary"   # output: results/sim/<NAME>.json, notes/<NAME>.md
    main(sys.argv[1] if len(sys.argv) > 1 else str(GTC / "config" / "cells_pilot.csv"))
