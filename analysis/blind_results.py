#!/usr/bin/env python3
"""Unblind batches A and B and run the registered real-trial analysis on the blind scores (Nov 10).

    .venv/bin/python -I analysis/blind_results.py [--out results/analysis/real_blind_v1]
Checks each sealed key against its committed SHA-256, joins codes -> trial records, and calls the analysis code as
released with prereg v2 (release/prereg_v2/analysis/real.py and stats.py, unchanged) on the blind outcomes:
conditions with Wilson 95 % intervals (registered; Clopper-Pearson added), Cohen's kappa live vs blind and every
disagreement, decision checks. With R3 and R5 cut (K8) the released h1_h3() skips H1, so H1c and the first
falsification check are computed here with the same functions and arguments (stats.adjusted_wald on R2 + R4 against
R1, [1, -0.5], "less"; pooled outside >= half of nominal). R4 is analysed without N06-004 to N06-007 (primary, I4)
and with them. N04B-R0 is the R0 result; N04-R0 is reported apart and not pooled (entry 2). S1_measured_c920 is shown
next to R1 with the Newcombe interval of the difference (descriptive).
Writes <out>.json, <out>.md and <out>_rows.jsonl (one joined row per trial).
"""
import argparse
import csv
import hashlib
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

GTC = Path(__file__).resolve().parents[1]
REL = GTC / "release" / "prereg_v2" / "analysis"
STAMP = "20261110T064043Z"
CAM1_I4 = {"N06-004", "N06-005", "N06-006", "N06-007"}
ROLE = {"N04-G1": "gate", "N05-C": "control", "N06-C": "control", "N05-RACK": "interspersed", "N06-C2": "interspersed"}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent))
    spec.loader.exec_module(m)
    return m


def rel_t0(r, clip_log, t_clip):
    """Clip time of a phone clip -> seconds from the policy start (T0)."""
    import datetime as dt
    if clip_log is None or t_clip is None or not r.get("t0_first_query"):
        return None
    start = dt.datetime.fromisoformat(clip_log["start_utc"]) + dt.timedelta(seconds=clip_log["clip"]["video_from_s"])
    t0 = dt.datetime.fromisoformat(r["t0_first_query"])
    return round((start - t0).total_seconds() + t_clip, 2)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(GTC / "results" / "analysis" / "real_blind_v1"))
    a = ap.parse_args(argv)
    A = load("stats", REL / "stats.py")
    R = load("real", REL / "real.py")
    recs = {f"{r['uid']}_a{r['attempt']}": r for r in map(json.loads, open(GTC / "results/real/trials.jsonl"))}
    clips = {}
    for p in sorted((GTC / "results/real").glob("judge_clips_*.json")):
        L = json.loads(p.read_text())
        for c in L.get("clips", []):
            if "clip" in c and "start_utc" in L:
                clips[c["key"]] = {"start_utc": L["start_utc"], "clip": c, "log": p.name}
    robot = {c["key"] for c in json.loads((GTC / "results/real/judge_clips_robot_frames.json").read_text())["clips"]}
    rows, keycheck = [], {}
    for b in ("A", "B"):
        kp = GTC / f"media/real/judge/sealed/blind_key_{b}_{STAMP}.json"
        h = hashlib.sha256(kp.read_bytes()).hexdigest()
        committed = (GTC / f"results/real/blind_key_{b}_{STAMP}.sha256").read_text().split()[0]
        if h != committed:
            raise SystemExit(f"STOP: key {b} SHA-256 {h} differs from the committed {committed}")
        keycheck[b] = h
        key = json.loads(kp.read_text())["key"]
        sheet = list(csv.DictReader(open(GTC / f"results/real/blind_scores_{b}_{STAMP}.csv")))
        if {s["blind_code"] for s in sheet} != set(key):
            raise SystemExit(f"STOP: sheet {b} codes differ from key {b}")
        for i, s in enumerate(sheet, start=2):
            k = key[s["blind_code"]]
            r = recs[k]
            live = r.get("relabel", {}).get("from", {}) if "relabel" in r else r
            t_clip = float(s["t_release_s"]) if s["t_release_s"] else None
            rows.append({
                "key": k, "uid": r["uid"], "attempt": r["attempt"], "block": r["block"], "cond": r["cond"],
                "batch": b, "sheet_row": i, "blind_code": s["blind_code"],
                "clip_source": "robot frames" if k in robot else "phone",
                "blind": {f: s[f] for f in ("outcome", "t_release_s", "hold_2s", "hold_05s", "grasp", "fail_code",
                                            "tilt_borderline", "confidence", "tube_contact", "note")},
                "t_release_from_T0_s": None if k in robot else rel_t0(r, clips.get(k), t_clip),
                "live_outcome": live.get("live_outcome"), "live_fail_code": live.get("live_fail_code"),
                "invalid_code": r.get("invalid_code"), "flags": r.get("flags") or {}, "live_note": r.get("note")})
    rows.sort(key=lambda x: (recs[x["key"]].get("t_launch") or "", x["key"]))

    def analysis_rows(cam1_valid):
        out = []
        for x in rows:
            inv = x["invalid_code"]
            if cam1_valid and x["uid"] in CAM1_I4:
                inv = None
            out.append({"uid": x["key"], "condition": "R0_offset" if x["block"] == "N04-R0" else x["cond"],
                        "day": recs[x["key"]].get("actual_date"), "success": x["blind"]["outcome"] == "S",
                        "success_live": x["live_outcome"] == "S", "invalid": inv, "flags": [],
                        "role": ROLE.get(x["block"]) if x["cond"] == "R1" else None, "block": x["block"],
                        "hold_0p5s": x["blind"]["hold_05s"] == "1", "grasp": x["blind"]["grasp"] == "1",
                        "failure_class": x["blind"]["fail_code"] or None,
                        "time_to_success_s": x["t_release_from_T0_s"] if x["blind"]["outcome"] == "S" else None})
        return out

    res = {"key_sha256": keycheck, "code": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                            for p in (REL / "real.py", REL / "stats.py", Path(__file__))}}
    for name, cam1_valid in (("primary", False), ("with_N06-004_to_007", True)):
        tr_all = analysis_rows(cam1_valid)
        out = R.analyse(tr_all)
        tr = R.valid(tr_all)
        for c, row in out["conditions"].items():
            row["clopper_pearson95"] = list(A.clopper_pearson(row["k"], row["n"]))
        kN, nN = R.kn(tr, {"R1"})
        ko, no = R.kn(tr, {"R2", "R4"})
        h1c = A.adjusted_wald([ko, kN], [no, nN], [1, -0.5], "less")
        out["H1c"] = dict(h1c, test="adjusted Wald one-sided, p_outside - 0.5 p_nominal < 0 (R2 + R4 against R1)",
                          outside=[ko, no], nominal=[kN, nN], reject=h1c["p"] <= R.ALPHA)
        out["H1_falsification_check_1"] = {"pooled_outside": ko / no, "half_nominal": 0.5 * kN / nN,
                                           "falsified": (ko / no) >= 0.5 * (kN / nN)}
        k0, n0 = R.kn(R.valid(tr_all), {"R0_offset"})
        out["R0_offset_N04-R0"] = {"k": k0, "n": n0, "wilson95": list(A.wilson(k0, n0)),
                                   "clopper_pearson95": list(A.clopper_pearson(k0, n0))}
        res[name] = out
    s1 = json.loads((GTC / "results/h4/s1_result.json").read_text())["S1_measured_c920"]
    p = res["primary"]["conditions"]["R1"]
    res["R1_vs_S1_measured_c920"] = {"real": [p["k"], p["n"]], "sim": [s1["k"], s1["n"]],
                                     "diff_real_minus_sim": p["k"] / p["n"] - s1["k"] / s1["n"],
                                     "newcombe95": list(A.newcombe_diff(p["k"], p["n"], s1["k"], s1["n"])),
                                     "ratio_real_to_sim": (p["k"] / p["n"]) / (s1["k"] / s1["n"])}
    val = [x for x in rows if not x["invalid_code"]]
    res["disagreements_live_vs_blind"] = [
        {"key": x["key"], "cond": x["cond"], "live": x["live_outcome"], "blind": x["blind"]["outcome"],
         "blind_confidence": x["blind"]["confidence"], "invalid_code": x["invalid_code"]}
        for x in rows if (x["live_outcome"] == "S") != (x["blind"]["outcome"] == "S")]
    res["kappa_all_61_incl_invalid"] = A.cohen_kappa([x["live_outcome"] == "S" for x in rows],
                                                     [x["blind"]["outcome"] == "S" for x in rows])
    fc = {}
    for x in val:
        c = x["cond"] if x["block"] != "N04-R0" else "R0_offset"
        d = fc.setdefault(c, {"live": Counter(), "blind": Counter()})
        d["live"]["S" if x["live_outcome"] == "S" else x["live_fail_code"]] += 1
        d["blind"]["S" if x["blind"]["outcome"] == "S" else x["blind"]["fail_code"]] += 1
    res["failure_codes_live_vs_blind"] = {c: {k: dict(sorted(v.items())) for k, v in d.items()} for c, d in fc.items()}
    res["tube_contact_blind"] = {}
    for x in val:
        c = x["cond"] if x["block"] != "N04-R0" else "R0_offset"
        res["tube_contact_blind"].setdefault(c, {}).setdefault(x["blind"]["tube_contact"], 0)
        res["tube_contact_blind"][c][x["blind"]["tube_contact"]] += 1
    res["S_release_from_T0_s"] = {x["key"]: x["t_release_from_T0_s"] for x in rows if x["blind"]["outcome"] == "S"}
    res["clip_8726af"] = next(({k: v for k, v in x.items() if k != "blind"} | {"blind": x["blind"]}
                               for x in rows if x["blind_code"] == "8726af"), None)
    res["n_rows"] = len(rows)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out + ".json").write_text(json.dumps(res, indent=1, default=str) + "\n")
    with open(a.out + "_rows.jsonl", "w") as f:
        for x in rows:
            f.write(json.dumps(x, default=str) + "\n")
    print(json.dumps({"rows": len(rows), "keys_ok": True}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
