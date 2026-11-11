#!/usr/bin/env python3
"""Unit tests for real/trial_runner.py with rendered frames (no camera, no robot, no server is opened).

    .venv/bin/python -I tests/test_trial_runner.py
Schedule picking and re-run rules (C 1.5), the score form's rules (C 1.4-1.7), the record/CSV writer, and the
pre-trial checks (clean view, light, drift, rack pose) on the C1 render with noise, shifts and a foreign object,
through the same `reference` command the operator runs.
"""
import argparse
import contextlib
import csv
import io
import json
import sys
import tempfile
import types
from pathlib import Path

import cv2
import numpy as np

GTC = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(GTC / "calib"), str(GTC / "real")]
import capture  # noqa: E402
import trial_runner as T  # noqa: E402
import vial_check as V  # noqa: E402

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append(bool(ok))
    print(f"  {'ok  ' if ok else 'FAIL'} {name} {detail}")


def raises(fn, *a, **kw):
    try:
        fn(*a, **kw)
    except SystemExit as e:
        return str(e)
    return None


# ------------------------------------------------------------------ schedule and re-run rules
rows = [{"uid": u, "day": "Nov04", "block": b, "cond": "R1", "method": "-", "cycle": "-", "layout": "L00", "note": ""}
        for u, b in (("N04-001", "N04-R0"), ("N04-002", "N04-R0"), ("N07-021", "N07-N17 (optional)"), ("N07-022", "N07-C"))]
check("next = first row without a record", T.pick(rows, [])[0]["uid"] == "N04-001")
recs = [{"uid": "N04-001", "attempt": 1, "live_outcome": "I"}]
check("an invalid uid is not picked by next", T.pick(rows, recs)[0]["uid"] == "N04-002")
check("explicit re-run of an invalid = attempt 2", T.pick(rows, recs, "N04-001")[1] == 2)
recs2 = recs + [{"uid": "N04-002", "attempt": 1, "live_outcome": "F"}]
check("optional blocks are skipped by next", T.pick(rows, recs2)[0]["uid"] == "N07-022")
check("a scored uid is never re-run", "never re-run" in (raises(T.pick, rows, recs2, "N04-002") or ""))
check("unknown uid stops", "not in the schedule" in (raises(T.pick, rows, [], "N09-001") or ""))

# ------------------------------------------------------------------ score form
ok = T.score_form({"outcome": "S"}, {"outcome": "S", "grasp": "y", "hold_2s": "y", "hold_05s": "y", "t_release_s": "21.5"})
check("S with grasp and 2 s hold", ok["live_outcome"] == "S" and ok["live_t_release_s"] == 21.5 and ok["live_fail_code"] is None)
check("S without the 2 s hold is refused", raises(T.score_form, {}, {"outcome": "S", "grasp": "y", "hold_2s": "n",
                                                                      "hold_05s": "y"}) is not None)
check("F needs a failure code", raises(T.score_form, {}, {"outcome": "F", "grasp": "n"}) is not None)
f = T.score_form({"fail_code": "F5"}, {"outcome": "F", "grasp": "n", "flags": "rack_pushed_mm=4 wall_contact"})
check("F default code and flags", f["live_fail_code"] == "F5" and f["flags"] == {"rack_pushed_mm": "4", "wall_contact": True})
check("I needs an invalid code", raises(T.score_form, {}, {"outcome": "I", "grasp": "n"}) is not None)
i = T.score_form({"invalid_code": "I3"}, {"outcome": "I", "grasp": "n"})
check("I takes the auto-flag as default", i["invalid_code"] == "I3")

# ------------------------------------------------------------------ records
with tempfile.TemporaryDirectory() as d:
    T.write_record(Path(d), {"uid": "N04-001", "attempt": 1, "start_joints": {"a": 1.0}, "live_outcome": "F"})
    T.write_record(Path(d), {"uid": "N04-002", "attempt": 1, "live_outcome": "S"})
    lines = (Path(d) / "trials.csv").read_text().splitlines()
    check("trials.jsonl + trials.csv", len(T.load_records(Path(d) / "trials.jsonl")) == 2 and len(lines) == 3
          and lines[0].startswith("uid,attempt"), lines[1][:60])

# ------------------------------------------------------------------ checks through the reference command
img = capture.load_rgb(GTC / "results" / "c1" / "nominal_front_rgb.png")
rng = np.random.default_rng(0)
noisy = lambda x: np.clip(x.astype(np.int16) + rng.normal(0, 2.0, x.shape).round().astype(np.int16), 0, 255).astype(np.uint8)
with tempfile.TemporaryDirectory() as d:
    d = Path(d)
    (d / "frames").mkdir()
    for k in range(12):
        capture.save_rgb(d / "frames" / f"f{k:02d}.png", noisy(img))
    VIAL_ZONE, ARM_ZONE = (330, 200, 560, 330), (420, 300, 640, 480)          # rough boxes on the render
    rc = T.main(["reference", "--root", str(d), "--mock", "--tag", "TEST_R1", "--frames", "12", "--source", str(d / "frames"),
                 "--ignore-rects", ";".join(",".join(map(str, r)) for r in (VIAL_ZONE, ARM_ZONE))])
    ref_dir = d / "media" / "dryrun_real" / "refs" / "TEST_R1"
    meta = json.loads((ref_dir / "meta.json").read_text())
    check("reference written", rc == 0 and meta["frames"] == 12 and meta["rack_area_px"] > 5000,
          f"drift noise SD {meta['drift_noise_sd_px']:.3f} px, rack {meta['rack_area_px']} px")

    def run(cur, name):
        res, _ = T.run_checks(ref_dir, cur, T.CHECKS)
        return res

    r = run(noisy(img), "clean")
    check("clean frame passes all checks", r["pass"],
          f"blobs {len(r['clean_view']['blobs'])}, light {r['light']['ratio']:.3f}, drift {r['drift']['max_px']:.2f} px, "
          f"rack {r['rack'].get('centroid_err_px', 0):.2f} px / {r['rack'].get('rot_deg', 0):.2f} deg")
    tape = noisy(img)
    tape[60:85, 40:110] = (235, 235, 235)                                  # a strip of white tape on the back wall
    r = run(tape, "tape")
    check("tape outside the ignore zones fails clean view", r["clean_view"]["pass"] is False
          and r["clean_view"]["blobs"][0]["area"] > 1000, json.dumps(r["clean_view"]["blobs"][:1]))
    vial = noisy(img)
    vial[240:270, 400:470] = (20, 60, 200)                                 # an object inside the vial zone
    check("an object inside the vial zone is ignored", run(vial, "vial")["clean_view"]["pass"])
    dark = noisy((img.astype(np.float32) * 0.9).astype(np.uint8))
    r = run(dark, "dark")
    check("light 10 % down fails the light check", r["light"]["pass"] is False, f"ratio {r['light']['ratio']:.3f}")
    shift = noisy(cv2.warpAffine(img, np.float32([[1, 0, 1.0], [0, 1, 0.5]]), (640, 480), borderMode=cv2.BORDER_REPLICATE))
    r = run(shift, "shift 1.1 px")
    check("a 1.1 px camera shift passes drift and clean view", r["drift"]["pass"] and r["clean_view"]["pass"],
          f"drift {r['drift']['max_px']:.2f} px, limit {r['drift']['limit_px']:.2f}")
    shift4 = noisy(cv2.warpAffine(img, np.float32([[1, 0, 4.0], [0, 1, 0]]), (640, 480), borderMode=cv2.BORDER_REPLICATE))
    r = run(shift4, "shift 4 px")
    check("a 4 px camera shift fails drift", r["drift"]["pass"] is False, f"drift {r['drift']['max_px']:.2f} px")
    # rack moved 4 px / rotated 3 deg, everything else unchanged
    m = T.yellow_mask(img, T.CHECKS["yellow_hsv_lo"], T.CHECKS["yellow_hsv_hi"])
    ys, xs = np.nonzero(m)
    x0, x1, y0, y1 = xs.min() - 6, xs.max() + 7, ys.min() - 6, ys.max() + 7
    for name, M, want in (("rack moved 4 px", np.float32([[1, 0, 4], [0, 1, 0]]), False),
                          ("rack rotated 3 deg", cv2.getRotationMatrix2D((float(xs.mean() - x0), float(ys.mean() - y0)), 3, 1),
                           False),
                          ("rack moved 1 px", np.float32([[1, 0, 1], [0, 1, 0]]), True)):
        moved = img.copy()
        patch = img[y0:y1, x0:x1].copy()
        pm = m[y0:y1, x0:x1].astype(np.uint8)
        wp = cv2.warpAffine(patch, M, patch.shape[1::-1], borderMode=cv2.BORDER_REPLICATE)
        wm = cv2.warpAffine(pm, M, pm.shape[::-1]) > 0
        region = moved[y0:y1, x0:x1]
        region[pm > 0] = cv2.inpaint(patch, pm * 255, 5, cv2.INPAINT_TELEA)[pm > 0]   # remove the rack, put it back moved
        region[wm] = wp[wm]
        r = run(noisy(moved), name)["rack"]
        check(f"{name}: rack check {'passes' if want else 'fails'}", r["pass"] is want,
              f"centroid {r.get('centroid_err_px', 0):.2f} px, rot {r.get('rot_deg', 0):.2f} deg")

# ------------------------------------------------------------------ vial placement check (E row 13, B 5.5)
fs = json.loads((GTC / "results" / "c1" / "frames_sim.json").read_text())
tc = fs["camera_external_D455"]["tiled_camera"]                      # the render's own camera: pose in E, K
R_cam, C_cam, K_sim = V.quat_to_R(tc["quat_w_ros"]), np.array(tc["pos_w"]), np.array(tc["intrinsic_matrices"])
CAM = (R_cam, C_cam, K_sim, np.zeros(5))
w10 = fs["objects_after_warmup10"]                                   # vial poses in the nominal render
C1_LAYOUT = {"layout_id": "L01", "vials": {k: {"pos_env": w10[k]["pos"], "quat_wxyz": w10[k]["quat_wxyz"]}
                                           for k in ("vial_1", "vial_2", "vial_3")}}
ids = cv2.imread(str(GTC / "results" / "c1" / "nominal_front_instance_ids.png"), cv2.IMREAD_UNCHANGED)
labels = json.loads((GTC / "results" / "c1" / "nominal_front_instance_labels.json").read_text())["instance_labels"]
VM = {v: np.isin(ids, [int(k) for k, x in labels.items() if x["label"] and f"Vial_{v}/" in x["label"]]) for v in "123"}
k5 = np.ones((5, 5), np.uint8)
inpaint = lambda im, m: cv2.inpaint(im, cv2.dilate(m.astype(np.uint8), k5) * 255, 7, cv2.INPAINT_TELEA)
REF = inpaint(img, np.logical_or.reduce(list(VM.values())))          # the clean reference: no vials
SD = np.ones(img.shape[:2], np.float32)


def moved(v, dE=None, rot180=False):
    """The render with vial v's pixels moved by dE (m, in E) or turned end for end; the hole inpainted."""
    o, ax = np.array(w10[f"vial_{v}"]["pos"]), V.quat_to_R(w10[f"vial_{v}"]["quat_wxyz"])[:, 2]
    if rot180:
        c = V.project(np.array([o + ax * (-0.017 + 0.0995) / 2]), R_cam, C_cam, K_sim)[0]
        M = cv2.getRotationMatrix2D((float(c[0]), float(c[1])), 180, 1)
    else:
        d = np.diff(V.project(np.array([o, o + dE]), R_cam, C_cam, K_sim), axis=0)[0]
        M = np.float32([[1, 0, d[0]], [0, 1, d[1]]])
    out = inpaint(img, VM[v])
    p, pm = cv2.warpAffine(img, M, (640, 480)), cv2.warpAffine(VM[v].astype(np.uint8), M, (640, 480)) > 0
    out[pm] = p[pm]
    return out


model = V.vial_model(GTC / "no_such_file.jsonl")
check("sim tube used, with a WARNING naming the missing measurements", model[1] == "sim Vial.usda"
      and all(k in model[3][0] for k in V.MEAS_KEYS), model[3][0][:90])
tg = V.targets(C1_LAYOUT, *model[:3], R_cam, C_cam, K_sim, (480, 640))
ious = [float((tg[f"vial_{v}"]["mask"] & VM[v]).sum() / (tg[f"vial_{v}"]["mask"] | VM[v]).sum()) for v in "123"]
check("projected silhouettes match the render's vial instance masks (IoU >= 0.9)", min(ious) >= 0.9, str(np.round(ious, 3)))
with tempfile.TemporaryDirectory() as d:
    mp = Path(d) / "m.jsonl"
    mp.write_text(json.dumps({"kashi_tube_od_mm": 31.4, "kashi_tube_length_mm": 116.5, "kashi_cap_od_mm": 34.0,
                              "kashi_cap_length_mm": 14.5}) + "\n")
    mm = V.vial_model(mp)
    tgm = V.targets(C1_LAYOUT, *mm[:3], R_cam, C_cam, K_sim, (480, 640))
    iou_m = [float((tgm[f"vial_{v}"]["mask"] & VM[v]).sum() / (tgm[f"vial_{v}"]["mask"] | VM[v]).sum()) for v in "123"]
    check("measured-tube branch (sim-sized numbers) rebuilds the resting pose (IoU >= 0.85)",
          mm[1] == "measured Kashi tube" and min(iou_m) >= 0.85, str(np.round(iou_m, 3)))
try:
    V.find_layout("L10")
    l10 = True
except KeyError:
    l10 = False
check("config/layouts.json has L00-L09 and no L10-L19", all(V.find_layout(f"L{i:02d}") for i in range(10)) and not l10)
cases = [("nominal", img, True), ("vial 1 moved 10 mm sideways", moved("1", 0.010 * np.cross([0, 0, 1], V.quat_to_R(
          w10["vial_1"]["quat_wxyz"])[:, 2])), False),
         ("vial 1 moved 5 mm sideways", moved("1", 0.005 * np.cross([0, 0, 1], V.quat_to_R(w10["vial_1"]["quat_wxyz"])[:, 2])),
          True),
         ("vial 1 moved 10 mm along its axis", moved("1", 0.010 * V.quat_to_R(w10["vial_1"]["quat_wxyz"])[:, 2]), False),
         ("vial 2 laid the wrong way round", moved("2", rot180=True), False),
         ("vial 3 missing", inpaint(img, VM["3"]), False)]
for name, frame, want in cases:
    r, _ = V.check(frame, REF, SD, C1_LAYOUT, CAM, model)
    check(f"{name}: vial check {'passes' if want else 'fails'}", r["pass"] is want,
          "union %.3f; " % r["union_iou"] + ", ".join(f"{k[-1]}: IoU {x['iou']} cap {x['cap_frac']} c {x['centroid_err_px']}px"
                                                       for k, x in r["vials"].items()))

# runner side: vial_step (deferral, pose rules) and the retro command on a mock record file
with tempfile.TemporaryDirectory() as d:
    d = Path(d)
    (d / "poses").mkdir()
    (d / "poses" / "sim.json").write_text(json.dumps({"frame": "E", "R_E_cv": R_cam.tolist(), "C_E_m": C_cam.tolist()}))
    (d / "intr.json").write_text(json.dumps({"K": K_sim.tolist(), "dist": [0, 0, 0, 0, 0]}))
    (d / "layouts.json").write_text(json.dumps({"layouts": [C1_LAYOUT]}))
    res_dir, media_root, refs = T.kind_dirs(d, "mock")
    ref_dir = refs / "N04-R0_R0"
    ref_dir.mkdir(parents=True)
    capture.save_rgb(ref_dir / "ref_front_median.png", REF)
    np.save(ref_dir / "ref_front_sd.npy", SD.astype(np.float16))
    ns = argparse.Namespace(measurements=str(d / "none.jsonl"), pose=None, poses_dir=str(d / "poses"),
                            intrinsics=str(d / "intr.json"), layouts=str(d / "layouts.json"))
    check("R0 row: vial check deferred", T.vial_step(ns, "R0", "L01", ref_dir, img, d)["deferred"].startswith("R0"))
    check("R4 row without --pose: cannot check", "--pose" in T.vial_step(ns, "R4", "L01", ref_dir, img, d)["error"])
    check("R1 row, default pose s1 missing: cannot check", "s1.json" in T.vial_step(ns, "R1", "L01", ref_dir, img, d)["error"])
    ns.pose = "sim"
    r = T.vial_step(ns, "R1", "L01", ref_dir, img, d)
    check("R1 row with the pose: pass, picture saved", r["pass"] and (d / "pre_vials.png").exists(), f"IoU min {r['iou_min_seen']}")
    recs = []
    for i, (uid, frame) in enumerate((("N04-001", img), ("N04-002", cases[1][1]))):
        m = media_root / f"{uid}_a1"
        capture.save_rgb(m / "pre_front.png", frame)
        recs.append({"uid": uid, "attempt": 1, "cond": "R0", "layout": "L01", "ref_tag": "N04-R0_R0", "live_outcome": "F",
                     "pre_front": str(m / "pre_front.png"), **T.vial_fields(T.vial_step(ns, "R0", "L01", ref_dir, frame, m))})
    for rec in recs:
        T.write_record(res_dir, rec)
    rc = T.main(["vialcheck-retro", "--root", str(d), "--mock", "--pose", "sim", "--poses-dir", str(d / "poses"),
                 "--intrinsics", str(d / "intr.json"), "--layouts", str(d / "layouts.json"),
                 "--measurements", str(d / "none.jsonl")])
    after = T.load_records(res_dir / "trials.jsonl")
    check("retro: results written into the records, failure flagged, outcome untouched",
          rc == 1 and after[0]["vial_check_pass"] is True and after[1]["vial_check_pass"] is False
          and "proposal for v2" in after[1]["vial_retro_flag"] and after[1]["live_outcome"] == "F"
          and after[0]["vial_check"]["retro"] and len(list(res_dir.glob("trials.jsonl.pre-vialretro-*"))) == 1,
          f"IoU min {after[0]['vial_iou_min']} / {after[1]['vial_iou_min']}")
    check("retro: trials.csv carries the vial columns", "vial_check_pass" in (res_dir / "trials.csv").read_text().splitlines()[0])

# ------------------------------------------------------------------ mat check (R0 reference, Nov 6)
R0_REF = GTC / "media" / "real" / "refs" / "N04-R0_R0" / "ref_front_median.png"
if R0_REF.exists():
    r0 = capture.load_rgb(R0_REF)
    shift = lambda im, dx, dy: cv2.warpAffine(im, np.float32([[1, 0, dx], [0, 1, dy]]), (im.shape[1], im.shape[0]),
                                              borderMode=cv2.BORDER_REPLICATE)
    m0 = T.mat_check(r0, r0, T.CHECKS)
    check("mat: reference against itself passes", m0["pass"] and m0["max_abs_px"] == 0.0)
    m1 = T.mat_check(r0, shift(r0, 1.0, 0.0), T.CHECKS)
    check("mat: 1.0 px sideways passes and is measured", m1["pass"] and abs(m1["back"]["shift_px"][0] - 1.0) < 0.15,
          f"back {m1['back']['shift_px']}")
    m2 = T.mat_check(r0, shift(r0, 2.0, 0.0), T.CHECKS)
    check("mat: 2.0 px sideways fails", m2["pass"] is False, f"max {m2['max_abs_px']}")
    m3 = T.mat_check(r0, shift(r0, 0.0, 2.0), T.CHECKS)
    check("mat: 2.0 px down fails on the far edge", m3["pass"] is False and abs(m3["far"]["shift_px"][0] - 2.0) < 0.2,
          f"far {m3['far']['shift_px']}")
    m4 = T.mat_check(r0, shift(r0, 20.0, 0.0), T.CHECKS)
    check("mat: a 20 px drag fails", m4["pass"] is False)
    lit = np.clip(r0.astype(np.float32) * 1.05, 0, 255).astype(np.uint8)
    check("mat: 5 % brighter, no move, passes", T.mat_check(r0, lit, T.CHECKS)["pass"])
    ig0 = T.ref_ignore(R0_REF.parent)
    m5 = T.mat_check(r0, shift(r0, 0.0, 2.0), T.CHECKS, ignore=ig0)
    check("mat: R0 ignore zones leave all three edges in use", m5["pass"] is False and "shift_px" in m5["far"],
          f"far {m5['far']}")
else:
    print("  (mat check tests skipped: no R0 reference on this machine)")

# ------------------------------------------------------------------ mat check at S1 (G1 reference, Nov 8)
S1_DIR = GTC / "media" / "real" / "refs" / "N04-G1_R1"
S1_PRE = GTC / "media" / "real" / "trials" / "N04-011_a1" / "pre_front_prestart_20261109T071527Z.png"
if (S1_DIR / "ignore_mask.png").exists() and S1_PRE.exists():
    s1 = capture.load_rgb(S1_DIR / "ref_front_median.png")
    ig1 = T.ref_ignore(S1_DIR)
    shift = lambda im, dx, dy: cv2.warpAffine(im, np.float32([[1, 0, dx], [0, 1, dy]]), (im.shape[1], im.shape[0]),
                                              borderMode=cv2.BORDER_REPLICATE)
    m6 = T.mat_check(s1, capture.load_rgb(S1_PRE), T.CHECKS)
    check("mat S1: without the ignore zones the far window (wrist cable) fails as before", m6["pass"] is False
          and "reason" in m6["far"], f"far {m6['far']}")
    m7 = T.mat_check(s1, capture.load_rgb(S1_PRE), T.CHECKS, ignore=ig1)
    check("mat S1: far edge not used, back and front pass", m7["pass"] is True and m7["far"]["used"] is False
          and "shift_px" in m7["back"] and "shift_px" in m7["front"], f"back {m7['back']} front {m7['front']}")
    m8 = T.mat_check(s1, shift(s1, 2.0, 0.0), T.CHECKS, ignore=ig1)
    check("mat S1: 2.0 px sideways still fails on back/front", m8["pass"] is False, f"max {m8['max_abs_px']}")
else:
    print("  (S1 mat check tests skipped: no G1 reference or N04-011 frame on this machine)")

# ------------------------------------------------------------------ tubes-present start check (R0, Nov 6)
R0_DIR = GTC / "media" / "real" / "refs" / "N04-R0_R0"
A1, A2 = (GTC / "media" / "real" / "trials" / f"N04-001_a{k}" / "pre_front.png" for k in (1, 2))
if (R0_DIR / "tubes_L01.png").exists() and A1.exists() and A2.exists():
    t1 = T.tubes_present(R0_DIR, "L01", capture.load_rgb(A1), T.CHECKS)
    t2 = T.tubes_present(R0_DIR, "L01", capture.load_rgb(A2), T.CHECKS)
    t3 = T.tubes_present(R0_DIR, "L04", capture.load_rgb(A2), T.CHECKS)
    check("tubes: no tubes on the mat blocks the start", t1["pass"] is False, f"{t1['frac']}")
    check("tubes: the L01 tubes at L01 pass", t2["pass"] is True, f"{t2['frac']}")
    check("tubes: the L01 tubes checked as L04 block the start", t3["pass"] is False, f"{t3['frac']}")
    check("tubes: no masks for a layout -> no check", T.tubes_present(R0_DIR, "L99", capture.load_rgb(A2), T.CHECKS) is None)
else:
    print("  (tubes-present tests skipped: no R0 masks or frames on this machine)")

# ------------------------------------------------------------------ score form left unfinished (Nov 7, N04B-002)
with tempfile.TemporaryDirectory() as d:
    d = Path(d)
    sched = d / "schedule.csv"
    with open(sched, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    res_dir = T.kind_dirs(d, "mock")[0]
    res_dir.mkdir(parents=True, exist_ok=True)
    rec = {"uid": "N04-001", "attempt": 1, "block": "N04-R0", "cond": "R1", "layout": "L00", "kind": "mock",
           "end_reason": "safety_key", "auto_invalid": [], "key_t_s": 18.7, "run_s": 22.1, "n_chunks": 29}
    up = T.save_unscored(res_dir, "N04-001_a1", rec)
    a = types.SimpleNamespace(score_json=None, schedule=str(sched))
    real_form = T.score_form

    def interrupted(*args, **kw):
        raise KeyboardInterrupt
    T.score_form = interrupted
    with contextlib.redirect_stderr(io.StringIO()) as err:
        done = T.finish_score(a, res_dir, dict(rec), "N04-001_a1", "mock", up)
    T.score_form = real_form
    recs = T.load_records(res_dir / "trials.jsonl")
    check("Ctrl+C in the form: no record, trial kept unscored", not done and not recs and up.exists()
          and "score --uid N04-001" in err.getvalue())
    pend = T.unscored_pending(res_dir, recs)
    check("next refuses a row that ran unscored", "not scored" in (raises(T.pick, rows, recs, None, pend) or ""))
    check("run --uid refuses it too", "not scored" in (raises(T.pick, rows, recs, "N04-001", pend) or ""))
    with contextlib.redirect_stdout(io.StringIO()):
        rc = T.main(["score", "--root", str(d), "--schedule", str(sched), "--mock", "--uid", "N04-001", "--score-json",
                     json.dumps({"outcome": "F", "grasp": "n", "flags": "wall_contact"})])
    recs = T.load_records(res_dir / "trials.jsonl")
    check("score writes the record from the saved trial", rc == 0 and len(recs) == 1 and recs[0]["live_fail_code"] == "F5"
          and recs[0]["n_chunks"] == 29 and recs[0]["flags"] == {"wall_contact": True}
          and "scored_after_form_interrupt_utc" in recs[0])
    pend = T.unscored_pending(res_dir, recs)
    check("after scoring, next moves on and nothing is pending", not pend and T.pick(rows, recs, None, pend)[0]["uid"] == "N04-002")
    check("score refuses a uid with a record", "no unscored trial" in (raises(T.main, ["score", "--root", str(d), "--schedule",
          str(sched), "--mock", "--uid", "N04-001", "--score-json", "{}"]) or ""))
    T.save_unscored(res_dir, "N04-002_a1", {**rec, "uid": "N04-002"})
    with contextlib.redirect_stdout(io.StringIO()):
        a = types.SimpleNamespace(score_json=json.dumps({"outcome": "S", "grasp": "y", "hold_2s": "n", "hold_05s": "y"}),
                                  schedule=str(sched))
        with contextlib.redirect_stderr(io.StringIO()):
            done = T.finish_score(a, res_dir, {**rec, "uid": "N04-002"}, "N04-002_a1", "mock",
                                  res_dir / "unscored" / "N04-002_a1.json")
    check("a refused answer (S without the hold) also keeps the trial unscored", not done
          and "N04-002" in T.unscored_pending(res_dir, T.load_records(res_dir / "trials.jsonl")))

# ------------------------------------------------------------------ tube check, "shift" method (addendum entry 2 draft)
R0B = GTC / "media" / "real" / "trials" / "N04B-004_a1" / "pre_front.png"
R0B_REF = GTC / "media" / "real" / "refs" / "N04B-R0_R0"
R0_POSE = GTC / "results" / "poses" / "r0.json"
if R0B.exists() and R0B_REF.exists() and R0_POSE.exists():
    cam = V.load_camera(R0_POSE, GTC / "config" / "c920_intrinsics.json")
    cur, ref = capture.load_rgb(R0B), capture.load_rgb(R0B_REF / "ref_front_median.png")
    sd = np.load(R0B_REF / "ref_front_sd.npy").astype(np.float32)
    model = V.vial_model()
    th = {**V.TH, "method": "shift"}
    ok, _ = V.check(cur, ref, sd, V.find_layout("L02"), cam, model, th)
    check("shift: N04B-004 (L02) passes, offsets in mm", ok["pass"] and all("across_mm" in v for v in ok["vials"].values()),
          str({k: (v["across_mm"], v["along_mm"]) for k, v in ok["vials"].items()}))
    reg, _ = V.check(cur, ref, sd, V.find_layout("L02"), cam, model, V.TH)
    check("registered IoU method on the same frame (documents the Nov 7 finding)", not reg["pass"], f"union {reg['union_iou']}")
    bad, _ = V.check(cur, ref, sd, V.find_layout("L03"), cam, model, th)
    check("shift: the L02 tubes checked as L03 fail", not bad["pass"])
    line = T.vial_line({**ok, "method": "shift"})
    check("pre-trial line shows mm per tube", "across" in line and "mm" in line, line[:80])
else:
    print("  (shift-method tests skipped: no N04B-R0 frames, reference or r0 pose on this machine)")

# ------------------------------------------------------------------ joint map (option; default = the course's conversion)
with tempfile.TemporaryDirectory() as d:
    jp = Path(d) / "jm.json"
    jp.write_text(json.dumps({"joints": {"shoulder_pan.pos": {"scale": 0.92, "offset": 1.5}, "gripper.pos": {"scale": 0.87}}}))
    jm = T.load_joint_map(str(jp))
    check("no map = as registered (identity)", T.load_joint_map(None) is None and T.map_act({"shoulder_pan.pos": 10.0}, None)
          == {"shoulder_pan.pos": 10.0})
    act = {k: 20.0 for k in T.JOINT_KEYS}
    r = T.map_act(act, jm)
    check("map_act: scale and offset per joint, others unchanged", abs(r["shoulder_pan.pos"] - 19.9) < 1e-9
          and abs(r["gripper.pos"] - 17.4) < 1e-9 and r["elbow_flex.pos"] == 20.0)
    back = T.map_obs(r, jm)
    check("map_obs inverts map_act", all(abs(back[k] - act[k]) < 1e-9 for k in act))
    check("map_act clamps to the joint's range", T.map_act({"shoulder_pan.pos": 120.0}, jm)["shoulder_pan.pos"] == 100.0
          and T.map_act({"gripper.pos": -5.0}, jm)["gripper.pos"] == 0.0)
    jp.write_text(json.dumps({"joints": {"elbow.pos": {"scale": 1.0}}}))
    check("unknown joint stops", "unknown joint" in (raises(T.load_joint_map, str(jp)) or ""))

print(f"TRIAL RUNNER UNITS {'PASS' if all(RESULTS) else 'FAIL'} ({sum(RESULTS)}/{len(RESULTS)})")
sys.exit(0 if all(RESULTS) else 1)
