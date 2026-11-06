#!/usr/bin/env python3
"""Real-trial analysis (PREREGISTRATION_v1.md §5 decision rules as checks, §6 analysis), numpy + stdlib only.

    .venv/bin/python -I analysis/real.py --trials results/real/trials.jsonl \
        [--photos results/real/photo_scores.jsonl --e1-variant NAME] [--h4 results/analysis/h4_inputs.json] \
        [--out results/analysis/real_v1.json]

Input schema (minimal; the trial runner's format is not final, so its rows are mapped onto this):
  trials.jsonl, one trial per line:
    uid (str), condition ("R0".."R9"), day ("YYYY-MM-DD"),
    success (bool, primary endpoint, from blind scoring), success_live (bool, optional),
    invalid (null or "I1".."I6"; invalid trials are excluded and counted),
    flags (list of str, optional: "drift_suspect" = since the last passing camera check, which showed
           0.5-1.0 deg or 3-5 mm, excluded only in the sensitivity analysis; "prefix_block" = D1 pre-fix gate
           block, excluded from R1),
    role (R1 only, optional: "gate" | "control" | "interspersed"),
    cycle (int; required for R6-R9: the correction cycle), block (optional, R2/R4: the E0 cluster id used by the
           cycle-level permutation test; when absent, R2/R4 trials are grouped in consecutive fours by uid order),
    secondary, optional: release_chunk28 (bool), hold_0p5s (bool), grasp (bool), time_to_success_s (float),
           failure_class (str).
  photo_scores.jsonl (H3b), one photo per line:
    photo_id, kind ("camera" | "rack"), set ("TEST" | "DEV"; DEV is excluded),
    truth_delta {dof: actual - nominal} (camera: x, y, z in m, roll, pitch, yaw in rad; rack: x, y in m, yaw rad),
    estimates {method: {dof: correction} | null}: the correction each method applies (perfect = -truth_delta).
  h4_inputs.json (H4 and the real nominal placement rule):
    {"sim_intrinsics": [k, n], "c920_measured": [k, n], "c920_image_matched": [k, n] (optional),
     "fx_measured_px": float}

Choices for v2 to fix (besides those in stats.py):
- H1a strata: rack = R3 (inside) vs R2 (outside); camera = R5 (inside) vs R4 (outside). H3a strata: M1 = R6 vs R2;
  M2 = R7 vs R4. p_nominal = all valid R1 trials (gate block, controls, interspersed), minus a D1 pre-fix block.
- H1b/H1c: pooled inside = R3 + R5, pooled outside = R2 + R4, each against 0.5 x p_nominal by the adjusted Wald
  test (stats.adjusted_wald, m = 2). H1 falsified also when the one-sided test of p_inside - 0.5 p_nominal < 0
  rejects at 0.05 (same test, other side).
- H3b score: residual_i = truth_delta_i + correction_i on each of the photo's degrees of freedom; a missing method
  output (null) or a missing degree of freedom counts as no correction (0); score = sqrt(mean((residual_i / h_i)^2))
  with the training half-ranges h (camera x, y 0.02 m, z 0.01 m, roll, pitch, yaw 0.05 rad; rack x 0.04 m,
  y 0.01 m, yaw 0.5 rad). Test: Wilcoxon signed-rank on d = score(E1 variant) - score(E3), one-sided d > 0.
  "Inside the box" (descriptive) = every degree of freedom's |residual| <= its half-range.
- The exploratory sim-real agreement (correlation, MMRV) needs the simulated predictions at the measured offsets
  and is not computed here.
"""
import argparse
import collections
import hashlib
import json
import math
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stats as A  # noqa: E402

HALF = {"camera": {"x": 0.02, "y": 0.02, "z": 0.01, "roll": 0.05, "pitch": 0.05, "yaw": 0.05},
        "rack": {"x": 0.04, "y": 0.01, "yaw": 0.5}}
FX_SIM = 514.7
ALPHA = 0.05


def load_jsonl(path):
    return [json.loads(l) for l in open(path) if l.strip()]


def valid(trials, sensitivity=False):
    out = []
    for t in trials:
        if t.get("invalid"):
            continue
        fl = set(t.get("flags") or [])
        if t["condition"] == "R1" and "prefix_block" in fl:
            continue
        if sensitivity and "drift_suspect" in fl:
            continue
        out.append(t)
    return out


def kn(trials, conds):
    ts = [t for t in trials if t["condition"] in conds]
    return sum(bool(t["success"]) for t in ts), len(ts)


def conditions_table(tr):
    k1, n1 = kn(tr, {"R1"})
    pnom = k1 / n1 if n1 else float("nan")
    rows = {}
    for c in [f"R{i}" for i in range(10)]:
        k, n = kn(tr, {c})
        if n == 0:
            continue
        lo, hi = A.wilson(k, n)
        rows[c] = {"k": k, "n": n, "rate": k / n, "wilson95": [lo, hi],
                   "ratio_to_nominal": (k / n) / pnom if pnom and pnom == pnom else None}
    return rows


def h1_h3(tr):
    s = {c: kn(tr, {c}) for c in ["R1", "R2", "R3", "R4", "R5", "R6", "R7"]}
    res = {}
    if all(s[c][1] for c in ("R2", "R3", "R4", "R5")):
        strata = [(s["R3"][0], s["R3"][1], s["R2"][0], s["R2"][1]), (s["R5"][0], s["R5"][1], s["R4"][0], s["R4"][1])]
        cmh = A.exact_cmh(strata, "greater")
        ki, ni = s["R3"][0] + s["R5"][0], s["R3"][1] + s["R5"][1]
        ko, no = s["R2"][0] + s["R4"][0], s["R2"][1] + s["R4"][1]
        res["H1a"] = {"test": "exact CMH one-sided, inside (R3, R5) > outside (R2, R4), strata rack / camera",
                      "strata": {"rack": strata[0], "camera": strata[1]}, "p": cmh["p"], "mh_or": cmh["mh_or"],
                      "sensitivity": {"pooled_fisher_one_sided": A.fisher_exact(ki, ni, ko, no, "greater"),
                                      "pooled_boschloo_one_sided": A.boschloo_exact(ki, ni, ko, no, "greater")},
                      "inside": [ki, ni], "outside": [ko, no]}
        if s["R1"][1]:
            kN, nN = s["R1"]
            res["H1b"] = dict(A.adjusted_wald([ki, kN], [ni, nN], [1, -0.5], "greater"),
                              test="adjusted Wald one-sided, p_inside - 0.5 p_nominal > 0")
            res["H1c"] = dict(A.adjusted_wald([ko, kN], [no, nN], [1, -0.5], "less"),
                              test="adjusted Wald one-sided, p_outside - 0.5 p_nominal < 0")
            res["H1_falsify_inside_test"] = A.adjusted_wald([ki, kN], [ni, nN], [1, -0.5], "less")
            res["nominal"] = [kN, nN]
    if all(s[c][1] for c in ("R2", "R4", "R6", "R7")):
        strata = [(s["R6"][0], s["R6"][1], s["R2"][0], s["R2"][1]), (s["R7"][0], s["R7"][1], s["R4"][0], s["R4"][1])]
        cmh = A.exact_cmh(strata, "greater")
        res["H3a"] = {"test": "exact CMH one-sided, E3 (R6, R7) > E0 (R2, R4), strata M1 / M2",
                      "strata": {"M1": strata[0], "M2": strata[1]}, "p": cmh["p"], "mh_or": cmh["mh_or"],
                      "sensitivity": {"cycle_permutation": cycle_permutation(tr)}}
    fam = [h for h in ("H1a", "H3a") if h in res]
    if fam:
        rej, adj = A.holm([res[h]["p"] for h in fam], ALPHA)
        for h, r, a in zip(fam, rej, adj):
            res[h]["holm_reject"], res[h]["holm_adjusted_p"] = r, a
    if "H1a" in res and "H1c" in res:
        kN, nN = res["nominal"]
        ko, no = res["H1a"]["outside"]
        supported = bool(res["H1a"].get("holm_reject")) and res["H1c"]["p"] <= ALPHA
        falsified = (ko / no) >= 0.5 * (kN / nN) or res["H1_falsify_inside_test"]["p"] <= ALPHA
        res["H1_verdict"] = "supported" if supported and not falsified else (
            "falsified" if falsified else "not supported (inconclusive)")
    return res


def cycle_permutation(tr):
    """Clusters: R6/R7 by cycle; R2/R4 by block, else consecutive fours in uid order. Strata M1 (R6 vs R2) and
    M2 (R7 vs R4)."""
    strata = []
    for treat, ctrl in (("R6", "R2"), ("R7", "R4")):
        clusters = []
        g = collections.defaultdict(list)
        for t in tr:
            if t["condition"] == treat:
                g[("T", t["cycle"])].append(t)
        ctl = sorted([t for t in tr if t["condition"] == ctrl], key=lambda t: t["uid"])
        if all("block" in t for t in ctl):
            for t in ctl:
                g[("C", t["block"])].append(t)
        else:
            for i, t in enumerate(ctl):
                g[("C", i // 4)].append(t)
        for (lab, _), ts in sorted(g.items(), key=lambda kv: (kv[0][0], str(kv[0][1]))):
            clusters.append((sum(bool(t["success"]) for t in ts), len(ts), lab == "T"))
        strata.append(clusters)
    return A.cluster_permutation(strata)


def photo_score(kind, truth, corr):
    h = HALF[kind]
    corr = corr or {}
    res = {d: truth.get(d, 0.0) + (corr.get(d) if isinstance(corr.get(d), (int, float)) else 0.0) for d in h}
    score = math.sqrt(sum((res[d] / h[d]) ** 2 for d in h) / len(h))
    inside = all(abs(res[d]) <= h[d] for d in h)
    return score, inside


def h3b(photos, e1):
    ph = [p for p in photos if p.get("set", "TEST") != "DEV"]
    rows, s3, s1, s0, in3, in1, in0 = [], [], [], [], [], [], []
    for p in ph:
        est = p.get("estimates") or {}
        a, ia = photo_score(p["kind"], p["truth_delta"], est.get("E3"))
        b, ib = photo_score(p["kind"], p["truth_delta"], est.get(e1))
        z, iz = photo_score(p["kind"], p["truth_delta"], None)
        rows.append({"photo_id": p["photo_id"], "E3": a, e1: b, "predict_zero": z})
        s3.append(a), s1.append(b), s0.append(z), in3.append(ia), in1.append(ib), in0.append(iz)
    w = A.wilcoxon_signed_rank([b - a for a, b in zip(s3, s1)], "greater")
    bb = sum(1 for x, y in zip(in3, in1) if x and not y)
    cc = sum(1 for x, y in zip(in3, in1) if y and not x)
    med = (lambda v: statistics.median(v) if v else None)
    return {"n_photos": len(ph), "e1_variant": e1, "wilcoxon": w,
            "test": "Wilcoxon signed-rank one-sided on score(E1) - score(E3) > 0",
            "median_score": {"E3": med(s3), e1: med(s1), "predict_zero": med(s0)},
            "inside_box_share": {"E3": sum(in3) / len(ph) if ph else None, e1: sum(in1) / len(ph) if ph else None,
                                 "predict_zero": sum(in0) / len(ph) if ph else None},
            "mcnemar_inside_E3_vs_E1": {"E3_only": bb, "E1_only": cc, "p_two_sided": A.mcnemar_exact(bb, cc)},
            "per_photo": rows}


def h4(inp):
    ks, ns = inp["sim_intrinsics"]
    km, nm = inp["c920_measured"]
    out = {"test": "Fisher two-sided, sim intrinsics vs measured C920 intrinsics at the simulated pose",
           "sim_intrinsics": [ks, ns], "c920_measured": [km, nm], "p": A.fisher_exact(ks, ns, km, nm, "two-sided")}
    fx = inp.get("fx_measured_px")
    if fx is not None:
        gap = abs(fx - FX_SIM) / FX_SIM
        out["fx_gap"] = gap
        rule = "pose-matched"
        if gap > 0.05 and inp.get("c920_image_matched"):
            ki, ni = inp["c920_image_matched"]
            wi, wm = A.wilson(ki, ni), A.wilson(km, nm)
            if ki / ni > km / nm and wi[0] > wm[1]:
                rule = "image-matched"
            out["image_vs_pose_matched_wilson"] = {"image_matched": [ki, ni, *wi], "pose_matched_c920": [km, nm, *wm]}
        elif gap > 0.05:
            rule = "undecided: fx gap > 5 %, the image-matched cell is needed"
        out["real_nominal_placement"] = rule
    return out


def secondary(tr):
    out = {}
    for c in sorted({t["condition"] for t in tr}):
        ts = [t for t in tr if t["condition"] == c]
        row = {}
        for f in ("release_chunk28", "hold_0p5s", "grasp"):
            v = [bool(t[f]) for t in ts if f in t]
            if v:
                row[f] = [sum(v), len(v)]
        tt = [t["time_to_success_s"] for t in ts if t.get("success") and t.get("time_to_success_s") is not None]
        if tt:
            row["median_time_to_success_s"] = statistics.median(tt)
        fc = collections.Counter(t["failure_class"] for t in ts if not t.get("success") and t.get("failure_class"))
        if fc:
            row["failure_classes"] = dict(fc)
        out[c] = row
    return out


def decision_checks(all_trials, tr):
    """§5 decision rules as checks on the data (the operator applies them live)."""
    out = {}
    gate = [t for t in tr if t["condition"] == "R1" and t.get("role") == "gate"]
    if gate:
        k = sum(bool(t["success"]) for t in gate)
        out["D1_gate"] = {"k": k, "n": len(gate), "low_nominal": k <= 3}
    days = collections.defaultdict(list)
    for t in tr:
        if t["condition"] == "R1" and t.get("role") == "control":
            days[t["day"]].append(bool(t["success"]))
    if days:
        out["D2_daily_controls"] = {d: {"k": sum(v), "n": len(v), "stop": len(v) >= 5 and sum(v) <= 1}
                                    for d, v in sorted(days.items())}
    k1, n1 = kn(tr, {"R1"})
    for c in ("R2", "R4"):
        k, n = kn(tr, {c})
        if n and n1:
            out[f"D3_no_effect_{c}"] = {"k": k, "n": n,
                                        "no_effect": k >= 7 and (k / n) >= 0.8 * (k1 / n1) and n >= 12}
    inv = collections.Counter(t["invalid"] for t in all_trials if t.get("invalid"))
    out["invalid"] = dict(inv)
    out["reserve_used"] = sum(inv.values())
    return out


def analyse(trials, photos=None, e1=None, h4_inp=None):
    tr, tr_s = valid(trials), valid(trials, sensitivity=True)
    res = {"n_rows": len(trials), "n_valid": len(tr),
           "conditions": conditions_table(tr), "tests": h1_h3(tr),
           "sensitivity_drift_suspect_excluded": {"conditions": conditions_table(tr_s), "tests": h1_h3(tr_s)},
           "secondary": secondary(tr), "decision_checks": decision_checks(trials, tr)}
    both = [t for t in tr if "success_live" in t]
    if both:
        res["kappa_live_vs_blind"] = {"n": len(both), "kappa": A.cohen_kappa([t["success_live"] for t in both],
                                                                           [t["success"] for t in both])}
    if photos is not None:
        res["H3b"] = h3b(photos, e1)
    if h4_inp is not None:
        res["H4"] = h4(h4_inp)
    return res


def report(res):
    L = [f"Trials: {res['n_rows']} rows, {res['n_valid']} valid. Invalid by code: "
         f"{res['decision_checks']['invalid'] or 'none'}"]
    for c, r in res["conditions"].items():
        rat = "" if r["ratio_to_nominal"] is None else f", {r['ratio_to_nominal']:.2f} x nominal"
        L.append(f"  {c}: {r['k']}/{r['n']} = {r['rate']:.2f} (Wilson 95 % {r['wilson95'][0]:.2f}-"
                 f"{r['wilson95'][1]:.2f}){rat}")
    t = res["tests"]
    for h in ("H1a", "H3a"):
        if h in t:
            sens = ", ".join(f"{k} {v['p'] if isinstance(v, dict) else v:.4g}" for k, v in t[h]["sensitivity"].items())
            L.append(f"  {h}: p = {t[h]['p']:.4g} (Holm-adjusted {t[h]['holm_adjusted_p']:.4g}, "
                     f"{'reject' if t[h]['holm_reject'] else 'no reject'}); MH OR {t[h]['mh_or']:.3g}; {sens}")
    for h in ("H1b", "H1c"):
        if h in t:
            L.append(f"  {h}: {t[h]['test']}: z = {t[h]['z']:.3f}, p = {t[h]['p']:.4g}")
    if "H1_verdict" in t:
        L.append(f"  H1: {t['H1_verdict']}")
    if "kappa_live_vs_blind" in res:
        L.append(f"  Cohen's kappa live vs blind: {res['kappa_live_vs_blind']['kappa']:.3f} "
                 f"(n {res['kappa_live_vs_blind']['n']})")
    if "H3b" in res:
        h = res["H3b"]
        L.append(f"  H3b: {h['n_photos']} photos, E3 vs {h['e1_variant']}: Wilcoxon p = {h['wilcoxon']['p']:.4g} "
                 f"(n {h['wilcoxon']['n']} non-zero); medians {h['median_score']}")
    if "H4" in res:
        h = res["H4"]
        L.append(f"  H4: Fisher two-sided p = {h['p']:.4g}; placement: {h.get('real_nominal_placement', 'fx not given')}")
    return "\n".join(L)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", required=True)
    ap.add_argument("--photos")
    ap.add_argument("--e1-variant")
    ap.add_argument("--h4")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    if a.photos and not a.e1_variant:
        raise SystemExit("STOP: --photos needs --e1-variant (the variant fixed in v2)")
    res = analyse(load_jsonl(a.trials), load_jsonl(a.photos) if a.photos else None, a.e1_variant,
                  json.loads(Path(a.h4).read_text()) if a.h4 else None)
    res["code_sha256"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in (Path(__file__), Path(__file__).with_name("stats.py"))}
    print(report(res))
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(json.dumps(res, indent=1, default=lambda o: o.tolist()) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
