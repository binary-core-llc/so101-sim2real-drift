#!/usr/bin/env python3
"""C920x lens calibration from two independent ChArUco capture sets, with B section 3.4 acceptance.

    .venv/bin/python -I calib/intrinsics_solve.py --square-mm 29.97 --sets A B [--missing-corner bottom-left]
        [--print-x-mm 179.9 179.8 --print-y-mm 119.9 120.0]     # the B 3.1 ruler readings, recorded
    .venv/bin/python -I calib/intrinsics_solve.py --camera wrist --square-mm 29.97 --sets W
        # wrist camera (E_premortem G10/V19): one set of 10-15 views; HFOV against the sim's wrist DR band
        # (focal 12-15 mm on horizontalAperture 20.955 mm = 69.8-82.3 deg); writes config/wrist_intrinsics.json
Reads media/calib/intrinsics/<set>/view_*.png and results/calib/intrinsics_<set>_capture.json.
Writes config/c920_intrinsics.json (K, dist, RMS, per-view errors, sigmas, coverage, the camera's exact model
and USB ID from the capture sets, lock readback, board with the measured square, sha256 of the images).

Pipeline (B 3.3): detect -> matchImagePoints -> calibrateCameraExtended; reject views with per-view RMS
> 2.5 x median and refit; keep k3 only if it lowers RMS by > 0.02 px. Acceptance (B 3.4):
  views kept >= 30 and coverage met (per set: 9 cells; every image corner >= 3 views within 40 px. If a set
  reaches the corners only within 80 px, that is accepted as a logged deviation from B 3.2 and k3 is fixed
  (CALIB_FIX_K3) in every fit (decided Oct 25). --missing-corner NAME (added Nov 7) leaves one
  unreachable image corner out of that rule, logs it with the best distance reached, and fixes k3) |
  RMS <= 0.30 px (0.30-0.50 WARN, > 0.50 FAIL) |
  no per-view RMS > 2.5 x median | sigma(fx), sigma(fy) <= 0.2 % | sigma(cx), sigma(cy) <= 1.0 px |
  hold-out: fit on 2/3, PnP-only RMS on 1/3 <= 0.40 px | two sets: fx within 0.5 %, cx and cy within 3 px |
  fy/fx within 1 %. Exit 0 = every check PASS (WARN allowed), 1 = a FAIL.
"""
import argparse
import datetime as dt
import hashlib
import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))  # sibling modules (python -I skips the script dir)

import capture
from charuco import Detector, SPEC
from intrinsics_capture import CORNER_NAMES, CORNER_VIEWS, MIN_CORNERS, coverage, view_stats

GTC = Path(__file__).resolve().parents[1]
SIZE = (640, 480)
CRIT = (cv2.TERM_CRITERIA_COUNT + cv2.TERM_CRITERIA_EPS, 200, 1e-9)
HAP_MM = 2.4                        # sim horizontalAperture (lightbox-simple.usd override)


def load_set(name, det, set_dir=None):
    d = Path(set_dir) if set_dir else GTC / "media" / "calib" / "intrinsics" / name
    files = sorted(d.glob("view_*.png"))
    if not files:
        raise SystemExit(f"STOP: no views in {d}")
    views, h = [], hashlib.sha256()
    for f in files:
        h.update(f.read_bytes())
        r = det.detect(capture.load_rgb(f))
        if r is not None and len(r["ids"]) >= MIN_CORNERS:
            views.append({"file": f"{name}/{f.name}", **r})
    meta_p = GTC / "results" / "calib" / f"intrinsics_{name}_capture.json"
    meta = json.loads(meta_p.read_text()) if meta_p.exists() else {}
    return {"name": name, "dir": str(d), "n_files": len(files), "views": views, "sha256": h.hexdigest(), "meta": meta}


def calibrate(views, fix_k3):
    objs = [v["obj"].astype(np.float32) for v in views]
    imgs = [v["img"].astype(np.float32) for v in views]
    flags = cv2.CALIB_FIX_K3 if fix_k3 else 0
    rms, K, dist, rv, tv, sdI, sdE, per = cv2.calibrateCameraExtended(objs, imgs, SIZE, None, None, flags=flags, criteria=CRIT)
    return {"rms": float(rms), "K": K, "dist": dist.ravel(), "sdI": sdI.ravel(), "per_view": per.ravel(), "fix_k3": fix_k3}


def fit(views, force_k3_fixed=False):
    """B 3.3: full model, reject > 2.5 x median per-view RMS, refit; compare with k3 fixed (or force it)."""
    kept = list(views)
    for _ in range(5):
        r = calibrate(kept, fix_k3=False)
        med = float(np.median(r["per_view"]))
        bad = [i for i, e in enumerate(r["per_view"]) if e > 2.5 * med]
        if not bad:
            break
        kept = [v for i, v in enumerate(kept) if i not in bad]
    kept_files = {v["file"] for v in kept}
    rejected = [v["file"] for v in views if v["file"] not in kept_files]
    full, k3fixed = calibrate(kept, False), calibrate(kept, True)
    best = k3fixed if force_k3_fixed else (full if full["rms"] < k3fixed["rms"] - 0.02 else k3fixed)
    return best, kept, rejected, {"rms_full": full["rms"], "rms_k3_fixed": k3fixed["rms"]}


def holdout_rms(views, seed=0, force_k3_fixed=False):
    rng = np.random.default_rng(seed)
    idx = rng.permutation(len(views))
    n_fit = int(round(len(views) * 2 / 3))
    train, test = [views[i] for i in idx[:n_fit]], [views[i] for i in idx[n_fit:]]
    r, _, _, _ = fit(train, force_k3_fixed)
    err = []
    for v in test:
        ok, rv, tv = cv2.solvePnP(v["obj"], v["img"], r["K"], r["dist"], flags=cv2.SOLVEPNP_IPPE)
        rv, tv = cv2.solvePnPRefineLM(v["obj"], v["img"], r["K"], r["dist"], rv, tv)
        p, _ = cv2.projectPoints(v["obj"], rv, tv, r["K"], r["dist"])
        err.append(np.sum((p.reshape(-1, 2) - v["img"]) ** 2, axis=1))
    e = np.concatenate(err)
    return float(np.sqrt(e.mean())), len(train), len(test)


def summary(r):
    K, sd = r["K"], r["sdI"]
    fx, fy, cx, cy = K[0, 0], K[1, 1], K[0, 2], K[1, 2]
    return {"fx": fx, "fy": fy, "cx": cx, "cy": cy, "sd_fx_pct": 100 * sd[0] / fx, "sd_fy_pct": 100 * sd[1] / fy,
            "sd_cx_px": sd[2], "sd_cy_px": sd[3], "rms_px": r["rms"]}


def grade(val, ok, warn=None):
    return "PASS" if ok(val) else ("WARN" if warn and warn(val) else "FAIL")


def wrist(a, sets):
    """G10: descriptive wrist calibration; the policy-relevant number is the HFOV against the sim DR band."""
    f = json.loads((GTC / "results" / "c1" / "frames_sim.json").read_text())
    hap = f["camera_ego"]["usd"]["horizontalAperture"]
    lo_f, hi_f = f["dr_setting"]["original_ranges"]["wrist_focal_range"]
    band = (math.degrees(2 * math.atan(hap / (2 * hi_f))), math.degrees(2 * math.atan(hap / (2 * lo_f))))
    allv = [v for s in sets for v in s["views"]]
    if len(allv) < 6:
        raise SystemExit(f"STOP: only {len(allv)} usable wrist views (need >= 10)")
    r, kept, rej, alt = fit(allv)
    S = summary(r)
    hfov = math.degrees(2 * math.atan(320 / S["fx"]))
    inside = band[0] <= hfov <= band[1]
    checks = [("views kept >= 10", len(kept), "PASS" if len(kept) >= 10 else "FAIL"),
              ("RMS <= 0.50 px", round(S["rms_px"], 3), "PASS" if S["rms_px"] <= 0.5 else "WARN"),
              (f"HFOV inside the sim wrist DR band {band[0]:.1f}-{band[1]:.1f} deg", round(hfov, 2),
               "PASS" if inside else "OUTSIDE: log as a known sim-real gap before Nov 4 (G10)")]
    out = {"utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "camera_role": "wrist",
           "camera": sets[0]["meta"].get("camera"), "K": r["K"].tolist(), "dist": r["dist"].tolist(), "rms_px": S["rms_px"],
           "sigmas": {k: S[k] for k in ("sd_fx_pct", "sd_fy_pct", "sd_cx_px", "sd_cy_px")}, "n_views_used": len(kept),
           "rejected": rej, "hfov_deg": hfov, "vfov_deg": math.degrees(2 * math.atan(240 / S["fy"])),
           "sim_wrist_fx_nominal": 640 * f["camera_ego"]["usd"]["focalLength"] / hap, "sim_dr_hfov_band_deg": band,
           "sha256": [s["sha256"] for s in sets], "checks": [{"check": c, "value": v, "result": g} for c, v, g in checks]}
    Path(a.out).write_text(json.dumps(out, indent=1, default=float))
    for c, v, g in checks:
        print(f"  {g:4s}  {c:52s} {v}")
    print(f"wrist fx {S['fx']:.1f} (sim nominal {out['sim_wrist_fx_nominal']:.1f}), HFOV {hfov:.1f} deg -> {a.out}")
    return 0


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--square-mm", type=float, required=True, help="measured printed square (B 3.1), mm")
    ap.add_argument("--sets", nargs="+", default=["A", "B"])
    ap.add_argument("--set-dirs", nargs="*", default=None, help="test only: explicit image directories")
    ap.add_argument("--print-x-mm", type=float, nargs="*", default=[])
    ap.add_argument("--print-y-mm", type=float, nargs="*", default=[])
    ap.add_argument("--out", default=None)
    ap.add_argument("--camera", default="front", choices=["front", "wrist"])
    ap.add_argument("--missing-corner", choices=CORNER_NAMES, default=None,
                    help="an image corner that cannot be reached in the box (Nov 7: bottom-left, by the back wall); "
                         "left out of the corner rule and logged as a deviation from B 3.2, with k3 fixed")
    a = ap.parse_args(argv)
    a.out = a.out or str(GTC / "config" / ("c920_intrinsics.json" if a.camera == "front" else "wrist_intrinsics.json"))
    det = Detector(a.square_mm, min_corners=MIN_CORNERS)
    dirs = a.set_dirs or [None] * len(a.sets)
    sets = [load_set(n, det, d) for n, d in zip(a.sets, dirs)]
    if a.camera == "wrist":
        return wrist(a, sets)
    checks, per_set, deviations = [], {}, []
    covs, best_missing = {}, {}
    miss = CORNER_NAMES.index(a.missing_corner) if a.missing_corner else None
    for s in sets:                                   # coverage first: the 80 px band fixes k3 in every fit
        r0, kept0, _, _ = fit(s["views"])
        stats0 = [view_stats(v, r0["K"]) for v in kept0]
        covs[s["name"]] = coverage(stats0)
        if miss is not None:
            best_missing[s["name"]] = min(st["corner_dist_px"][miss] for st in stats0)
            for k in ("corners_ok", "corners_ok_80px"):   # the accepted missing corner is left out of the corner rule
                zones = covs[s["name"]]["corner_zones" if k == "corners_ok" else "corner_zones_80px"]
                covs[s["name"]][k] = all(z >= CORNER_VIEWS for i, z in enumerate(zones) if i != miss)
    k3_fixed_by_rule = any(c["cells_ok"] and not c["corners_ok"] and c["corners_ok_80px"] for c in covs.values()) or miss is not None
    for s in sets:
        r, kept, rej, alt = fit(s["views"], k3_fixed_by_rule)
        cov = covs[s["name"]]
        per_set[s["name"]] = {"n_files": s["n_files"], "n_detected": len(s["views"]), "n_kept": len(kept),
                              "rejected": rej, **summary(r), **alt, "coverage": cov, "sha256": s["sha256"]}
        checks.append((f"set {s['name']}: views kept >= 30", len(kept), grade(len(kept), lambda v: v >= 30)))
        checks.append((f"set {s['name']}: coverage (9 cells; 4 corners x3 within 40 px, WARN 80 px"
                       + (f"; {a.missing_corner} accepted missing)" if miss is not None else ")"),
                       f"cells {cov['cells_ok']}, 40px {cov['corner_zones']}, 80px {cov['corner_zones_80px']}",
                       "PASS" if cov["cells_ok"] and cov["corners_ok"] and miss is None else
                       "DEVIATION" if cov["cells_ok"] and cov["corners_ok_80px"] else "FAIL"))
        if cov["cells_ok"] and not cov["corners_ok"] and cov["corners_ok_80px"]:
            deviations.append(f"set {s['name']}: image corners reached only within 80 px (B 3.2 asks 40 px; "
                              f"40 px counts {cov['corner_zones']}, 80 px counts {cov['corner_zones_80px']}); k3 fixed")
        if miss is not None:
            deviations.append(f"set {s['name']}: image corner {a.missing_corner} within 80 px in "
                              f"{cov['corner_zones_80px'][miss]} kept views, not {CORNER_VIEWS} (nearest dot "
                              f"{best_missing[s['name']]:.1f} px); accepted as missing with the other "
                              f"three corners x{CORNER_VIEWS} within 80 px (--missing-corner, Nov 7; "
                              "results/real/deviations.md); distortion toward it is extrapolated; k3 fixed")
    if len(sets) >= 2:
        a0, b0 = per_set[sets[0]["name"]], per_set[sets[1]["name"]]
        dfx = 100 * abs(a0["fx"] - b0["fx"]) / ((a0["fx"] + b0["fx"]) / 2)
        checks.append(("two sets: fx within 0.5 %", round(dfx, 3), grade(dfx, lambda v: v <= 0.5)))
        dc = max(abs(a0["cx"] - b0["cx"]), abs(a0["cy"] - b0["cy"]))
        checks.append(("two sets: cx, cy within 3 px", round(dc, 2), grade(dc, lambda v: v <= 3.0)))
    else:
        checks.append(("two sets", "only one set given", "FAIL"))
    allv = [v for s in sets for v in s["views"]]
    r, kept, rej, alt = fit(allv, k3_fixed_by_rule)
    S = summary(r)
    med = float(np.median(r["per_view"]))
    ho, n_tr, n_te = holdout_rms(kept, force_k3_fixed=k3_fixed_by_rule)
    checks += [("overall RMS <= 0.30 px", round(S["rms_px"], 3), grade(S["rms_px"], lambda v: v <= 0.30, lambda v: v <= 0.50)),
               ("per-view RMS <= 2.5 x median", round(float(r["per_view"].max() / med), 2),
                grade(float(r["per_view"].max() / med), lambda v: v <= 2.5)),
               ("sigma(fx), sigma(fy) <= 0.2 %", round(max(S["sd_fx_pct"], S["sd_fy_pct"]), 4),
                grade(max(S["sd_fx_pct"], S["sd_fy_pct"]), lambda v: v <= 0.2)),
               ("sigma(cx), sigma(cy) <= 1.0 px", round(max(S["sd_cx_px"], S["sd_cy_px"]), 3),
                grade(max(S["sd_cx_px"], S["sd_cy_px"]), lambda v: v <= 1.0)),
               (f"hold-out PnP RMS <= 0.40 px ({n_te} views)", round(ho, 3), grade(ho, lambda v: v <= 0.40)),
               ("fy/fx within 1 %", round(100 * abs(S["fy"] / S["fx"] - 1), 3), grade(100 * abs(S["fy"] / S["fx"] - 1), lambda v: v <= 1.0))]
    fx, fy = S["fx"], S["fy"]
    derived = {"hfov_deg": math.degrees(2 * math.atan(320 / fx)), "vfov_deg": math.degrees(2 * math.atan(240 / fy)),
               "dfov_deg": math.degrees(2 * math.atan(400 / math.sqrt(fx * fy))),
               "sim_focal_mm_at_hAp_2.4": fx * HAP_MM / 640, "fx_vs_sim_514.67_pct": 100 * (fx / 514.6666 - 1),
               "undistort_Kp": [[fx, 0, 320], [0, fx, 240], [0, 0, 1]]}
    metas = [s["meta"] for s in sets]
    cams = {json.dumps(m.get("camera", {}), sort_keys=True) for m in metas}
    if len(cams) > 1:
        checks.append(("same camera in every set", "identities differ", "FAIL"))
    status = "FAIL" if any(c[2] == "FAIL" for c in checks) else ("WARN" if any(c[2] == "WARN" for c in checks) else "PASS")
    if status != "FAIL" and deviations:
        status += " with deviation from B 3.2"
    out = {"utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "status": status,
           "camera": metas[0].get("camera") if metas else None, "settings": metas[0].get("settings") if metas else None,
           "lock_readback_ok": [m.get("lock_readback_ok") for m in metas],
           "image_size": list(SIZE), "K": r["K"].tolist(), "dist": r["dist"].tolist(), "dist_model": "k1 k2 p1 p2 k3",
           "k3_fixed": r["fix_k3"], "k3_fixed_by_corner_rule": k3_fixed_by_rule, "deviations_from_B": deviations,
           "rms_px": S["rms_px"], "sigmas": {k: S[k] for k in ("sd_fx_pct", "sd_fy_pct", "sd_cx_px", "sd_cy_px")},
           "n_views_used": len(kept), "rejected": rej, "per_view_rms": dict(zip([v["file"] for v in kept], r["per_view"].round(4).tolist())),
           "holdout_rms_px": ho, "per_set": per_set, "derived": derived,
           "board": {**SPEC, "square_mm_measured": a.square_mm, "marker_mm_scaled": SPEC["marker_m"] / SPEC["square_m"] * a.square_mm,
                     "print_x_mm": a.print_x_mm, "print_y_mm": a.print_y_mm},
           "opencv": cv2.__version__, "checks": [{"check": c, "value": v, "result": g} for c, v, g in checks]}
    Path(a.out).write_text(json.dumps(out, indent=1, default=float))
    for c, v, g in checks:
        print(f"  {g:4s}  {c:44s} {v}")
    print(f"fx {fx:.2f} fy {fy:.2f} cx {S['cx']:.2f} cy {S['cy']:.2f}  HFOV {derived['hfov_deg']:.2f} deg  "
          f"(sim D455 slot: fx 514.67, {derived['fx_vs_sim_514.67_pct']:+.2f} %)")
    for d in deviations:
        print(f"  DEVIATION from B 3.2 (logged in the JSON): {d}")
    print(f"INTRINSICS {status} -> {a.out}")
    return 1 if status == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
