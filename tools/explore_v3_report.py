#!/usr/bin/env python3
"""explore-v3 report, as fixed in notes/explore_v3_plan.md before running.

    python3 -I tools/explore_v3_report.py                    # latency = explore-v1 median policy latency
    python3 -I tools/explore_v3_report.py --latency-s 0.095  # e.g. a pilot's latency (recomputes cutoff c)
Per success: success step s (the episode ends after the 25-step hold), release step r = s - 25, chunk = ceil((r - 10) / 16).
Cutoffs: (a) s <= 450 (the sim budget); (b) chunk <= 28; (c) chunk <= 58 / (16/30 + latency); full = any success
within the 1775-step episode. k/40 with Wilson 95 % CI. (a) is compared with the earlier runs (independent replicate:
the server's sampling is not seeded). Rule: a tilt level qualifies as the H3a correction mis-setup if at (c) its
success is <= 25 % while nominal is >= 50 %.
Writes results/explore_v3/explore_v3_successes.json, results/explore_v3/explore_v3_summary.json, notes/explore_v3_summary.md.
"""
import argparse
import csv
import json
import math
import statistics as st
import sys
from pathlib import Path

GTC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GTC / "sim"))
from pilot_report import fisher_two_sided, wilson  # noqa: E402

TAG = "explore-v3: added after explore-v2, not part of prereg-v1"
EARLIER = {"Z_nominal_long": ("S0 nominal, seeds 0-39 x 5", "results/sim/S0_nominal.jsonl"),
           "Z_tilt_down_13_long": ("explore-v2 tilt 13", "results/explore_v2/Y_tilt_down_13.jsonl"),
           "Z_tilt_down_15_long": ("explore-v1 tilt 15", "results/explore_v1/X_tilt_down_15.jsonl")}


def rows_of(p):
    p = GTC / p
    return [r for r in (json.loads(l) for l in open(p)) if r.get("status") == "ok"] if p.exists() else []


def explore_v1_latency():
    lat = [r["policy_s"] / r["queries"] for f in sorted((GTC / "results" / "explore_v1").glob("X_*.jsonl"))
           for r in rows_of(f.relative_to(GTC)) if r["queries"]]
    return st.median(lat), len(lat)


def frac(k, n):
    w = wilson(k, n)
    return {"k": k, "n": n, "rate": round(k / n, 3) if n else None, "wilson95": w}


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--latency-s", type=float, default=None)
    a = ap.parse_args(argv)
    lat_src = "argument"
    if a.latency_s is None:
        a.latency_s, n_lat = explore_v1_latency()
        lat_src = f"explore-v1 median policy latency over {n_lat} episodes"
    n_c = 58 / (16 / 30 + a.latency_s)
    cells = [r["cell_id"] for r in csv.DictReader(open(GTC / "config" / "explore_v3_cells.csv"))]
    succ, summ = [], {}
    for c in cells:
        rows = rows_of(f"results/explore_v3/{c}.jsonl")
        n = len(rows)
        s_rows = []
        for r in rows:
            if r["success"]:
                rel = r["steps"] - 25
                chunk = math.ceil((rel - 10) / 16)
                s_rows.append({"cell": c, "episode": r["episode"], "seed": r["seed"], "success_step": r["steps"],
                               "release_step": rel, "release_chunk": chunk})
        succ += s_rows
        k_a = sum(s["success_step"] <= 450 for s in s_rows)
        k_b = sum(s["release_chunk"] <= 28 for s in s_rows)
        k_c = sum(s["release_chunk"] <= n_c for s in s_rows)
        e_label, e_path = EARLIER[c]
        e_rows = rows_of(e_path)
        ek = sum(r["success"] for r in e_rows)
        summ[c] = {"n": n, "max_steps": sorted({r["max_steps"] for r in rows}),
                   "a_450_steps": frac(k_a, n), "b_28_chunks": frac(k_b, n), "c_58s_real_pace": frac(k_c, n),
                   "full_1775_steps": frac(len(s_rows), n),
                   "earlier_at_450": {"label": e_label, "k": ek, "n": len(e_rows),
                                      "fisher_p_vs_a": round(fisher_two_sided(k_a, n - k_a, ek, len(e_rows) - ek), 4) if n else None},
                   "release_chunks": sorted(s["release_chunk"] for s in s_rows)}
    nom = summ.get("Z_nominal_long", {}).get("c_58s_real_pace", {})
    rule = {}
    for c in ("Z_tilt_down_13_long", "Z_tilt_down_15_long"):
        t = summ.get(c, {}).get("c_58s_real_pace", {})
        if t.get("n") and nom.get("n"):
            rule[c] = {"tilt_rate_c": t["rate"], "nominal_rate_c": nom["rate"],
                       "qualifies": t["rate"] <= 0.25 and nom["rate"] >= 0.50}
    out = {"note": TAG, "latency_s": a.latency_s, "latency_source": lat_src, "cutoff_c_chunks": n_c, "cells": summ, "rule": rule}
    (GTC / "results" / "explore_v3" / "explore_v3_successes.json").write_text(json.dumps(succ, indent=1))
    (GTC / "results" / "explore_v3" / "explore_v3_summary.json").write_text(json.dumps(out, indent=1))

    def cell(f):
        return f"{f['k']}/{f['n']} ({f['wilson95'][0]}-{f['wilson95'][1]})" if f.get("n") else "-"
    md = ["# explore-v3 summary", "", f"_{TAG}._ Episode length 1775 steps; seeds 0-39; cutoffs fixed in notes/explore_v3_plan.md.",
          f"Cutoff (c) = 58 / (16/30 + {a.latency_s * 1000:.1f} ms) = {n_c:.2f} chunks ({lat_src}).", "",
          "| cell | (a) step <= 450 | earlier at 450 (Fisher p vs a) | (b) chunk <= 28 | (c) chunk <= %.2f | full 1775 |" % n_c,
          "|---|---|---|---|---|---|"]
    for c, s in summ.items():
        e = s["earlier_at_450"]
        md.append(f"| {c} | {cell(s['a_450_steps'])} | {e['label']}: {e['k']}/{e['n']} (p {e['fisher_p_vs_a']}) | "
                  f"{cell(s['b_28_chunks'])} | {cell(s['c_58s_real_pace'])} | {cell(s['full_1775_steps'])} |")
    md += ["", "Rule (fixed before running): a tilt level qualifies as the H3a correction mis-setup if at (c) its success is "
           "<= 25 % while nominal is >= 50 %."]
    for c, r in rule.items():
        md.append(f"- {c}: tilt {r['tilt_rate_c']:.3f}, nominal {r['nominal_rate_c']:.3f} -> "
                  f"{'QUALIFIES' if r['qualifies'] else 'does not qualify'}")
    md += ["", "Release chunk of every success (sorted):"] + [f"- {c}: {s['release_chunks']}" for c, s in summ.items()]
    (GTC / "notes" / "explore_v3_summary.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
