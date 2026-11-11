#!/usr/bin/env python3
"""Validate the tube check's "shift" method (real/vial_check.py score_shift) against the registered "iou" method on
saved pre-trial frames, without writing any record.

    .venv/bin/python -I tools/vial_check_validate.py [--pose r0] [--blocks N04B-R0 N04-R0] [--out DIR]
Positives: N04B-R0 (mat re-placed from the lobes; the overlays show the tubes on their targets). Negatives: N04-R0
(mat about 18-19 mm toward the camera wall), every N04B-R0 frame checked against the next layout (wrong layout), and
synthetic edits of the N04B-R0 frames: one tube removed (its pixels replaced by the tube-free reference) and one tube
moved by 3, 6, 10 and 15 mm across its axis on the mat (the move in the image is the projected move). For the moves the
check's measured across-axis change is compared with the applied move. Pass/fail is then tallied for limits of 5 / 5,
7.5 / 7.5 (proposed) and 10 / 10 mm across / along (covered share >= 0.85, cap as registered). Writes <out>/vial_check_validation.json (overlays: media/real/vial_check_validation/).
"""
import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

GTC = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(GTC / "calib"), str(GTC / "real")]

import capture  # noqa: E402
import vial_check as V  # noqa: E402

LAYOUT_ORDER = ["L00", "L01", "L02", "L03", "L04", "L05", "L06", "L07", "L08", "L09"]


def local(p):
    return GTC / str(p).replace("/workspace/gtc/", "")


def summary(res):
    return {k: {"pass": v["pass"], "shift_px": v.get("shift_px"), "shift_E_mm": v.get("shift_E_mm"), "across_mm": v.get("across_mm"),
                "along_mm": v.get("along_mm"), "cover": v.get("cover"), "cap": v.get("cap_frac"), "iou": v["iou"]}
            for k, v in res["vials"].items()}


def passes(vials, across_lim, along_lim, cover_min=0.85, cap_min=0.5):
    for v in vials.values():
        if v["across_mm"] is None or abs(v["across_mm"]) > across_lim or abs(v["along_mm"]) > along_lim:
            return False
        if v["cover"] < cover_min or (v["cap"] is not None and v["cap"] < cap_min):
            return False
    return True


def move_tube(cur, ref, region, dx, dy):
    """The tube's pixels (region) moved by (dx, dy) onto the tube-free reference."""
    out = cur.copy()
    out[region] = ref[region]
    M = np.float32([[1, 0, dx], [0, 1, dy]])
    h, w = region.shape
    moved = cv2.warpAffine(cur, M, (w, h), flags=cv2.INTER_LINEAR)
    mreg = cv2.warpAffine(region.astype(np.uint8), M, (w, h), flags=cv2.INTER_NEAREST).astype(bool)
    out[mreg] = moved[mreg]
    return out


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--pose", default="r0")
    ap.add_argument("--blocks", nargs="+", default=["N04B-R0", "N04-R0"])
    ap.add_argument("--out", default=str(GTC / "results" / "real" / "vial_check_validation"))
    a = ap.parse_args(argv)
    cam = V.load_camera(GTC / "results" / "poses" / f"{a.pose}.json", GTC / "config" / "c920_intrinsics.json")
    R_E_cv, C_E, K, dist = cam
    model = V.vial_model()
    th_s, th_i = {**V.TH, "method": "shift"}, {**V.TH, "method": "iou"}
    recs = [json.loads(l) for l in open(GTC / "results" / "real" / "trials.jsonl")]
    out = {"pose": a.pose, "thresholds_shift": th_s, "cases": []}
    tally = {}

    def add(kind, expect, uid, res_s, res_i, extra=None):
        out["cases"].append({"kind": kind, "expect_pass": expect, "uid": uid, "shift_pass": res_s["pass"], "iou_pass": res_i["pass"],
                             "vials": summary(res_s), **(extra or {})})
        t = tally.setdefault(kind, {"n": 0, "pass_iou_registered": 0, "pass_5_5": 0, "pass_7.5_7.5": 0, "pass_10_10": 0})
        t["n"] += 1
        t["pass_iou_registered"] += int(res_i["pass"])
        v = summary(res_s)
        t["pass_5_5"] += int(passes(v, 5.0, 5.0))
        t["pass_7.5_7.5"] += int(passes(v, 7.5, 7.5))
        t["pass_10_10"] += int(passes(v, 10.0, 10.0))

    for blk in a.blocks:
        good = blk == "N04B-R0"
        for r in [r for r in recs if r["block"] == blk and r.get("pre_front")]:
            cur = capture.load_rgb(local(r["pre_front"]))
            rd = GTC / "media" / "real" / "refs" / r["ref_tag"]
            ref = capture.load_rgb(rd / "ref_front_median.png")
            sd = np.load(rd / "ref_front_sd.npy").astype(np.float32)
            L = V.find_layout(r["layout"])
            rs, vis = V.check(cur, ref, sd, L, cam, model, th_s)
            ri, _ = V.check(cur, ref, sd, L, cam, model, th_i)
            tag = f"{r['uid']}_a{r['attempt']}"
            capture.save_rgb(GTC / "media" / "real" / "vial_check_validation" / f"{tag}_shift.png", vis)
            add(f"{blk} as placed", good, tag, rs, ri)
            if not good:
                continue
            Lw = V.find_layout(LAYOUT_ORDER[(LAYOUT_ORDER.index(r["layout"]) + 1) % 10])
            add("wrong layout", False, tag, V.check(cur, ref, sd, Lw, cam, model, th_s)[0], V.check(cur, ref, sd, Lw, cam, model, th_i)[0])
            # synthetic edits, on the undistorted frame then distorted back is not needed: edit in the captured frame
            # around the tube's projected silhouette (dilated), which the check undistorts like any frame
            prof, src, mat_top, _ = model
            tg = V.targets(L, prof, src, mat_top, R_E_cv, C_E, K, cur.shape[:2])
            mx, my = cv2.initUndistortRectifyMap(K, dist, None, K, cur.shape[1::-1], cv2.CV_32FC1)
            name = sorted(tg)[1]
            reg_u = cv2.dilate(tg[name]["mask"].astype(np.uint8), np.ones((15, 15), np.uint8))
            # undistorted-space region -> captured-space region (inverse map by forward-mapping the pixel grid)
            reg = np.zeros(cur.shape[:2], np.uint8)
            ys, xs = np.nonzero(reg_u)
            reg[np.clip(np.round(my[ys, xs]).astype(int), 0, cur.shape[0] - 1), np.clip(np.round(mx[ys, xs]).astype(int), 0, cur.shape[1] - 1)] = 1
            reg = cv2.morphologyEx(reg, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)).astype(bool)
            gone = cur.copy()
            gone[reg] = ref[reg]
            add("one tube removed", False, tag, V.check(gone, ref, sd, L, cam, model, th_s)[0], V.check(gone, ref, sd, L, cam, model, th_i)[0],
                {"edited": name})
            Rv, pv = V.vial_poses(L, prof, src, mat_top)[name]
            ax = Rv[:2, 2] / np.linalg.norm(Rv[:2, 2])
            mid = pv + Rv[:, 2] * 0.04
            base_across = rs["vials"][name].get("across_mm")
            for s in (3, 6, 10, 15):
                P = np.array([mid, mid + np.array([-ax[1], ax[0], 0.0]) * s / 1000])
                uv = V.project(P, R_E_cv, C_E, K)
                mv = move_tube(cur, ref, reg, *(uv[1] - uv[0]))
                rs_m = V.check(mv, ref, sd, L, cam, model, th_s)[0]
                seen = rs_m["vials"][name].get("across_mm")
                add(f"one tube moved {s} mm", None, tag, rs_m, V.check(mv, ref, sd, L, cam, model, th_i)[0],
                    {"edited": name, "applied_mm": s, "measured_change_mm": None if seen is None or base_across is None
                     else round(seen - base_across, 1)})
    out["tally"] = tally
    Path(a.out).mkdir(parents=True, exist_ok=True)
    (Path(a.out) / "vial_check_validation.json").write_text(json.dumps(out, indent=1, default=str))
    print(f"{'case':24s}  n   pass: IoU>=0.7 (registered) | 5/5 mm | 7.5/7.5 mm (proposed) | 10/10 mm")
    for k, t in tally.items():
        print(f"{k:24s} {t['n']:2d}         {t['pass_iou_registered']:2d}            |  {t['pass_5_5']:2d}    |     {t['pass_7.5_7.5']:2d}               |   {t['pass_10_10']:2d}")
    ch = [(c["applied_mm"], c["measured_change_mm"]) for c in out["cases"] if c.get("applied_mm") is not None and c["measured_change_mm"] is not None]
    for s in sorted({x for x, _ in ch}):
        m = np.array([y for x, y in ch if x == s])
        print(f"move {s:2d} mm across: measured change {m.mean():+.1f} mm (SD {m.std():.1f}, n {len(m)})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
