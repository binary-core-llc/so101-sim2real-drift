#!/usr/bin/env python3
"""E1 variant selection on the simulated selection set (v2 item 2b). Rule fixed before any selection result was read
(this file's commit precedes results/e1/selection_eval.json).

    .venv/bin/python -I e1/eval_selection.py [--runs results/e1/selection_runs] [--out results/e1/selection_eval.json]
Per scene, the error of an estimate against the truth (results/e1/selection_truth.json) over all 9 quantities, each
scaled by the planned mis-setup size: camera angles / 6 deg, camera translations / 30 mm, rack position / 30 mm,
rack yaw / 15 deg:
    e = |(d_tilt, d_pan, d_roll)| / 6 + |(d_lat, d_depth, d_height)| / 0.030 + |(d_x, d_y)| / 0.030 + |d_yaw| / 15
A parse failure or a missing estimate counts as "no correction" (all deltas 0). The nominal scene (no change) counts
like the others. Selection: the variant with the lower median e over the 25 scenes; a tie goes to v1 (metric).
Round 2 (committed before its runs): the candidates are v1, v2, v1b, v2b; the lowest median wins, a tie goes to the
earlier in that order. Round 1 (v1, v2) is kept and reported.
Also reported: the "no correction" baseline, failures, per-scene errors and the camera / rack split.
"""
import argparse
import json
import statistics as st
from pathlib import Path

import numpy as np

GTC = Path(__file__).resolve().parents[1]
CAM = ["tilt_down_deg", "pan_deg", "roll_deg", "lateral_m", "depth_m", "height_m"]
RACK = ["x_m", "y_m", "yaw_deg"]


def vec(d, keys):
    return np.array([float((d or {}).get(k, 0.0) or 0.0) for k in keys])


def err(est_cam, est_rack, tr):
    c = vec(est_cam, CAM) - vec(tr["camera_delta"], CAM)
    r = vec(est_rack, RACK) - vec(tr["rack_delta"], RACK)
    return float(np.linalg.norm(c[:3]) / 6 + np.linalg.norm(c[3:]) / 0.030 + np.linalg.norm(r[:2]) / 0.030 + abs(r[2]) / 15)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default=str(GTC / "results" / "e1" / "selection_runs"))
    ap.add_argument("--out", default=str(GTC / "results" / "e1" / "selection_eval.json"))
    ap.add_argument("--variants", nargs="+", default=["v1", "v2"])
    a = ap.parse_args(argv)
    truth = json.loads((GTC / "results" / "e1" / "selection_truth.json").read_text())["truth"]
    out = {"rule": "lowest median scaled error over the selection set; tie -> the earlier of " + ", ".join(a.variants),
           "variants": {}, "per_scene": {}}
    base = [err(None, None, t) for t in truth.values()]
    out["no_correction_median"] = round(st.median(base), 4)
    for v in a.variants:
        es, fails, cam_e, rack_e = [], 0, [], []
        for name, t in truth.items():
            p = Path(a.runs) / f"{name}_{v}.json"
            if not p.exists():
                raise SystemExit(f"STOP: missing run {p}")
            r = json.loads(p.read_text())
            ok = r["status"] == "ok"
            fails += not ok
            e = err(r["camera_delta"] if ok else None, r["rack_delta"] if ok else None, t)
            es.append(e)
            (cam_e if t["camera_delta"] else rack_e if t["rack_delta"] else []).append(e)
            out["per_scene"].setdefault(name, {})[v] = {"error": round(e, 4), "status": r["status"], "moved": r.get("moved"),
                                                        "seconds": r["seconds"]}
        out["variants"][v] = {"median": round(st.median(es), 4), "mean": round(float(np.mean(es)), 4), "failures": fails,
                              "median_camera_scenes": round(st.median(cam_e), 4), "median_rack_scenes": round(st.median(rack_e), 4)}
    out["chosen"] = min(a.variants, key=lambda v: (out["variants"][v]["median"], a.variants.index(v)))
    Path(a.out).write_text(json.dumps(out, indent=1))
    for v, s in out["variants"].items():
        print(f"{v}: median {s['median']} (camera scenes {s['median_camera_scenes']}, rack scenes {s['median_rack_scenes']}), "
              f"mean {s['mean']}, failures {s['failures']}/{len(truth)}")
    print(f"no correction: median {out['no_correction_median']}; chosen: {out['chosen']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
