#!/usr/bin/env python3
"""Write the two H4 sweep cells (PREREGISTRATION_v1 §4 "After October 26"; D_software C8a) from the C920 intrinsics.

    .venv/bin/python -I sim/make_h4_cells.py --intrinsics config/c920_intrinsics.json \\
        [--pose results/h4/image_matched_pose.json] [--out results/h4/cells_h4.csv]

The rows use the exact format of config/cells_sweep_v1.csv. Checkpoint, task and seeds are copied from its
S0_nominal row: 200 episodes = seeds 0-39 × 5 repeats.
  - H4_c920_measured: only the external focal changes, focal_mm = fx * hAp / 640 (hAp 2.4 mm), at the D455 pose.
  - H4_c920_image_matched: the same focal plus the camera_mount offsets from sim/image_matched_pose.py. That
    file must have been computed from the same intrinsics file (checked by sha256).
The sim camera is a square-pixel pinhole centred on the image. The measured fy/fx, cx, cy and distortion are not
represented (stated in each row's notes).

v1 §6, real nominal camera placement: pose-matched, unless the measured fx differs from 514.7 px by more than
5 % AND the image-matched arm has higher simulated success than the pose-matched C920 arm, with
non-overlapping 95 % CIs. If the gap is <= 5 %, the image-matched cell is not needed for that decision.
H4's Fisher test (sim intrinsics vs measured C920 intrinsics, both at the simulated pose) needs H4_c920_measured.
Both cells are listed in v1 §4, so both rows are written; --measured-only writes the first row alone.
"""
import argparse
import csv
import hashlib
import io
import json
import sys
from pathlib import Path

GTC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))   # sibling modules (python -I skips the script dir)

import overrides  # noqa: E402

SWEEP = GTC / "config" / "cells_sweep_v1.csv"
HAP_MM = 2.4
FX_SIM = 514.6666259765625            # results/c1/frames_sim.json tiled_camera intrinsic_matrices (v1: 514.7)
GAP_RULE_PCT = 5.0
COLS = ["cell_id", "priority", "lane", "checkpoint", "task", "overrides_json", "n_episodes", "seed_base", "seed_mod",
        "as_shipped", "notes"]
LIMIT = "fy/fx, cx, cy and distortion not represented (sim pinhole, square pixels, centred)"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def s0_row():
    with open(SWEEP) as f:
        rows = list(csv.DictReader(f))
    assert list(rows[0].keys()) == COLS, f"unexpected columns in {SWEEP}"
    return next(r for r in rows if r["cell_id"] == "S0_nominal")


def build(intrinsics, pose=None, measured_only=False):
    intr = json.loads(Path(intrinsics).read_text())
    K = intr["K"]
    fx, fy = float(K[0][0]), float(K[1][1])
    gap = 100 * (fx / FX_SIM - 1)
    focal = round(fx * HAP_MM / 640, 6)
    s0 = s0_row()
    base = {k: s0[k] for k in ("lane", "checkpoint", "task", "n_episodes", "seed_base", "seed_mod", "as_shipped")}
    h_int = sha(intrinsics)[:12]
    rows, info = [], {"fx": fx, "fy": fy, "fx_gap_pct": gap, "camera_focal_mm": focal, "intrinsics_sha256": sha(intrinsics),
                      "intrinsics_status": intr.get("status")}
    ov1 = {"camera_focal_mm": focal}
    overrides.resolve(ov1)
    rows.append({**base, "cell_id": "H4_c920_measured", "priority": "4", "overrides_json": json.dumps(ov1),
                 "notes": f"C920 fx {fx:.2f} px (gap {gap:+.2f} % vs {FX_SIM:.2f}): external focal {focal:.6f} mm (hAp 2.4 mm) "
                          f"at the D455 pose; intrinsics sha256 {h_int}; {LIMIT}"})
    if not measured_only:
        if not pose or not Path(pose).exists():
            raise SystemExit(f"STOP: {pose} not found: run sim/image_matched_pose.py match --intrinsics {intrinsics} first "
                             "(or --measured-only)")
        pj = json.loads(Path(pose).read_text())
        if pj["intrinsics"]["sha256"] != info["intrinsics_sha256"]:
            raise SystemExit(f"STOP: {pose} was computed from a different intrinsics file "
                             f"({pj['intrinsics']['sha256'][:12]} != {h_int}); re-run image_matched_pose.py match")
        if not pj.get("lens_inside_box", True):
            raise SystemExit(f"STOP: the image-matched lens is outside the box ({pose}); not a valid level")
        cam = {k: float(pj["camera_offsets"][k]) for k in ("x", "y", "z", "roll", "pitch", "yaw")}
        ov2 = {"camera": cam, "camera_focal_mm": focal}
        overrides.resolve(ov2)
        L, iou = pj["lens"], pj["iou_full_res"]
        rows.append({**base, "cell_id": "H4_c920_image_matched", "priority": "4", "overrides_json": json.dumps(ov2),
                     "notes": f"C920 focal {focal:.6f} mm at the image-matched pose (sim/image_matched_pose.py, class-mask "
                              f"mean IoU vs the D455 view {iou['pose_matched']:.3f} -> {iou['image_matched']:.3f}): lens moved "
                              f"{[round(v, 1) for v in L['lens_shift_env_mm']]} mm in env, tilt {L['delta_tilt_down_deg']:+.2f} deg, "
                              f"heading {L['delta_heading_deg']:+.2f} deg; pose file sha256 {sha(pose)[:12]}; {LIMIT}"})
        info["pose_sha256"] = sha(pose)
    for r in rows:
        assert r["n_episodes"] == "200" and r["seed_base"] == "0" and r["seed_mod"] == "40", r
    return rows, info


def to_csv(rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLS, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow({k: r[k] for k in COLS})
    return buf.getvalue()


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--intrinsics", required=True)
    ap.add_argument("--pose", default=str(GTC / "results" / "h4" / "image_matched_pose.json"))
    ap.add_argument("--out", default=str(GTC / "results" / "h4" / "cells_h4.csv"))
    ap.add_argument("--measured-only", action="store_true")
    a = ap.parse_args(argv)
    if not Path(a.intrinsics).exists():
        raise SystemExit(f"STOP: {a.intrinsics} not found (C3 intrinsics first)")
    rows, info = build(a.intrinsics, a.pose, a.measured_only)
    gap = info["fx_gap_pct"]
    print(f"fx {info['fx']:.2f} px (fy {info['fy']:.2f}), gap {gap:+.2f} % vs {FX_SIM:.2f}; intrinsics status "
          f"{info['intrinsics_status']}; sim focal {info['camera_focal_mm']:.6f} mm")
    if abs(gap) <= GAP_RULE_PCT:
        print(f"v1 §6: |gap| <= {GAP_RULE_PCT:.0f} %, so the real nominal placement is pose-matched; the image-matched cell "
              "is not needed for that decision (H4's Fisher test still needs H4_c920_measured)")
    else:
        print(f"v1 §6: |gap| > {GAP_RULE_PCT:.0f} %: the placement is image-matched only if the image-matched arm has higher "
              "simulated success than H4_c920_measured with non-overlapping 95 % CIs; both cells are needed")
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    text = to_csv(rows)
    Path(a.out).write_text(text)
    print(f"wrote {a.out} ({len(rows)} rows, sha256 {hashlib.sha256(text.encode()).hexdigest()})")
    for r in rows:
        print(f"  {r['cell_id']}: {r['overrides_json']}")


if __name__ == "__main__":
    main(sys.argv[1:])
