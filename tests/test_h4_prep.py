#!/usr/bin/env python3
"""H4 prep tests: sim/image_matched_pose.py and sim/make_h4_cells.py (CPU only; no GPU, no devices, no docker).

    .venv/bin/python -I tests/test_h4_prep.py            # about 4 min (two image-matched searches)
    .venv/bin/python -I tests/test_h4_prep.py --quick    # about 15 s (skips the searches)

1. The camera rig: offsets -> lens pose reproduces the C1 dump and every T06 probe readback (the real sim), and
   the inverse round-trips.
2. The renderer: class masks at the nominal pose vs the C1 instance masks (Isaac's own render).
3. The renderer is not degenerate: a 0.1 deg turn changes pixels.
4. make_h4_cells.py: the cells_sweep_v1 format, the focal formula (checked against the S6 70.4 deg row), the seed
   columns copied from S0, the sha256 guard, the 5 % rule message.
5. (slow) Image-matched search with the sim's own K, started off-nominal, returns to the nominal pose.
6. (slow) With fx 460 px: offsets found, IoU gain, lens inside the box.
"""
import csv
import io
import json
import math
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np

GTC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GTC / "sim"))

import image_matched_pose as imp  # noqa: E402
import make_h4_cells as mk  # noqa: E402

FAILS = []


def check(name, ok, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'} {name} {detail}")
    if not ok:
        FAILS.append(name)


def write_intr(d, name, fx, fy=None):
    p = Path(d) / f"{name}.json"
    p.write_text(json.dumps({"status": "SYNTHETIC (test)", "image_size": [640, 480],
                             "K": [[fx, 0, 320], [0, fy or fx, 240], [0, 0, 1]], "dist": [0, 0, 0, 0, 0]}))
    return p


def main(quick):
    frames = json.loads(imp.FRAMES.read_text())
    rig = imp.Rig(frames)
    print("1. rig")
    check("render prim from the mount chain = dumped pose", rig.rig_check["pos_err_m"] < 1e-9 and rig.rig_check["rot_err_deg"] < 1e-4,
          f"{rig.rig_check['pos_err_m'] * 1000:.2e} mm, {rig.rig_check['rot_err_deg']:.2e} deg")
    t06 = imp.t06_check(rig)
    rot_sets = [e for e in t06 if any(k in (e["set"] or "") for k in ("roll", "pitch", "yaw"))]
    check("T06 readback: every probe record", len(t06) >= 20 and len(rot_sets) >= 6
          and max(e["pos_err_mm"] for e in t06) < 1e-3 and max(e["rot_err_deg"] for e in t06) < 1e-4,
          f"{len(t06)} records ({len(rot_sets)} with rotations): max {max(e['pos_err_mm'] for e in t06):.2e} mm, "
          f"{max(e['rot_err_deg'] for e in t06):.2e} deg")
    check("offsets round trip", max(e["inverse_err"] for e in t06) < 1e-9, f"{max(e['inverse_err'] for e in t06):.1e}")

    print("2. renderer vs the C1 instance masks")
    scene = imp.Scene(frames)
    R0, C0 = rig.lens(np.zeros(6))
    img = imp.render(scene, R0, C0, rig.K_sim[0, 0])
    ref = imp.c1_class_mask()
    m, per = imp.mean_iou(img, ref)
    diff = int((img != ref).sum())
    check("per-class IoU >= 0.999 and <= 0.1 % pixels differ", min(per.values()) >= 0.999 and diff <= 307,
          f"mean {m:.4f}, min {min(per.values()):.4f}, {diff} pixels differ")

    print("3. sensitivity")
    R, C = imp.lens_move(R0, C0, [0, 0, 0, 0.1, 0, 0])
    d1 = int((imp.render(scene, R, C, rig.K_sim[0, 0]) != ref).sum())
    check("0.1 deg tilt changes > 1000 pixels", d1 > 1000, f"{d1}")

    print("4. make_h4_cells")
    with tempfile.TemporaryDirectory() as d:
        fx70 = 320 / math.tan(math.radians(70.4 / 2))
        kp = write_intr(d, "k70", fx70)
        rows, info = mk.build(kp, measured_only=True)
        s6 = next(r for r in csv.DictReader(open(mk.SWEEP)) if r["cell_id"] == "S6_ext_hfov_70p4")
        check("focal formula = the S6 70.4 deg row", abs(info["camera_focal_mm"] - json.loads(s6["overrides_json"])["camera_focal_mm"]) < 1e-6,
              f"{info['camera_focal_mm']:.6f} vs {s6['overrides_json']}")
        s0 = mk.s0_row()
        r = rows[0]
        check("seeds, checkpoint, task, lane copied from S0", all(r[k] == s0[k] for k in ("checkpoint", "task", "lane", "n_episodes", "seed_base", "seed_mod", "as_shipped")),
              f"n {r['n_episodes']} seed_base {r['seed_base']} seed_mod {r['seed_mod']}")
        text = mk.to_csv(rows)
        hdr = next(csv.reader(io.StringIO(text)))
        check("columns = cells_sweep_v1.csv", hdr == mk.COLS)
        # a fake pose file from another intrinsics -> STOP
        pose = Path(d) / "pose.json"
        pose.write_text(json.dumps({"intrinsics": {"sha256": "0" * 64}, "camera_offsets": {k: 0.0 for k in ("x", "y", "z", "roll", "pitch", "yaw")},
                                    "lens": {}, "iou_full_res": {}}))
        try:
            mk.build(kp, pose)
            check("sha256 guard", False, "no STOP")
        except SystemExit as e:
            check("sha256 guard", "different intrinsics" in str(e), str(e)[:80])
        # matching pose file -> 2 rows, overrides resolve
        pose.write_text(json.dumps({"intrinsics": {"sha256": mk.sha(kp)}, "lens_inside_box": True,
                                    "camera_offsets": {"x": -0.03, "y": -0.004, "z": -0.03, "roll": 0.01, "pitch": 0.03, "yaw": 0.0},
                                    "lens": {"lens_shift_env_mm": [4, -38, -32], "delta_tilt_down_deg": 1.6, "delta_heading_deg": 0.0},
                                    "iou_full_res": {"pose_matched": 0.6, "image_matched": 0.9}}))
        rows2, _ = mk.build(kp, pose)
        ov = json.loads(rows2[1]["overrides_json"])
        check("image-matched row: focal + camera offsets", rows2[1]["cell_id"] == "H4_c920_image_matched" and ov["camera"]["pitch"] == 0.03
              and ov["camera_focal_mm"] == info["camera_focal_mm"])
        buf = io.StringIO()
        with redirect_stdout(buf):
            mk.main(["--intrinsics", str(write_intr(d, "k_close", 500.0)), "--measured-only", "--out", str(Path(d) / "c.csv")])
        check("gap <= 5 % message", "pose-matched; the image-matched cell is not needed" in buf.getvalue(), "fx 500 (-2.85 %)")
        buf = io.StringIO()
        with redirect_stdout(buf):
            mk.main(["--intrinsics", str(kp), "--pose", str(pose), "--out", str(Path(d) / "c2.csv")])
        check("gap > 5 % message", "both cells are needed" in buf.getvalue(), f"fx {fx70:.1f} ({info['fx_gap_pct']:+.2f} %)")

    if quick:
        print("(--quick: searches skipped)")
        return
    print("5. search with the sim's own K, started off-nominal")
    res = imp.match(scene, rig, rig.K_sim[0, 0], start=[8, -6, 10, 0.8, -0.6, 0.5], log=lambda *a: None)
    p = res["lens_params"]
    off = rig.offsets_for_lens(*imp.lens_move(R0, C0, p))
    L = imp.lens_summary(rig, p)
    shift = float(np.linalg.norm(L["lens_shift_env_mm"]))
    rot = imp.rot_angle_deg(R0, imp.lens_move(R0, C0, p)[0])
    check("returns to the nominal pose (<= 2 mm, <= 0.2 deg)", shift <= 2.0 and rot <= 0.2,
          f"lens shift {shift:.2f} mm, rotation {rot:.3f} deg; offsets {np.round(off, 5).tolist()}")
    print("6. fx 460 px")
    res = imp.match(scene, rig, 460.0, log=lambda *a: None)
    p = res["lens_params"]
    rep = imp.full_res_report(scene, rig, 460.0, p)
    R, C = imp.lens_move(R0, C0, p)
    ins, margin = imp.inside_box(frames, C)
    L = imp.lens_summary(rig, p)
    check("IoU gain > 0.2 and lens inside the box", rep["iou_image_matched"] - rep["iou_pose_matched"] > 0.2 and ins,
          f"IoU {rep['iou_pose_matched']:.4f} -> {rep['iou_image_matched']:.4f}; lens moved "
          f"{np.round(L['lens_shift_env_mm'], 1).tolist()} mm env, tilt {L['delta_tilt_down_deg']:+.2f} deg, "
          f"heading {L['delta_heading_deg']:+.2f} deg; margin {margin * 100:.1f} cm")


if __name__ == "__main__":
    main("--quick" in sys.argv)
    print("H4 PREP TEST " + ("PASS" if not FAILS else f"FAIL: {FAILS}"))
    sys.exit(1 if FAILS else 0)
