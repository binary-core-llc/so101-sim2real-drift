#!/usr/bin/env python3
"""V05: vial layouts L00-L09 from sim seeds (randomization off), filtered as in E_premortem row 16.

    .venv/bin/python -I sim/layouts.py results/sim/v05_t07_a.jsonl [results/c1/frames_sim.json]

Input: a probe run of the nominal cell (every randomization at its centre; vial poses drawn per seed
by the course's own reset), poses read after the course's 10 warm-up steps.
Checks per seed (E row 16):
  - B 5.4 clearance: every pair of vial surfaces >= 3 mm apart (axis segments tip-17 mm .. cap+99.5 mm,
    radius 17 mm, as in B's generator);
  - C Appendix A on-mat: both ends inside the mat front-back (u), and at least one radius inside the
    right and left edges (v), as C's table/B's code apply it;
  - C rack-clear: no vial capsule overlaps the rack footprint at nominal, x+3 and y+3 (E row 16); x-3 is
    reported too.
The first 10 seeds that pass become L00-L09. Writes config/layouts.json.
Mat frame (C 1.2): u from the mat's front edge (toward the back wall), v from the mat's right edge
(toward the camera wall), in mm.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
TIP, CAP, R, CLEAR = 0.017, 0.0995, 0.017, 0.003       # B 5.4 generator constants
RACK_O, RACK_SIZE = (0.18, 0.08), 0.12                  # vials_to_rack_env_cfg.py:103; rack USD bbox 0..0.12
RACK_CASES = {"nominal": (0.0, 0.0), "x+3": (0.03, 0.0), "y+3": (0.0, 0.03), "x-3": (-0.03, 0.0)}
REQUIRED_RACK = ("nominal", "x+3", "y+3")
VIALS = ("vial_1", "vial_2", "vial_3")


def axis_of(q):
    w, x, y, z = q   # vial local +z (tip -> cap) in world
    return np.array([2 * (x * z + w * y), 2 * (y * z - w * x), 1 - 2 * (x * x + y * y)])


def seg_seg_dist(a0, a1, b0, b1, n=200):
    t = np.linspace(0, 1, n)[:, None]
    A = a0 + t * (a1 - a0)
    B = b0 + t * (b1 - b0)
    return float(np.min(np.linalg.norm(A[:, None, :] - B[None, :, :], axis=2)))


def seg_rect_dist(a0, a1, lo, hi, n=200):
    t = np.linspace(0, 1, n)[:, None]
    P = a0 + t * (a1 - a0)
    d = np.maximum(np.maximum(lo - P, P - hi), 0.0)
    return float(np.min(np.linalg.norm(d, axis=1)))


def main(jsonl, frames):
    f = json.loads(Path(frames).read_text())
    mat = f["mat"]["world_usd"]
    mx, my = mat["pos"][0], mat["pos"][1]
    assert abs(mat["rpy_deg_xyz"][2] - 90) < 1e-3, "mat expected at yaw 90 deg (DR off)"
    depth, width = 0.3048, 0.4572                      # mat.usda bbox 457.2 x 304.8 mm, rotated 90 deg
    front, back, right, left = mx - depth / 2, mx + depth / 2, my - width / 2, my + width / 2

    rows = sorted((json.loads(l) for l in open(jsonl)), key=lambda r: r["seed"])
    layouts, skipped, all_seeds = [], [], []
    for r in rows:
        if r.get("mode") != "probe":
            continue
        objs, objs0 = r["objects_after_warmup10"], r["objects_after_reset"]
        vials, segs = {}, {}
        for v in VIALS:
            p = np.array(objs[v]["pos"])
            a = axis_of(objs[v]["quat_wxyz"])
            a2 = a[:2] / np.linalg.norm(a[:2])
            tip, cap = p[:2] - TIP * a2, p[:2] + CAP * a2
            segs[v] = (tip, cap)
            mid = (tip + cap) / 2
            uv = lambda q: [round((q[0] - front) * 1000, 1), round((q[1] - right) * 1000, 1)]
            vials[v] = {"pos_env": [round(c, 5) for c in objs[v]["pos"]], "quat_wxyz": [round(c, 6) for c in objs[v]["quat_wxyz"]],
                        "heading_deg": round(math.degrees(math.atan2(a2[1], a2[0])), 2),
                        "axis_tilt_deg": round(math.degrees(math.asin(max(-1, min(1, a[2])))), 2),
                        "tip_uv_mm": uv(tip), "mid_uv_mm": uv(mid), "cap_uv_mm": uv(cap),
                        "settle_from_reset_mm": round(float(np.linalg.norm(np.array(objs[v]["pos"]) - np.array(objs0[v]["pos"]))) * 1000, 2)}
        gaps = [seg_seg_dist(*segs[a], *segs[b]) - 2 * R for i, a in enumerate(VIALS) for b in VIALS[i + 1:]]
        clearance_ok = min(gaps) >= CLEAR
        on_mat = all(front <= min(t[0], c[0]) and max(t[0], c[0]) <= back and
                     right + R <= min(t[1], c[1]) and max(t[1], c[1]) <= left - R for t, c in segs.values())
        rack = {}
        for case, (dx, dy) in RACK_CASES.items():
            lo = np.array([RACK_O[0] + dx, RACK_O[1] + dy])
            hi = lo + RACK_SIZE
            rack[case] = round(min(seg_rect_dist(t, c, lo, hi) - R for t, c in segs.values()) * 1000, 1)
        rack_ok = all(rack[c] > 0 for c in REQUIRED_RACK)
        rec = {"seed": r["seed"], "min_gap_mm": round(min(gaps) * 1000, 1), "clearance_ok": clearance_ok, "on_mat": on_mat,
               "rack_clearance_mm": rack, "rack_clear_ok": rack_ok, "vials": vials}
        all_seeds.append({k: rec[k] for k in ("seed", "min_gap_mm", "clearance_ok", "on_mat", "rack_clearance_mm", "rack_clear_ok")})
        if clearance_ok and on_mat and rack_ok:
            if len(layouts) < 10:
                rec["layout_id"] = f"L{len(layouts):02d}"
                layouts.append(rec)
        else:
            skipped.append({"seed": r["seed"], "reasons": [n for n, ok in (("clearance<3mm", clearance_ok), ("off_mat", on_mat),
                                                                            ("rack_overlap", rack_ok)) if not ok],
                            "min_gap_mm": rec["min_gap_mm"], "rack_clearance_mm": rack})
    out = {"schema": "gtc layouts v0", "source": str(jsonl), "frames": str(frames),
           "poses": "after the course's 10 warm-up steps (lerobot_eval.py:183), every randomization at its centre, "
                    "vial poses drawn per seed by the course reset (seed convention v0: RNGs seeded right before env.reset)",
           "mat_env": {"front_x": front, "back_x": back, "right_y": right, "left_y": left, "depth_m": depth, "width_m": width},
           "frame_uv": "u = mm from the mat's front edge (toward the back wall); v = mm from the mat's right edge (toward the camera wall)",
           "filter": {"clearance_mm": CLEAR * 1000, "vial_model": {"tip_m": TIP, "cap_m": CAP, "radius_m": R},
                      "rack_cases_required": REQUIRED_RACK, "rack_footprint_m": RACK_SIZE, "source": "E_premortem row 16; B 5.4; C App. A"},
           "layouts": layouts, "skipped": skipped, "all_seeds": all_seeds}
    (ROOT / "config" / "layouts.json").write_text(json.dumps(out, indent=1))
    print(f"{len(all_seeds)} seeds checked, {len(skipped)} skipped, {len(layouts)} layouts kept")
    for s in skipped:
        print(f"  skip seed {s['seed']}: {', '.join(s['reasons'])} (min gap {s['min_gap_mm']} mm, rack {s['rack_clearance_mm']})")
    for L in layouts:
        h = [L['vials'][v]['heading_deg'] for v in VIALS]
        st = max(L['vials'][v]['settle_from_reset_mm'] for v in VIALS)
        print(f"  {L['layout_id']} = seed {L['seed']:2d}: min gap {L['min_gap_mm']:5.1f} mm, headings {h}, "
              f"rack clearance {L['rack_clearance_mm']}, max settle {st} mm")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else str(ROOT / "results/c1/frames_sim.json"))
