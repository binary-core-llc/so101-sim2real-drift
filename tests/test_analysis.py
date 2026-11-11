#!/usr/bin/env python3
"""analysis/stats.py, analysis/thresholds.py and analysis/real.py on cases with known answers (numpy only).

    .venv/bin/python -I tests/test_analysis.py
1. Exact CMH = brute-force enumeration of every table set with the strata's margins (1e-12); one stratum = Fisher.
2. Power by exact enumeration with 12 vs 12 trials per stratum (v1 §6): the stratified exact CMH gives
   H1a 0.874 / 0.928 (alpha 0.025 / 0.05; 60 % vs 15 %), H3a 0.900 / 0.948 (55 % vs 10 %). v1 prints 0.88 / 0.93
   and 0.91, which pooled one-sided Fisher on 24 vs 24 reproduces (0.876 / 0.928 / 0.908); printed for the record.
3. Adjusted Wald: m = 2 and c = (1, -1) is Agresti-Caffo (add 1 success and 2 trials to each group), by formula.
4. Holm, Wilcoxon zero handling and the exact all-positive case (p = 2^-n), cluster permutation = brute force,
   kappa, Newcombe on a hand case.
5. Threshold fit: a logistic with t = 3 and plenty of episodes is recovered within 0.1; flat data are censored.
6. real.py end to end on synthetic trials, photo scores and H4 inputs with known answers; the CLI writes its JSON.
"""
import itertools
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

GTC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GTC / "analysis"))
import real as R  # noqa: E402
import stats as A  # noqa: E402
import thresholds as T  # noqa: E402

ok = True


def check(name, cond, info=""):
    global ok
    ok &= bool(cond)
    print(f"  {name:60s} {'ok' if cond else 'FAIL'} {info}")


print("1. exact CMH")
rng = np.random.default_rng(3)
worst = 0.0
for _ in range(60):
    strata = []
    for _ in range(int(rng.integers(1, 4))):
        n1, n2 = (int(v) for v in rng.integers(1, 7, 2))
        strata.append((int(rng.integers(0, n1 + 1)), n1, int(rng.integers(0, n2 + 1)), n2))
    t_obs = sum(s[0] for s in strata)
    supports = []
    for a, n1, b, n2 in strata:
        m, N = a + b, n1 + n2
        supports.append([(x, math.comb(n1, x) * math.comb(n2, m - x) / math.comb(N, m))
                         for x in range(max(0, m - n2), min(n1, m) + 1)])
    brute = sum(math.prod(p for _, p in combo) for combo in itertools.product(*supports)
                if sum(x for x, _ in combo) >= t_obs)
    worst = max(worst, abs(A.exact_cmh(strata, "greater")["p"] - brute))
check("exact CMH = brute force (60 random strata sets)", worst < 1e-12, f"max diff {worst:.2g}")
check("one stratum = Fisher one-sided", abs(A.exact_cmh([(9, 12, 3, 12)])["p"] - A.fisher_exact(9, 12, 3, 12, "greater")) < 1e-15)

print("2. power (v1 §6)")


def power_cmh(p_in, p_out, alpha, n=12):
    pin, pout, cache, tot = A.binom_pmf(n, p_in), A.binom_pmf(n, p_out), {}, 0.0
    for a1, b1, a2, b2 in itertools.product(range(n + 1), repeat=4):
        pr = pin[a1] * pout[b1] * pin[a2] * pout[b2]
        if pr < 1e-15:
            continue
        key = tuple(sorted([(a1, b1), (a2, b2)]))
        if key not in cache:
            cache[key] = A.exact_cmh([(a1, n, b1, n), (a2, n, b2, n)])["p"]
        tot += pr * (cache[key] <= alpha)
    return tot


def power_fisher(p_in, p_out, alpha, n=24):
    pin, pout = A.binom_pmf(n, p_in), A.binom_pmf(n, p_out)
    return sum(pin[a] * pout[b] for a in range(n + 1) for b in range(n + 1)
               if A.fisher_exact(a, n, b, n, "greater") <= alpha)


pw = {k: power_cmh(*v) for k, v in {"H1a .025": (.6, .15, .025), "H1a .05": (.6, .15, .05),
                                    "H3a .025": (.55, .10, .025), "H3a .05": (.55, .10, .05)}.items()}
pf = {k: power_fisher(*v) for k, v in {"H1a .025": (.6, .15, .025), "H1a .05": (.6, .15, .05),
                                       "H3a .025": (.55, .10, .025)}.items()}
print("     stratified exact CMH:", {k: round(float(v), 4) for k, v in pw.items()})
print("     pooled Fisher 24 v 24:", {k: round(float(v), 4) for k, v in pf.items()}, " v1 prints 0.88, 0.93, 0.91")
check("CMH power H1a 0.025 = 0.8736", abs(pw["H1a .025"] - 0.8736) < 5e-4)
check("CMH power H3a 0.025 = 0.9005", abs(pw["H3a .025"] - 0.9005) < 5e-4)
check("pooled Fisher reproduces v1's 0.88 / 0.93 / 0.91 (rounded)",
      round(pf["H1a .025"], 2) == 0.88 and round(pf["H1a .05"], 2) == 0.93 and round(pf["H3a .025"], 2) == 0.91)

print("3. adjusted Wald")
y1, n1, y2, n2 = 9, 12, 3, 12
p1, p2 = (y1 + 1) / (n1 + 2), (y2 + 1) / (n2 + 2)
z = (p1 - p2) / math.sqrt(p1 * (1 - p1) / (n1 + 2) + p2 * (1 - p2) / (n2 + 2))
r = A.adjusted_wald([y1, y2], [n1, n2], [1, -1], "greater")
check("m = 2, c = (1, -1) is Agresti-Caffo", abs(r["z"] - z) < 1e-12 and abs(r["p"] - (1 - A.norm_cdf(z))) < 1e-12)
r = A.adjusted_wald([10, 15], [24, 25], [1, -0.5], "greater")
q1, q2 = 11 / 26, 16 / 27
z = (q1 - 0.5 * q2) / math.sqrt(q1 * (1 - q1) / 26 + 0.25 * q2 * (1 - q2) / 27)
check("p_inside - 0.5 p_nominal by formula", abs(r["z"] - z) < 1e-12)

print("4. Holm, Wilcoxon, permutation, kappa, Newcombe")
check("Holm (0.01, 0.04): both rejected", A.holm([0.01, 0.04]) == ([True, True], [0.02, 0.04]))
check("Holm (0.03, 0.04): none rejected", A.holm([0.03, 0.04])[0] == [False, False])
check("Holm (0.02, 0.06): first only", A.holm([0.02, 0.06])[0] == [True, False])
w = A.wilcoxon_signed_rank([0.0, 0.0, 1.0, 2.0, 3.0, 4.0, 5.0], "greater")
check("Wilcoxon: zeros dropped, all positive -> p = 2^-5", w["n"] == 5 and abs(w["p"] - 2 ** -5) < 1e-15)
strata = [[(3, 4, True), (1, 4, False), (4, 4, True), (2, 4, False)], [(2, 4, True), (0, 4, False), (1, 3, False)]]
t_obs = 3 + 4 + 2
vals = []
for c1 in itertools.combinations(range(4), 2):
    for c2 in itertools.combinations(range(3), 1):
        vals.append(sum(strata[0][i][0] for i in c1) + sum(strata[1][i][0] for i in c2))
cp = A.cluster_permutation(strata)
check("cluster permutation = brute force", abs(cp["p"] - np.mean(np.array(vals) >= t_obs)) < 1e-15, f"p {cp['p']:.4f}")
check("kappa: identical ratings = 1", A.cohen_kappa([1, 0, 1, 1], [1, 0, 1, 1]) == 1.0)
check("kappa: hand case 0.5", abs(A.cohen_kappa([1, 1, 0, 0], [1, 0, 0, 0]) - 0.5) < 1e-12)
lo, hi = A.newcombe_diff(9, 12, 3, 12)
check("Newcombe contains the difference 0.5", lo < 0.5 < hi and -1 <= lo and hi <= 1, f"({lo:.3f}, {hi:.3f})")

print("5. threshold fit")
x = np.array([1.0, 2.0, 2.5, 3.0, 3.5, 4.0, 6.0])
p0, h, t_true, k_true = 0.6, 2.865, 3.0, 4.0
p = p0 / (1 + np.exp(k_true * (x - t_true) / h))
n = np.full(len(x), 20000.0)
fit = T.fit_point(x, np.round(p * n), n, p0, h)
check("logistic t = 3 recovered within 0.1", not fit["censored"] and abs(fit["t"] - 3.0) < 0.1, f"t {fit['t']:.3f}")
flat = T.fit_point(x, np.full(len(x), 24.0), np.full(len(x), 40.0), 0.62, h)
check("flat data (0.6 at every level) censored", flat["censored"])

print("6. real.py end to end")
rows, uid = [], 0


def add(cond, k, n, **kw):
    global uid
    for i in range(n):
        uid += 1
        rows.append(dict(uid=f"T{uid:03d}", condition=cond, day="2026-11-05", success=i < k, invalid=None, flags=[],
                         **{key: (v(i) if callable(v) else v) for key, v in kw.items()}))


add("R1", 6, 10, role="gate", success_live=lambda i: i < 6)
add("R1", 9, 15, role="control")
add("R2", 2, 12)
add("R3", 9, 12)
add("R4", 3, 12)
add("R5", 8, 12)
add("R6", 8, 12, cycle=lambda i: i // 4)
add("R7", 7, 12, cycle=lambda i: i // 4)
rows.append(dict(uid="T999", condition="R2", day="2026-11-05", success=False, invalid="I3", flags=[]))
res = R.analyse(rows)
c = res["conditions"]
check("k/n per condition and invalid excluded", c["R1"]["k"] == 15 and c["R1"]["n"] == 25 and c["R2"]["n"] == 12
      and res["decision_checks"]["invalid"] == {"I3": 1})
t = res["tests"]
check("H1a = exact CMH on (R3 v R2, R5 v R4)",
      abs(t["H1a"]["p"] - A.exact_cmh([(9, 12, 2, 12), (8, 12, 3, 12)])["p"]) < 1e-15, f"p {t['H1a']['p']:.4g}")
check("H3a = exact CMH on (R6 v R2, R7 v R4)",
      abs(t["H3a"]["p"] - A.exact_cmh([(8, 12, 2, 12), (7, 12, 3, 12)])["p"]) < 1e-15, f"p {t['H3a']['p']:.4g}")
rej, adj = A.holm([t["H1a"]["p"], t["H3a"]["p"]])
check("Holm across H1a and H3a", [t["H1a"]["holm_reject"], t["H3a"]["holm_reject"]] == rej)
check("H1c on outside 5/24 vs 0.5 x 15/25", abs(t["H1c"]["z"] - A.adjusted_wald([5, 15], [24, 25], [1, -0.5], "less")["z"]) < 1e-15)
check("H1 verdict: H1a rejects, H1c does not (5/24 vs 0.3), not falsified -> inconclusive",
      t["H1a"]["holm_reject"] and t["H1c"]["p"] > 0.05 and t["H1_verdict"] == "not supported (inconclusive)")
check("D1 gate 6/10 not low", res["decision_checks"]["D1_gate"] == {"k": 6, "n": 10, "low_nominal": False})
check("kappa present", res["kappa_live_vs_blind"]["n"] == 10 and res["kappa_live_vs_blind"]["kappa"] == 1.0)
photos = [{"photo_id": f"P{i}", "kind": "camera", "set": "TEST",
           "truth_delta": {"pitch": 0.1 + 0.01 * i, "x": 0.01},
           "estimates": {"E3": {"pitch": -(0.1 + 0.01 * i), "x": -0.01}, "E1a": None}} for i in range(6)]
photos.append({"photo_id": "DEV1", "kind": "rack", "set": "DEV", "truth_delta": {"y": 0.03}, "estimates": {}})
hb = R.h3b(photos, "E1a")
check("H3b: E3 perfect vs E1 missing -> p = 2^-6, DEV excluded",
      hb["n_photos"] == 6 and abs(hb["wilcoxon"]["p"] - 2 ** -6) < 1e-15 and hb["median_score"]["E3"] == 0.0)
check("H3b: missing estimate scores as predict-zero", hb["median_score"]["E1a"] == hb["median_score"]["predict_zero"])
h4 = R.h4({"sim_intrinsics": [124, 200], "c920_measured": [110, 200], "fx_measured_px": 520.0})
check("H4: fx gap 1 % -> pose-matched", h4["real_nominal_placement"] == "pose-matched" and abs(h4["fx_gap"] - 5.3 / 514.7) < 1e-12)
h4b = R.h4({"sim_intrinsics": [124, 200], "c920_measured": [60, 200], "c920_image_matched": [150, 200],
            "fx_measured_px": 455.0})
check("H4: fx gap > 5 % and image-matched clearly better -> image-matched", h4b["real_nominal_placement"] == "image-matched")
h4c = R.h4({"sim_intrinsics": [124, 200], "c920_measured": [110, 200], "c920_image_matched": [118, 200],
            "fx_measured_px": 455.0})
check("H4: fx gap > 5 % but CIs overlap -> pose-matched", h4c["real_nominal_placement"] == "pose-matched")
with tempfile.TemporaryDirectory() as d:
    tp, pp, op = Path(d) / "trials.jsonl", Path(d) / "photos.jsonl", Path(d) / "out.json"
    tp.write_text("".join(json.dumps(r) + "\n" for r in rows))
    pp.write_text("".join(json.dumps(r) + "\n" for r in photos))
    cp = subprocess.run([sys.executable, "-I", str(GTC / "analysis" / "real.py"), "--trials", str(tp), "--photos",
                         str(pp), "--e1-variant", "E1a", "--out", str(op)], capture_output=True, text=True)
    out = json.loads(op.read_text()) if op.exists() else {}
    check("CLI runs and writes JSON", cp.returncode == 0 and out.get("n_valid") == 97, (cp.stderr or "")[-300:])
    print("\n".join("     " + l for l in cp.stdout.splitlines()))

print("ANALYSIS TEST PASS" if ok else "ANALYSIS TEST FAIL")
sys.exit(0 if ok else 1)
