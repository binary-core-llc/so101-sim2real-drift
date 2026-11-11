#!/usr/bin/env python3
"""analysis/stats.py against scipy, on random and edge-case inputs. gtc/.venv has no scipy, so this runs inside the
local real-robot image (scipy 1.15.3, numpy 2.2.6), offline, with gtc mounted read-only:

    docker run --rm --network none -v $HOME/gtc2027/gtc:/gtc:ro --entrypoint /Isaac-GR00T/.venv/bin/python \
        real-robot:latest -I /gtc/tests/test_analysis_scipy.py
Checks (max abs difference in p): Fisher one- and two-sided vs scipy.stats.fisher_exact (1e-12), Boschloo one-sided
vs scipy.stats.boschloo_exact (1e-6, and never below scipy by more than 1e-9: our search is finer), Wilcoxon exact
vs scipy.stats.wilcoxon (no ties: method "exact", 1e-12; ties: exact permutation, 1e-12), McNemar vs
scipy.stats.binomtest (1e-12), Wilson vs scipy.stats.binomtest(...).proportion_ci("wilson") (1e-12),
Clopper-Pearson vs proportion_ci("exact") (1e-9), normal CDF vs scipy.stats.norm (1e-14).
"""
import sys
from pathlib import Path

import numpy as np
import scipy
from scipy import stats as S

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "analysis"))
import stats as A  # noqa: E402

rng = np.random.default_rng(7)
worst = {}


def note(name, diff):
    worst[name] = max(worst.get(name, 0.0), float(diff))


# Fisher
for _ in range(400):
    n1, n2 = rng.integers(1, 30, 2)
    a, b = rng.integers(0, n1 + 1), rng.integers(0, n2 + 1)
    tab = [[a, b], [n1 - a, n2 - b]]
    for alt in ("greater", "less", "two-sided"):
        note(f"fisher {alt}", abs(A.fisher_exact(a, n1, b, n2, alt) - S.fisher_exact(tab, alternative=alt)[1]))

# Boschloo: scipy's table has the groups as columns; check which alternative means "group 1 better"
assert S.boschloo_exact([[10, 0], [0, 10]], alternative="greater").pvalue < 1e-4
bos_below = 0.0
for n1, n2 in ((12, 12), (24, 24), (10, 14), (5, 9), (20, 20)):
    for _ in range(6):
        a, b = rng.integers(0, n1 + 1), rng.integers(0, n2 + 1)
        for alt in ("greater", "less"):
            ours = A.boschloo_exact(a, n1, b, n2, alt)
            ref = S.boschloo_exact([[a, b], [n1 - a, n2 - b]], alternative=alt).pvalue
            note(f"boschloo {alt}", abs(ours - ref))
            bos_below = max(bos_below, ref - ours)

# Wilcoxon, no ties
for _ in range(200):
    n = int(rng.integers(3, 25))
    d = rng.normal(0.3, 1, n)
    for alt in ("greater", "less"):
        note(f"wilcoxon exact {alt}",
             abs(A.wilcoxon_signed_rank(d, alt)["p"] - S.wilcoxon(d, alternative=alt, method="exact").pvalue))
# Wilcoxon with ties and zeros: scipy's exact permutation (zeros dropped first, as our "wilcox" rule)
for _ in range(60):
    n = int(rng.integers(4, 13))
    d = rng.integers(-3, 4, n).astype(float)
    dz = d[d != 0]
    if len(dz) == 0:
        continue
    for alt in ("greater", "less"):
        ref = S.wilcoxon(dz, alternative=alt, method=S.PermutationMethod(n_resamples=np.inf)).pvalue
        note(f"wilcoxon ties {alt}", abs(A.wilcoxon_signed_rank(d, alt)["p"] - ref))

# McNemar, Wilson, Clopper-Pearson, normal
for b in range(0, 15):
    for c in range(0, 15):
        if b + c:
            note("mcnemar", abs(A.mcnemar_exact(b, c) - S.binomtest(min(b, c), b + c, 0.5).pvalue))
for n in (1, 5, 10, 12, 24, 40, 200):
    for k in range(n + 1):
        r = S.binomtest(k, n)
        w, cp = r.proportion_ci(0.95, "wilson"), r.proportion_ci(0.95, "exact")
        note("wilson", max(abs(A.wilson(k, n)[0] - w.low), abs(A.wilson(k, n)[1] - w.high)))
        note("clopper-pearson", max(abs(A.clopper_pearson(k, n)[0] - cp.low), abs(A.clopper_pearson(k, n)[1] - cp.high)))
for z in np.linspace(-6, 6, 101):
    note("norm cdf", abs(A.norm_cdf(z) - S.norm.cdf(z)))

tol = {"fisher": 1e-12, "boschloo": 1e-6, "wilcoxon": 1e-12, "mcnemar": 1e-12, "wilson": 1e-12,
       "clopper-pearson": 1e-9, "norm cdf": 1e-14}
ok = True
print(f"scipy {scipy.__version__}, numpy {np.__version__}")
for k, v in sorted(worst.items()):
    t = tol[k.split(" ")[0] if not k.startswith(("clopper", "norm")) else k]
    good = v <= t
    ok &= good
    print(f"  {k:28s} max |diff| {v:.3g}  (tol {t:g})  {'ok' if good else 'FAIL'}")
print(f"  boschloo: ours below scipy by at most {bos_below:.3g} (must be <= 1e-9)")
ok &= bos_below <= 1e-9
print("ANALYSIS SCIPY CHECK PASS" if ok else "ANALYSIS SCIPY CHECK FAIL")
sys.exit(0 if ok else 1)
