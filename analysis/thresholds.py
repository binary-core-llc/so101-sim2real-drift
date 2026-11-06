#!/usr/bin/env python3
"""Simulated thresholds per geometric factor (PREREGISTRATION_v1.md §4) from the sweep v1 episodes.

    .venv/bin/python -I analysis/thresholds.py            # writes results/analysis/thresholds_v1.{json,md}
Input: config/cells_sweep_v1.csv (cell levels from overrides_json) and results/sim/<cell>.jsonl (one row per
episode; all rows must be status "ok" and stamped gtc@0f2b1f7). Factors: S1 camera tilt down (deg, code pitch),
S2 rack toward the camera wall (cm), S3 rack toward the back wall (cm), S7 camera yaw (code deg; v1: +10 deg code =
16.7 deg physical pan), S8 camera raised (cm). Training half-ranges (v1 §2): pitch and yaw 0.05 rad = 2.865 deg,
camera z 1 cm, rack x 4 cm, rack y 1 cm.

Model (v1 §4: logistic, upper asymptote fixed at the S0 rate, threshold = offset where success is half of S0):
    P(success | x) = p0 / (1 + exp(k (x - t) / h)),  k >= 0,  so P(t) = p0 / 2,
p0 = the S0 success rate (124/200 in v1), h = the training half-range (scale only), t the threshold. Choices for v2
to fix: the fit uses the factor's own cells only (S0 enters through p0, not as a point at x = 0); maximum likelihood
on a grid (t: 400 steps over [0, largest level], then 100 log steps to 1000 x the largest level; k: 40 log steps
over [0.01, 1000]) refined by Nelder-Mead for the point estimate; censored when t > the largest level tested (the
fitted curve never falls below half within the tested range; the curve that never falls at all is t -> infinity).
CI: 2,000 bootstrap resamples by seed: the 40 vial seeds are drawn with replacement, and every episode with a drawn
seed is kept (S0's 5 repeats per seed included, so p0 is resampled too); the same resampled seed sets serve every
factor; percentile 2.5 / 97.5 with censored resamples counted as +infinity. RNG: numpy default_rng(20261103).
Registered prediction (v1 §4): met when the threshold is not censored and its 95 % CI overlaps [1 h, 2 h].
"""
import csv
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np

GTC = Path(__file__).resolve().parents[1]
CELLS = GTC / "config" / "cells_sweep_v1.csv"
SIM = GTC / "results" / "sim"
OUT = GTC / "results" / "analysis"
STAMP = "0f2b1f7"
SEED, B = 20261103, 2000
FACTORS = {   # prefix: (name, overrides path, to display units, half-range in those units, units)
    "S1": ("camera tilt down", ("camera", "pitch"), math.degrees, math.degrees(0.05), "deg"),
    "S2": ("rack toward the camera wall", ("rack", "y"), lambda v: v * 100, 1.0, "cm"),
    "S3": ("rack toward the back wall", ("rack", "x"), lambda v: v * 100, 4.0, "cm"),
    "S7": ("camera yaw", ("camera", "yaw"), math.degrees, math.degrees(0.05), "deg code"),
    "S8": ("camera raised", ("camera", "z"), lambda v: v * 100, 1.0, "cm"),
}
YAW_CODE_TO_PHYSICAL = 16.7 / 10.0   # v1 §4 table, S7 row


def load_cell(cell):
    rows = [json.loads(l) for l in open(SIM / f"{cell}.jsonl")]
    bad = [r for r in rows if r["status"] != "ok" or not r["gtc_git"].startswith(STAMP)]
    if bad:
        raise SystemExit(f"STOP: {cell}: {len(bad)} rows not ok or not stamped gtc@{STAMP}")
    return rows


def seed_matrix(rows, n_seeds=40):
    """Successes per seed (array of length n_seeds) and episodes per seed."""
    s, n = np.zeros(n_seeds, int), np.zeros(n_seeds, int)
    for r in rows:
        s[r["seed"]] += int(bool(r["success"]))
        n[r["seed"]] += 1
    return s, n


def loglik(k_obs, n_obs, p0, q):
    """Binomial log-likelihood; q (..., L) = P/p0 per level; k_obs, n_obs (..., L); p0 broadcastable to q[..., 0]."""
    p = np.clip(p0[..., None] * q, 1e-12, 1 - 1e-12)
    return (k_obs * np.log(p) + (n_obs - k_obs) * np.log1p(-p)).sum(-1)


def grids(xmax):
    t = np.concatenate([np.linspace(0, xmax, 401), xmax * np.logspace(np.log10(1.02), 3, 100)])
    k = np.logspace(-2, 3, 40)
    return t, k


def q_of(x, t, k, h):
    """P/p0 at the levels x for every (t, k): shape (len(t) * len(k), len(x))."""
    T, K = np.meshgrid(t, k, indexing="ij")
    z = K.ravel()[:, None] * (x[None, :] - T.ravel()[:, None]) / h
    return 1.0 / (1.0 + np.exp(np.clip(z, -700, 700))), T.ravel(), K.ravel()


def nelder_mead(f, x0, step, iters=400):
    pts = [np.array(x0, float)] + [np.array(x0, float) + np.eye(len(x0))[i] * step[i] for i in range(len(x0))]
    vals = [f(p) for p in pts]
    for _ in range(iters):
        o = np.argsort(vals)
        pts, vals = [pts[i] for i in o], [vals[i] for i in o]
        c = np.mean(pts[:-1], axis=0)
        xr = c + (c - pts[-1])
        fr = f(xr)
        if fr < vals[0]:
            xe = c + 2 * (c - pts[-1])
            fe = f(xe)
            pts[-1], vals[-1] = (xe, fe) if fe < fr else (xr, fr)
        elif fr < vals[-2]:
            pts[-1], vals[-1] = xr, fr
        else:
            xc = c + 0.5 * (pts[-1] - c)
            fc = f(xc)
            if fc < vals[-1]:
                pts[-1], vals[-1] = xc, fc
            else:
                pts = [pts[0] + 0.5 * (p - pts[0]) for p in pts]
                vals = [f(p) for p in pts]
    i = int(np.argmin(vals))
    return pts[i], vals[i]


def fit_point(x, k_obs, n_obs, p0, h):
    """Maximum-likelihood t (grid, then Nelder-Mead in (t, log k) when the grid optimum is inside the range)."""
    xmax = float(x.max())
    tg, kg = grids(xmax)
    q, T, K = q_of(x, tg, kg, h)
    ll = loglik(k_obs[None, :], n_obs[None, :], np.full(len(T), p0), q)
    i = int(np.argmax(ll))
    t0, k0 = T[i], K[i]
    if t0 > xmax:
        return {"t": None, "censored": True, "t_grid": float(t0), "k": float(k0), "loglik": float(ll[i])}

    def nll(v):
        t, lk = v
        if t < 0:
            return 1e300
        qq = 1.0 / (1.0 + np.exp(np.clip(math.exp(lk) * (x - t) / h, -700, 700)))
        return -float(loglik(k_obs, n_obs, np.array(p0), qq))

    v, f = nelder_mead(nll, [t0, math.log(k0)], [xmax / 50, 0.5])
    if -f < ll[i]:
        v, f = np.array([t0, math.log(k0)]), -ll[i]
    t = float(v[0])
    return {"t": t if t <= xmax else None, "censored": t > xmax, "t_grid": float(t0), "k": float(math.exp(v[1])),
            "loglik": float(-f)}


def bootstrap(x, S_lv, s0, n0_per_seed, h, W):
    """Bootstrap thresholds. S_lv (seeds, L) successes per seed and level (1 episode each); s0 (seeds,) S0 successes
    per seed (n0_per_seed episodes each); W (B, seeds) multiplicities. Censored resamples -> +inf."""
    xmax = float(x.max())
    tg, kg = grids(xmax)
    q, T, K = q_of(x, tg, kg, h)
    k_b = W @ S_lv                                       # (B, L)
    n_b = W.sum(1)[:, None] * np.ones(len(x))            # every seed drawn contributes one episode per level
    p0_b = (W @ s0) / (W.sum(1) * n0_per_seed)
    out = np.empty(len(W))
    logq, log1q = None, None
    for a in range(0, len(W), 25):
        sl = slice(a, a + 25)
        p = np.clip(p0_b[sl, None, None] * q[None], 1e-12, 1 - 1e-12)          # (b, G, L)
        ll = (k_b[sl, None, :] * np.log(p) + (n_b[sl, None, :] - k_b[sl, None, :]) * np.log1p(-p)).sum(-1)
        tb = T[np.argmax(ll, axis=1)]
        out[sl] = np.where(tb > xmax, np.inf, tb)
    return out


def main():
    cells = {r["cell_id"]: r for r in csv.DictReader(open(CELLS))}
    s0_rows = load_cell("S0_nominal")
    s0, n0 = seed_matrix(s0_rows)
    if not (n0 == 5).all():
        raise SystemExit("STOP: S0 must have 5 episodes per seed 0-39")
    p0 = s0.sum() / n0.sum()
    rng = np.random.default_rng(SEED)
    W = np.stack([np.bincount(rng.integers(0, 40, 40), minlength=40) for _ in range(B)])   # (B, 40)
    results, sources = {}, {}
    for pre, (name, path, conv, h, unit) in FACTORS.items():
        ids = [c for c in cells if c.startswith(pre + "_")]
        lv = []
        for c in ids:
            ov = json.loads(cells[c]["overrides_json"])
            raw = ov[path[0]][path[1]]
            rows = load_cell(c)
            res = {(r["resolved"][path[0]][path[1]]) for r in rows}
            if len(res) != 1 or abs(res.pop() - raw) > 1e-9:
                raise SystemExit(f"STOP: {c}: resolved {path} differs from the registered override")
            s, n = seed_matrix(rows)
            if not (n == 1).all():
                raise SystemExit(f"STOP: {c}: expected one episode per seed 0-39")
            lv.append((conv(raw), c, s))
            sources[c] = hashlib.sha256((SIM / f"{c}.jsonl").read_bytes()).hexdigest()
        lv.sort()
        x = np.array([v[0] for v in lv])
        S_lv = np.stack([v[2] for v in lv], axis=1)           # (40, L)
        k_obs, n_obs = S_lv.sum(0).astype(float), np.full(len(x), 40.0)
        pt = fit_point(x, k_obs, n_obs, p0, h)
        tb = bootstrap(x, S_lv.astype(float), s0.astype(float), 5, h, W.astype(float))
        big = 1e300                                           # +inf stand-in, so percentiles stay defined
        lo, hi = np.percentile(np.where(np.isfinite(tb), tb, big), [2.5, 97.5])
        lo = None if lo >= big else float(lo)
        hi = None if hi >= big else float(hi)
        overlaps = (not pt["censored"]) and (lo is not None and lo <= 2 * h) and (hi is None or hi >= h)
        results[pre] = {
            "factor": name, "unit": unit, "half_range": h, "prediction_interval": [h, 2 * h],
            "levels": [{"cell": c, "x": float(v), "k": int(s.sum()), "n": 40} for v, c, s in lv],
            "threshold": pt["t"], "censored": pt["censored"], "fit": pt,
            "ci95": [lo, hi], "ci95_note": "None = censored (above the largest level)",
            "bootstrap_censored_share": float(np.mean(~np.isfinite(tb))),
            "prediction_met": bool(overlaps),
        }
        if pre == "S7":
            results[pre]["physical_pan_per_code"] = YAW_CODE_TO_PHYSICAL
    out = {"p0": {"k": int(s0.sum()), "n": int(n0.sum()), "rate": float(p0), "half": float(p0 / 2)},
           "bootstrap": {"B": B, "rng": f"numpy default_rng({SEED})", "unit": "vial seed (40), shared across factors"},
           "stamp": f"gtc@{STAMP}", "source_sha256": sources,
           "code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "factors": results}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "thresholds_v1.json").write_text(json.dumps(out, indent=1) + "\n")

    def f(v):
        return "censored" if v is None else f"{v:.2f}"

    lines = ["# Simulated thresholds, sweep v1 (PREREGISTRATION_v1.md §4)", "",
             f"S0: {int(s0.sum())}/{int(n0.sum())} = {p0:.3f}; half of nominal = {p0 / 2:.3f}. Bootstrap: {B} "
             f"resamples by vial seed, numpy default_rng({SEED}). Code: `analysis/thresholds.py`.", "",
             "| Factor | Levels | Lowest level rate | Threshold | 95 % CI | Training half-range h | Prediction [h, 2h] |",
             "|---|---|---|---|---|---|---|"]
    for pre, r in results.items():
        lvls = ", ".join(f"{l['x']:g}" for l in r["levels"])
        low = min(l["k"] / l["n"] for l in r["levels"])
        th = "censored (> {:g})".format(r["levels"][-1]["x"]) if r["censored"] else f"{r['threshold']:.2f}"
        share = r["bootstrap_censored_share"]
        ci = (f"above the range ({share:.2%} of resamples censored)" if r["ci95"][0] is None
              else f"{f(r['ci95'][0])} to {f(r['ci95'][1])}")
        lines.append(f"| {pre} {r['factor']} ({r['unit']}) | {lvls} | {low:.3f} | {th} | {ci} | "
                     f"{r['half_range']:.3f} | {'met' if r['prediction_met'] else 'not met'} |")
    lines += ["", "Censored: success never falls to half of S0 within the tested levels; v1 counts a censored "
              "threshold as a prediction not met. S7 is in code units (v1: +10 deg code = 16.7 deg physical pan)."]
    (OUT / "thresholds_v1.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    sys.exit(main())
