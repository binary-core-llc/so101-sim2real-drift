#!/usr/bin/env python3
"""Statistics for the pre-registered analysis (PREREGISTRATION_v1.md §4 and §6; D_software C18), numpy + stdlib only.

Validated against scipy 1.15.3 (run inside the local real-robot image) by tests/test_analysis_scipy.py, and against
brute-force enumeration and the power numbers printed in v1 §6 by tests/test_analysis.py.

Choices where v1 leaves a detail open (each is listed for v2 to fix):
- Wilson 95 % CI with z = 1.959964 (no continuity correction). Clopper-Pearson by bisection on the exact binomial
  tails. Newcombe's hybrid score interval (method 10) for a difference of two proportions.
- Exact CMH (`exact_cmh`): the conditional test of a common odds ratio of 1, given every stratum's margins; the
  statistic is the summed successes of the first group, whose null law is the convolution of the strata's
  hypergeometric laws. One-sided "greater" = P(T >= t_obs). With one stratum it is Fisher's one-sided test.
- Fisher two-sided: sum of the hypergeometric probabilities <= P(observed) * (1 + 1e-7) (scipy's / R's rule).
- Boschloo one-sided: statistic = Fisher's one-sided p; p-value = the maximum over the common success probability
  pi in [0, 1] of P(Fisher p <= observed Fisher p * (1 + 1e-13)), found on a 20,001-point grid and refined by
  golden-section search around the best grid points (scipy maximises with shgo on 32 Sobol points).
- Adjusted Wald test of a linear contrast L = sum c_i p_i of independent proportions (H1b, H1c): Price & Bonett
  (2004): p~_i = (y_i + 2/m) / (n_i + 4/m) with m = number of proportions in the contrast, SE from the same p~_i
  and n_i + 4/m; z = L~ / SE; one-sided normal p-value. For p_inside - 0.5 * p_nominal, m = 2: add 1 success and
  2 trials to each.
- Wilcoxon signed-rank (H3b): zero differences dropped (Wilcoxon's "wilcox" rule), ties given average ranks, the
  p-value from the exact sign-flip distribution of W+ given those ranks (exact also with ties).
- McNemar: exact two-sided binomial test on the discordant pairs, min(1, 2 * smaller tail).
- Holm: step-down over the family, adjusted p-values reported; family alpha 0.05.
- Cluster permutation (H3a sensitivity): within each stratum the treatment labels are permuted over clusters
  (correction cycles; E0 trials grouped as described in real.py), all assignments enumerated when there are at
  most 1,000,000, else 200,000 random ones with a fixed seed; statistic = summed successes in treated clusters.
"""
import math

import numpy as np

Z975 = 1.959963984540054        # standard normal 0.975 quantile
Z95 = 1.6448536269514722        # 0.95 quantile


def norm_cdf(z):
    return 0.5 * math.erfc(-z / math.sqrt(2.0))


# ---------------------------------------------------------------- one proportion
def wilson(k, n, z=Z975):
    """Wilson score interval (no continuity correction)."""
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def binom_pmf(n, p):
    """P(X = 0..n) for X ~ Bin(n, p), as a float array."""
    if p <= 0:
        out = np.zeros(n + 1)
        out[0] = 1.0
        return out
    if p >= 1:
        out = np.zeros(n + 1)
        out[n] = 1.0
        return out
    ks = np.arange(n + 1)
    logc = np.array([math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1) for k in ks])
    return np.exp(logc + ks * math.log(p) + (n - ks) * math.log1p(-p))


def clopper_pearson(k, n, alpha=0.05):
    """Exact (Clopper-Pearson) interval by bisection on the binomial tails."""
    if n == 0:
        return (float("nan"), float("nan"))

    def solve(f):                 # f increasing in p, find f(p) = 0 on [0, 1]
        lo, hi = 0.0, 1.0
        for _ in range(200):
            mid = (lo + hi) / 2
            if f(mid) < 0:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2

    lower = 0.0 if k == 0 else solve(lambda p: binom_pmf(n, p)[k:].sum() - alpha / 2)       # P(X >= k) = a/2
    upper = 1.0 if k == n else solve(lambda p: alpha / 2 - binom_pmf(n, p)[:k + 1].sum())   # P(X <= k) = a/2
    return (lower, upper)


def newcombe_diff(k1, n1, k2, n2, z=Z975):
    """Newcombe's hybrid score interval for p1 - p2 (his method 10), from the two Wilson intervals."""
    p1, p2 = k1 / n1, k2 / n2
    l1, u1 = wilson(k1, n1, z)
    l2, u2 = wilson(k2, n2, z)
    d = p1 - p2
    return (d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2), d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2))


# ---------------------------------------------------------------- 2x2 tables
def hypergeom_pmf(N, n1, m):
    """Law of the first group's successes given the margins: (lowest value, probabilities), exact integer ratios."""
    lo, hi = max(0, m - (N - n1)), min(n1, m)
    den = math.comb(N, m)
    return lo, np.array([math.comb(n1, x) * math.comb(N - n1, m - x) / den for x in range(lo, hi + 1)])


def exact_cmh(strata, alternative="greater"):
    """Exact conditional CMH test. strata: [(a, n1, b, n2), ...], a of n1 successes in group 1, b of n2 in group 2.
    "greater": group 1 has the higher odds of success. Returns dict(p, t_obs, mh_or, dist_lo, dist)."""
    dist, off, t_obs, num, den = np.array([1.0]), 0, 0, 0.0, 0.0
    for a, n1, b, n2 in strata:
        N, m = n1 + n2, a + b
        if N == 0:
            continue
        lo, pmf = hypergeom_pmf(N, n1, m)
        dist, off, t_obs = np.convolve(dist, pmf), off + lo, t_obs + a
        num += a * (n2 - b) / N
        den += b * (n1 - a) / N
    i = t_obs - off
    if alternative == "greater":
        p = dist[i:].sum()
    elif alternative == "less":
        p = dist[:i + 1].sum()
    else:
        raise ValueError(alternative)
    mh_or = num / den if den > 0 else (float("inf") if num > 0 else float("nan"))
    return {"p": min(1.0, float(p)), "t_obs": int(t_obs), "mh_or": mh_or, "dist_lo": int(off), "dist": dist}


def fisher_exact(a, n1, b, n2, alternative="two-sided"):
    """Fisher's exact test for a of n1 vs b of n2. "greater": group 1 has the higher success odds."""
    if alternative in ("greater", "less"):
        return exact_cmh([(a, n1, b, n2)], alternative)["p"]
    lo, pmf = hypergeom_pmf(n1 + n2, n1, a + b)
    return min(1.0, float(pmf[pmf <= pmf[a - lo] * (1 + 1e-7)].sum()))


def _fisher_one_sided_grid(n1, n2, alternative):
    """Fisher one-sided p-value for every table (y1, y2), shape (n1+1, n2+1)."""
    P = np.empty((n1 + 1, n2 + 1))
    N = n1 + n2
    for s in range(N + 1):
        lo, pmf = hypergeom_pmf(N, n1, s)
        tail = np.cumsum(pmf[::-1])[::-1] if alternative == "greater" else np.cumsum(pmf)
        for j, y1 in enumerate(range(lo, lo + len(pmf))):
            P[y1, s - y1] = tail[j]
    return P


def boschloo_exact(a, n1, b, n2, alternative="greater"):
    """Boschloo's unconditional exact test (one-sided). Group 1 = a of n1."""
    P = _fisher_one_sided_grid(n1, n2, alternative)
    obs = P[a, b]
    R = P <= obs * (1 + 1e-13)
    N = n1 + n2
    W = [0] * (N + 1)                                       # exact integer weight of each total s in the region
    for y1 in range(n1 + 1):
        for y2 in range(n2 + 1):
            if R[y1, y2]:
                W[y1 + y2] += math.comb(n1, y1) * math.comb(n2, y2)
    s_idx = np.array([s for s in range(N + 1) if W[s] > 0])
    logW = np.array([math.log(W[s]) for s in s_idx])

    def f(pi):
        if pi <= 0:
            return float(W[0])
        if pi >= 1:
            return float(W[N])
        v = logW + s_idx * math.log(pi) + (N - s_idx) * math.log1p(-pi)
        mx = v.max()
        return float(math.exp(mx) * np.exp(v - mx).sum())

    grid = np.linspace(0.0, 1.0, 20001)
    vals = np.array([f(x) for x in grid])
    best = float(vals.max())
    gr = (math.sqrt(5) - 1) / 2
    for i in np.argsort(vals)[-5:]:                        # refine around the 5 best grid points
        lo, hi = grid[max(0, i - 1)], grid[min(len(grid) - 1, i + 1)]
        c, d = hi - gr * (hi - lo), lo + gr * (hi - lo)
        for _ in range(60):
            if f(c) > f(d):
                hi = d
            else:
                lo = c
            c, d = hi - gr * (hi - lo), lo + gr * (hi - lo)
        best = max(best, f((lo + hi) / 2))
    return min(1.0, best)


# ---------------------------------------------------------------- contrasts, ranks, pairs
def adjusted_wald(ys, ns, cs, alternative="greater"):
    """Price-Bonett adjusted Wald test of L = sum c_i p_i against 0. "greater": H1 L > 0; "less": H1 L < 0.
    Returns dict(L_hat (unadjusted), L_adj, se, z, p, ci95_one_sided)."""
    m = sum(1 for c in cs if c != 0)
    pt = [(y + 2 / m) / (n + 4 / m) for y, n in zip(ys, ns)]
    L_adj = sum(c * p for c, p in zip(cs, pt))
    se = math.sqrt(sum(c * c * p * (1 - p) / (n + 4 / m) for c, p, n in zip(cs, pt, ns)))
    z = L_adj / se
    p = 1 - norm_cdf(z) if alternative == "greater" else norm_cdf(z)
    ci = (L_adj - Z95 * se, float("inf")) if alternative == "greater" else (float("-inf"), L_adj + Z95 * se)
    return {"L_hat": sum(c * y / n for c, y, n in zip(cs, ys, ns)), "L_adj": L_adj, "se": se, "z": z, "p": p,
            "ci95_one_sided": ci}


def midranks(x):
    x = np.asarray(x, float)
    order = np.argsort(x, kind="mergesort")
    r = np.empty(len(x))
    xs = x[order]
    i = 0
    while i < len(x):
        j = i
        while j + 1 < len(x) and xs[j + 1] == xs[i]:
            j += 1
        r[order[i:j + 1]] = (i + j) / 2 + 1
        i = j + 1
    return r


def wilcoxon_signed_rank(d, alternative="greater"):
    """Exact Wilcoxon signed-rank test of the differences d (zeros dropped, average ranks for ties).
    "greater": H1 the differences tend to be positive. Returns dict(n, w_plus, p)."""
    d = np.asarray(d, float)
    d = d[d != 0]
    n = len(d)
    if n == 0:
        return {"n": 0, "w_plus": 0.0, "p": 1.0}
    r2 = np.round(2 * midranks(np.abs(d))).astype(int)    # doubled ranks are integers
    w2 = int(r2[d > 0].sum())
    dist = np.zeros(int(r2.sum()) + 1)
    dist[0] = 1.0
    for r in r2:
        new = dist * 0.5
        new[r:] += 0.5 * dist[:len(dist) - r]
        dist = new
    p = dist[w2:].sum() if alternative == "greater" else dist[:w2 + 1].sum()
    return {"n": n, "w_plus": w2 / 2, "p": min(1.0, float(p))}


def mcnemar_exact(b, c):
    """Exact two-sided McNemar test on the discordant counts b and c."""
    n = b + c
    if n == 0:
        return 1.0
    pmf = binom_pmf(n, 0.5)
    return min(1.0, 2 * float(pmf[:min(b, c) + 1].sum()))


def holm(pvals, alpha=0.05):
    """Holm step-down. Returns (reject list, adjusted p list) in the input order."""
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    adj, rej, run, stop = [0.0] * m, [False] * m, 0.0, False
    for k, i in enumerate(order):
        run = max(run, min(1.0, (m - k) * pvals[i]))
        adj[i] = run
        if not stop and pvals[i] <= alpha / (m - k):
            rej[i] = True
        else:
            stop = True
    return rej, adj


def cohen_kappa(x, y):
    """Cohen's kappa for two binary ratings of the same items."""
    x, y = np.asarray(x, bool), np.asarray(y, bool)
    n = len(x)
    if n == 0:
        return float("nan")
    po = float((x == y).mean())
    pe = float(x.mean() * y.mean() + (1 - x.mean()) * (1 - y.mean()))
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def cluster_permutation(strata, n_max=1_000_000, n_random=200_000, seed=20261103):
    """Cluster-level permutation test, one-sided (treated clusters have more successes).
    strata: [[(successes, trials, treated_bool), ...cluster...], ...stratum...].
    Labels are permuted within each stratum, keeping each stratum's number of treated clusters."""
    import itertools
    per = []
    t_obs = 0
    for clusters in strata:
        s = np.array([c[0] for c in clusters])
        k = sum(1 for c in clusters if c[2])
        t_obs += int(s[[i for i, c in enumerate(clusters) if c[2]]].sum())
        per.append((s, k))
    total = 1
    for s, k in per:
        total *= math.comb(len(s), k)
    if total <= n_max:
        dist = np.array([0])
        for s, k in per:
            sums = np.array([s[list(cmb)].sum() for cmb in itertools.combinations(range(len(s)), k)])
            dist = (dist[:, None] + sums[None, :]).ravel()
        return {"p": float((dist >= t_obs).mean()), "t_obs": t_obs, "n_assignments": int(total), "exact": True}
    rng = np.random.default_rng(seed)
    T = np.zeros(n_random, int)
    for s, k in per:
        idx = np.argsort(rng.random((n_random, len(s))), axis=1)[:, :k]
        T += s[idx].sum(axis=1)
    return {"p": float(((T >= t_obs).sum() + 1) / (n_random + 1)), "t_obs": t_obs, "n_assignments": int(total),
            "exact": False, "seed": seed}
