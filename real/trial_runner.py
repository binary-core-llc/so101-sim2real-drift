#!/usr/bin/env python3
"""Real-trial runner (D_software C10; C_trials sections 1-2 and 4): one schedule row per trial, the course policy
loop with the 60 s cap, the 3 s policy-socket watchdog, operator keys, keyframes, pre-trial checks, a live score
form and one record per trial in results/real/trials.jsonl (+ trials.csv). Runs in the real-robot container:

    real/run_real.sh python /workspace/gtc/real/trial_runner.py next                    # the next scheduled trial
    real/run_real.sh python /workspace/gtc/real/trial_runner.py run --uid N04-003       # one row; re-run of an invalid
    real/run_real.sh python /workspace/gtc/real/trial_runner.py run --pilot V28-01 --cond R1 --layout L00   # unscored
    .venv/bin/python -I real/trial_runner.py reference --tag N04-R0_R0 --draw            # references (host, C920x free)
    .venv/bin/python -I real/trial_runner.py status                                     # progress and open invalids
    .venv/bin/python -I real/trial_runner.py vialcheck-retro --pose r0                  # R0 vial check, after the R0 PnP

Per trial (C 1.3 and 2.1): reset card -> Enter -> preflight (devices by USB identity, camera lock applied and read
back, server ping within the timeout, pre-trial front/wrist frames, clean-view / light / drift / rack-pose checks
against the block reference, vial placement check against the layout projected from the measured camera pose,
real/vial_check.py) -> Enter: connect, the arm goes to the course initial pose (3 s) -> Enter: policy.
Vial check (E row 13, B 5.5): camera pose = --pose (default s1; camera conditions R4/R5/R7/R9 must name theirs).
R0 rows defer it, because the R0 pose is measured only after the R0 block (E rows 9/28, G8): their pre-trial frames
are checked later by `vialcheck-retro --pose r0`, which writes the result into the records and flags failures.
T0 = the first policy query; the trial ends at the first of: key s (success seen), f (safety stop), i (invalid),
q or space (stop), cap (T0 + 60 s), watchdog (no policy reply within 3 s), crash (camera, bus or server error).
On every end: end frame, servo temperatures, lock readback, then the course disconnect (home pose, torque off).
Never press Ctrl+C twice (a second interrupt aborts the home move); the hard stop is the 12 V plug.

The robot never moves without the operator's Enter: --yes is refused unless --mock-robot. Scored trials refuse a
cap, timeout, action horizon or instruction other than the pre-registered ones. A uid that already has a scored
(non-invalid) record is never re-run (C 1.5); a uid with only invalid records runs as attempt n+1.
A preflight or connect failure is not a trial (I0): it goes to prestart.jsonl and the reserve is not used.
Auto-flags suggested to the score form: I1 camera timeout or >= 3 identical consecutive keyframes; I2 bus error;
I3 watchdog, server error or a chunk latency > 1 s; I4 camera lock changed during the trial; I6 served model path
differs from the pre-registered one.

References (`reference`): N frames of the block's clean scene (rack at the condition pose by jig, no vials, arm at
rest, door closed, light at level) -> median, per-pixel noise SD, the drift noise floor (each frame vs the median)
and an ignore mask (vial zone and arm zone; drawn with --draw, or --ignore-rects, or copied with --ignore-from).
The check thresholds are proposals [P] until prereg v2 fixes them; every record carries the values used.
Same pieces as the course docker/real/scripts/so101_eval.py, unchanged: SO101Control and So100Adapter, 30 Hz.
"""
import argparse
import builtins
import csv
import datetime as dt
import fcntl
import hashlib
import json
import queue
import re
import sys
import threading
import time
from pathlib import Path

import numpy as np

GTC = Path(__file__).resolve().parents[1]
COURSE_SCRIPTS = Path("/Isaac-GR00T/gr00t/eval/real_robot/SO100")
sys.path[:0] = [str(GTC / "calib"), str(GTC / "real"), str(COURSE_SCRIPTS)]
import pilot  # noqa: E402  (KeyWatcher, patched_client, MockControl, make_real_control)
import usbcam  # noqa: E402

# pre-registered trial constants (prereg v1/B_methods; C 1.1)
LANG = pilot.LANG
CAP_S, TIMEOUT_S, HORIZON = 60.0, 3.0, 16
PREREG_MODEL = "/workspace/models/aravindhs-NV/grootn16-finetune_sreetz-so101_teleop_vials_rack_left/checkpoint-10000"
PST = dt.timezone(dt.timedelta(hours=-8))                              # Pacific standard time, Nov 1 - Mar
LAT_INVALID_S, FREEZE_N = 1.0, 3                                        # I3 latency spike (C 1.5), I1 frozen keyframes
# pre-trial check thresholds [P] (C 2.1 step 7; C D4: set from the Nov 4 noise floor); recorded in every trial
CHECKS = dict(clean_k=6.0, clean_floor=25, clean_min_area_px=150, clean_open_px=5, light_tol=0.05,
              drift_min_px=1.5, drift_k=3.0, rack_px=2.0, rack_deg=1.0, rack_min_area_px=300, mat_px=1.5, tubes_min_frac=0.6,
              yellow_hsv_lo=[20, 90, 90], yellow_hsv_hi=[38, 255, 255])
END = {"success_seen": "success_key", "safety_stop": "safety_key", "invalid": "invalid_key", "stop": "stop_key"}
COND_TEXT = {"R0": "course camera instructions (camera at S0 by tape, HUD closed); rack, mat, vials, light as R1",
             "R1": "sim-matched nominal", "R2": "rack y+3 cm (M1, E0)", "R3": "rack x+3 cm (sign fixed by reach)",
             "R4": "camera tilt_down +6.0 deg (M2, E0)", "R5": "camera tilt_down +1.5 deg",
             "R6": "E3 correction at M1", "R7": "E3 correction at M2", "R8": "E1 correction at M1",
             "R9": "E1 correction at M2"}
CSV_COLS = ["uid", "attempt", "rerun_of", "day", "actual_date", "block", "cond", "method", "cycle", "layout",
            "operator", "t_enter", "t_launch", "t0_first_query", "t_end", "end_reason", "end_detail", "run_s",
            "n_chunks", "n_actions", "chunk_at_key", "lat_ms_med", "lat_ms_p95", "lat_ms_max", "n_lat_gt_1s",
            "act_period_ms_med", "act_period_ms_p95", "ref_tag", "checks_mode", "cleanview_pass", "cleanview_score",
            "light_ratio", "drift_px", "drift_deg", "rack_centroid_err_px", "rack_rot_deg", "lock_pre", "lock_after_open",
            "lock_end", "mat_shift_px", "mat_shift_post_px", "start_joints", "temp_pre", "temp_post", "calib_sha256", "model_path", "groot_ref",
            "runner_sha256", "gtc_commit", "schedule_sha256", "instruction", "action_horizon", "cap_s",
            "policy_timeout_s", "front_dev", "wrist_dev", "auto_invalid", "live_outcome", "live_grasp",
            "live_t_grasp_s", "live_t_release_s", "live_hold_2s", "live_hold_05s", "live_fail_code", "flags",
            "invalid_code", "note", "pre_front", "pre_wrist", "post_front", "kf_front_mp4", "kf_wrist_mp4",
            "kf_dir", "steps_jsonl", "mock_robot", "vial_check_pass", "vial_iou_min", "vial_pose_tag",
            "vial_retro_flag"]
CAMERA_CONDS = ("R4", "R5", "R7", "R9")                                 # camera moved: the vial check needs --pose


def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def git_head(repo=GTC):
    """HEAD commit without the git binary (the container has none for our repo)."""
    g = repo / ".git"
    try:
        head = (g / "HEAD").read_text().strip()
        if not head.startswith("ref: "):
            return head
        ref = head[5:]
        if (g / ref).exists():
            return (g / ref).read_text().strip()
        for line in (g / "packed-refs").read_text().splitlines():
            if line.endswith(" " + ref):
                return line.split()[0]
    except OSError:
        pass
    return None


# ---------------------------------------------------------------- schedule and records
def kind_dirs(root, kind):
    """results dir, media dir, refs dir for real | pilot | mock (mock never mixes with real data)."""
    sub = {"real": ("results/real", "media/real/trials", "media/real/refs"),
           "pilot": ("results/real/shakedown", "media/real/shakedown", "media/real/refs"),
           "mock": ("results/dryrun_real", "media/dryrun_real/trials", "media/dryrun_real/refs")}[kind]
    return tuple(Path(root) / s for s in sub)


def load_schedule(path):
    rows = list(csv.DictReader(open(path, newline="")))
    uids = [r["uid"] for r in rows]
    if len(set(uids)) != len(uids):
        raise SystemExit(f"STOP: duplicate uids in {path}")
    return rows


def load_records(path):
    return [json.loads(line) for line in open(path)] if Path(path).exists() else []


def unscored_pending(res_dir, recs):
    """{uid: path} of trials saved before the score form (unscored/<uid>_a<n>.json) that have no record yet."""
    have = {(r["uid"], r["attempt"]) for r in recs}
    out = {}
    for p in sorted((Path(res_dir) / "unscored").glob("*_a*.json")):
        uid, _, n = p.stem.rpartition("_a")
        if n.isdigit() and (uid, int(n)) not in have:
            out[uid] = p
    return out


def pick(rows, recs, uid=None, pending=None):
    """(row, attempt): the given uid, or the first row in schedule order with no record (optional blocks skipped).
    pending = unscored_pending(): a row whose trial ran but was not scored is never started again (score it)."""
    by = {}
    for r in recs:
        by.setdefault(r["uid"], []).append(r)
    pending = pending or {}
    if uid is None:
        for row in rows:
            if row["uid"] in pending:
                raise SystemExit(f"STOP: {row['uid']} ran but is not scored ({pending[row['uid']]}); score it first: "
                                 f"trial_runner.py score --uid {row['uid']}")
            if row["uid"] not in by and "optional" not in row["block"]:
                return row, 1
        raise SystemExit("All scheduled rows have a record. Open invalids: see `status`.")
    row = next((x for x in rows if x["uid"] == uid), None)
    if row is None:
        raise SystemExit(f"STOP: {uid} is not in the schedule")
    if uid in pending:
        raise SystemExit(f"STOP: {uid} ran but is not scored ({pending[uid]}); score it first: trial_runner.py score "
                         f"--uid {uid}")
    prev = by.get(uid, [])
    scored = [r for r in prev if r.get("live_outcome") != "I"]
    if scored:
        raise SystemExit(f"STOP: {uid} already has a scored record (attempt {scored[0]['attempt']}, "
                         f"outcome {scored[0].get('live_outcome')}); a trial is never re-run because it failed (C 1.5)")
    return row, len(prev) + 1


def write_record(res_dir, rec):
    res_dir.mkdir(parents=True, exist_ok=True)
    with open(res_dir / "trials.jsonl", "a") as f:
        f.write(json.dumps(rec, default=str) + "\n")
    write_csv(res_dir, load_records(res_dir / "trials.jsonl"))


def write_csv(res_dir, recs):
    with open(res_dir / "trials.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLS, extrasaction="ignore")
        w.writeheader()
        for r in recs:
            w.writerow({k: json.dumps(v) if isinstance(v, (dict, list)) else v for k, v in r.items()})


def append_jsonl(path, rec):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(rec, default=str) + "\n")


def append_check(res_dir, typ, values, ok, note=""):
    p = res_dir / "checks.csv"
    res_dir.mkdir(parents=True, exist_ok=True)
    new = not p.exists()
    with open(p, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["utc", "type", "values_json", "pass", "note"])
        w.writerow([utc(), typ, json.dumps(values, default=str), ok, note])


# ---------------------------------------------------------------- pre-trial checks (pure functions, unit-tested)
def yellow_mask(rgb, lo, hi):
    import cv2
    m = cv2.inRange(cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV), np.array(lo, np.uint8), np.array(hi, np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
    if n <= 1:
        return np.zeros(m.shape, bool)
    return lab == 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))


def rack_pose(ref_m, cur_m, th):
    """Yellow-mask centroid shift (px) and in-plane rotation (deg, ECC Euclidean on the blurred masks)."""
    import cv2
    rec = {"ref_area_px": int(ref_m.sum()), "cur_area_px": int(cur_m.sum())}
    if rec["ref_area_px"] < th["rack_min_area_px"]:
        return {**rec, "pass": None, "reason": "reference has no rack-sized yellow region; check skipped"}
    if rec["cur_area_px"] < th["rack_min_area_px"]:
        return {**rec, "pass": False, "reason": "no rack-sized yellow region in the pre-trial frame"}
    c0, c1 = (np.argwhere(m).mean(axis=0)[::-1] for m in (ref_m, cur_m))
    rec["centroid_err_px"] = float(np.hypot(*(c1 - c0)))
    g0, g1 = (cv2.GaussianBlur(m.astype(np.float32), (0, 0), 2.0) for m in (ref_m, cur_m))
    warp = np.eye(2, 3, dtype=np.float32)
    warp[:, 2] = c1 - c0
    try:
        _, warp = cv2.findTransformECC(g0, g1, warp, cv2.MOTION_EUCLIDEAN,
                                       (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-6), None, 5)
        rec["rot_deg"] = float(np.degrees(np.arctan2(warp[1, 0], warp[0, 0])))
    except cv2.error as e:
        return {**rec, "pass": False, "reason": f"ECC on the rack mask did not converge: {str(e).splitlines()[-1]}"}
    rec["pass"] = rec["centroid_err_px"] <= th["rack_px"] and abs(rec["rot_deg"]) <= th["rack_deg"]
    return rec


def clean_view(ref, sd, ignore, cur, th, warp=None):
    """Changed blobs outside the ignore mask after undoing the drift warp; light ratio over the same pixels."""
    import cv2
    h, w = ref.shape[:2]
    back = cur if warp is None else cv2.warpPerspective(cur, warp, (w, h), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP)
    keep = ~ignore
    diff = np.abs(back.astype(np.int16) - ref.astype(np.int16)).max(axis=2)
    out = ((diff > np.maximum(th["clean_k"] * sd, th["clean_floor"])) & keep).astype(np.uint8)
    k = th["clean_open_px"]
    out = cv2.morphologyEx(out, cv2.MORPH_OPEN, np.ones((k, k), np.uint8))
    n, _, st, _ = cv2.connectedComponentsWithStats(out, 8)
    blobs = [dict(zip(("x", "y", "w", "h", "area"), map(int, st[i]))) for i in range(1, n)
             if st[i, cv2.CC_STAT_AREA] >= th["clean_min_area_px"]]
    ratio = float(back[keep].mean() / max(ref[keep].mean(), 1e-6))
    return ({"pass": not blobs, "score_px": int(out.sum()), "blobs": sorted(blobs, key=lambda b: -b["area"])[:10]},
            {"pass": abs(ratio - 1) <= th["light_tol"], "ratio": ratio}, out)


# Mat edges seen by the R0 front camera (Nov 6: the jaw dragged the mat in V28-01): per edge, the scan lines, the
# direction of the step from mat to floor, the search window, and the two places where the fitted line is compared.
MAT_EDGES = {"back": dict(axis="row", lines=range(90, 241, 3), x=(60, 230), sign=-1, at=(110, 230)),
             "front": dict(axis="row", lines=range(300, 476, 3), x=(430, 620), sign=+1, at=(300, 460)),
             "far": dict(axis="col", lines=range(430, 497, 3), x=(55, 125), sign=-1, at=(440, 490))}


def edge_points(gray, e, guess=None, win=12):
    """Per scan line, the subpixel position of the strongest mat/floor step (gradient peak), within +-win px of the
    reference line when one is given, else over the whole window. Level-free, so light changes do not move it."""
    import cv2
    g = cv2.GaussianBlur(gray.astype(np.float32), (0, 0), 1.2)
    pts = []
    for s in e["lines"]:
        prof = g[s, :] if e["axis"] == "row" else g[:, s]
        lo, hi = e["x"]
        if guess is not None:
            c = guess(s)
            lo, hi = max(lo, int(c) - win), min(hi, int(c) + win + 1)
        d = e["sign"] * np.diff(prof[lo:hi])                     # + where the step goes the mat->floor way
        if len(d) < 3:
            continue
        i = int(np.argmax(d))
        if d[i] < 4.0 or i in (0, len(d) - 1):                   # no clear edge here (tube, shadow, arm)
            continue
        a, b, c3 = d[i - 1], d[i], d[i + 1]
        x = lo + i + 0.5 + 0.5 * (a - c3) / (a - 2 * b + c3)
        pts.append((x, s))
    return np.array(pts)


def fit_edge(p, tol=1.0):
    """Line x = m*s + q through (x, s) points, two passes dropping points > max(tol, 2.5 MAD) px away."""
    keep = np.ones(len(p), bool)
    for _ in range(2):
        m, q = np.polyfit(p[keep, 1], p[keep, 0], 1)
        r = np.abs(p[:, 0] - (m * p[:, 1] + q))
        keep = r <= max(tol, 2.5 * np.median(r[keep]))
    return m, q, int(keep.sum())


def edge_window(e):
    """An edge's search window as (rows, cols) slices."""
    lo, hi = e["x"]
    span = slice(e["lines"].start, e["lines"][-1] + 1)
    return (span, slice(lo, hi)) if e["axis"] == "row" else (slice(lo, hi), span)


def ref_ignore(ref_dir):
    import cv2
    return cv2.imread(str(Path(ref_dir) / "ignore_mask.png"), cv2.IMREAD_GRAYSCALE) > 0


def mat_check(ref, cur, th, warp=None, ignore=None):
    """Mat edges in the pre-trial frame against the reference: shift of each fitted edge line at two places, px.
    Fails above th['mat_px'] or if an edge has too few clear points (covered). A camera drift shows here as well.
    An edge whose search window lies wholly inside the reference's ignore zones is not used (Nov 8: at S1 the far
    edge's window falls inside the arm zone and sees only the wrist camera's cable, not the mat)."""
    import cv2
    h, w = ref.shape[:2]
    back = cur if warp is None else cv2.warpPerspective(cur, warp, (w, h), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP)
    g0, g1 = (cv2.cvtColor(x, cv2.COLOR_RGB2GRAY) for x in (ref, back))
    out, ok = {"limit_px": th["mat_px"]}, True
    for name, e in MAT_EDGES.items():
        if ignore is not None and ignore[edge_window(e)].all():
            out[name] = {"used": False, "reason": "search window wholly inside the reference's ignore zones"}
            continue
        p0 = edge_points(g0, e)
        if len(p0) < 0.5 * len(e["lines"]):
            return {**out, "pass": None, "reason": f"reference: {name} edge not found; check skipped"}
        m0, q0, _ = fit_edge(p0)
        p1 = edge_points(g1, e, guess=lambda s: m0 * s + q0)
        if len(p1) < 0.5 * len(e["lines"]):
            out[name] = {"n": len(p1), "reason": "edge covered or moved beyond the search window"}
            ok = False
            continue
        m1, q1, n1 = fit_edge(p1)
        sh = [round(float((m1 * s + q1) - (m0 * s + q0)), 2) for s in e["at"]]
        out[name] = {"shift_px": sh, "n": n1}
        ok &= max(abs(x) for x in sh) <= th["mat_px"]
    out["max_abs_px"] = max((max(abs(x) for x in v["shift_px"]) for k, v in out.items()
                             if isinstance(v, dict) and "shift_px" in v), default=None)
    out["pass"] = bool(ok)
    return out


def run_checks(ref_dir, cur, th):
    """All pre-trial checks against one reference folder -> (summary dict, diff image)."""
    import cv2
    import capture
    import drift_check
    meta = json.loads((ref_dir / "meta.json").read_text())
    ref = capture.load_rgb(ref_dir / "ref_front_median.png")
    sd = np.load(ref_dir / "ref_front_sd.npy").astype(np.float32)
    ignore = cv2.imread(str(ref_dir / "ignore_mask.png"), cv2.IMREAD_GRAYSCALE) > 0
    static = ((~ignore) & (cv2.cvtColor(ref, cv2.COLOR_RGB2GRAY) > 8)).astype(np.uint8)
    drift, warp = drift_check.compare(ref, cur, static)
    lim = max(th["drift_min_px"], th["drift_k"] * meta["drift_noise_sd_px"])
    d = {"pass": drift.get("verdict") != "STOP" and drift.get("max_px", 1e9) <= lim, "max_px": drift.get("max_px"),
         "rot_deg": drift.get("rotation_deg"), "limit_px": lim, "verdict_b8": drift.get("verdict"),
         "reason": drift.get("reason")}
    cv_, light, out = clean_view(ref, sd, ignore, cur, th, warp)
    lo, hi = th["yellow_hsv_lo"], th["yellow_hsv_hi"]
    rack = rack_pose(yellow_mask(ref, lo, hi), yellow_mask(cur, lo, hi), th)
    mat = mat_check(ref, cur, th, ignore=ignore)   # no drift warp: the drift estimate itself leans on the mat
    vis = drift_check.diff_image(ref, cur, warp)
    vis[:, 2 * ref.shape[1]:][out > 0] = (255, 0, 255)
    ok = all(x["pass"] is not False for x in (d, cv_, light, rack, mat))
    return {"pass": ok, "clean_view": cv_, "light": light, "drift": d, "rack": rack, "mat": mat}, vis


# ---------------------------------------------------------------- reference
def cmd_reference(a):
    import cv2
    import capture
    import drift_check
    kind = "mock" if a.mock else "real"
    res_dir, _, refs = kind_dirs(a.root, kind)
    out = refs / a.tag
    if out.exists() and not a.replace:
        raise SystemExit(f"STOP: reference {a.tag} exists ({out}); pass --replace to make a new one")
    lock_rc = None
    if a.source.startswith("camera:"):
        import camera_lock
        lock_rc = camera_lock.cmd_apply(a.source.split(":", 1)[1], write=True)
        if lock_rc != 0:
            raise SystemExit("STOP: camera lock does not read back")
    src = capture.open_source(a.source)
    try:
        frames = [src.read() for _ in range(a.frames)]
        ident = src.identity
    finally:
        src.close()
    stack = np.stack(frames).astype(np.float32)
    med = np.median(stack, axis=0).round().astype(np.uint8)
    sd = stack.std(axis=0).max(axis=2)
    out.mkdir(parents=True, exist_ok=True)
    if a.ignore_from:
        ignore = cv2.imread(str(refs / a.ignore_from / "ignore_mask.png"), cv2.IMREAD_GRAYSCALE) > 0
    else:
        rects = []
        if a.ignore_rects:
            rects = [tuple(int(v) for v in r.split(",")) for r in a.ignore_rects.split(";") if r.strip()]
            rects = [(x0, y0, x1 - x0, y1 - y0) for x0, y0, x1, y1 in rects]
        if a.draw:
            print("Drag a box over the vial zone (all layouts, with margin), Enter; then over the arm at rest, Enter; "
                  "Esc when done. Leave the rack, walls, floor and door uncovered.")
            rects += [tuple(int(v) for v in r) for r in
                      cv2.selectROIs("ignore zones", cv2.cvtColor(med, cv2.COLOR_RGB2BGR), False, False)]
            cv2.destroyAllWindows()
        if not rects:
            raise SystemExit("STOP: no ignore zones (vial zone and arm zone); use --draw, --ignore-rects or --ignore-from")
        ignore = np.zeros(med.shape[:2], bool)
        for x, y, w, h in rects:
            ignore[y:y + h, x:x + w] = True
    static = ((~ignore) & (cv2.cvtColor(med, cv2.COLOR_RGB2GRAY) > 8)).astype(np.uint8)
    noise = [drift_check.compare(med, f, static)[0].get("max_px") for f in frames]
    noise = [x for x in noise if x is not None]
    lo, hi = CHECKS["yellow_hsv_lo"], CHECKS["yellow_hsv_hi"]
    rack = yellow_mask(med, lo, hi)
    capture.save_rgb(out / "ref_front_median.png", med)
    np.save(out / "ref_front_sd.npy", sd.astype(np.float16))
    cv2.imwrite(str(out / "ignore_mask.png"), ignore.astype(np.uint8) * 255)
    vis = med.copy()
    vis[ignore] = (vis[ignore] * 0.4).astype(np.uint8)
    vis[rack] = (255, 0, 255)
    capture.save_rgb(out / "ref_check.png", vis)
    meta = {"tag": a.tag, "utc": utc(), "frames": a.frames, "source": a.source, "identity": ident, "lock_apply": lock_rc,
            "drift_noise_px": [round(x, 4) for x in noise], "drift_noise_sd_px": float(np.std(noise)) if noise else 0.0,
            "sd_median": float(np.median(sd)), "ignore_frac": float(ignore.mean()), "rack_area_px": int(rack.sum()),
            "note": a.note}
    (out / "meta.json").write_text(json.dumps(meta, indent=1, default=str))
    append_check(res_dir, "clean_ref", {k: meta[k] for k in ("tag", "frames", "drift_noise_sd_px", "sd_median",
                                                             "ignore_frac", "rack_area_px")}, True, a.note)
    print(f"REFERENCE {a.tag}: {a.frames} frames, drift noise SD {meta['drift_noise_sd_px']:.3f} px, pixel SD median "
          f"{meta['sd_median']:.2f}, ignore {100 * meta['ignore_frac']:.0f} % of the image, rack {meta['rack_area_px']} px "
          f"-> {out}  (check ref_check.png: rack magenta, ignore zones dark)")
    return 0


# ---------------------------------------------------------------- vial placement check (E row 13, B 5.5)
def local(path):
    """A path written inside the container (/workspace/gtc/...) as seen from wherever this runs."""
    p = Path(str(path))
    if not p.exists() and str(p).startswith("/workspace/gtc/"):
        p = GTC / str(p)[len("/workspace/gtc/"):]
    return p


def tubes_present(ref_dir, layout_id, pre_front, th):
    """Start blocker while the tube check is deferred (R0, Nov 6: attempt 1 of N04-001 ran with no tubes): each tube's
    projected spot (tubes_<layout>.png in the reference folder, tools/ignore_zone_check.py --write-tube-masks) must have
    changed against the tube-free reference over >= th['tubes_min_frac'] of its pixels. None if the masks are absent."""
    import cv2
    import capture
    lab_p = ref_dir / f"tubes_{layout_id}.png"
    if not lab_p.exists():
        return None
    lab = cv2.imread(str(lab_p), cv2.IMREAD_GRAYSCALE)
    ref = capture.load_rgb(ref_dir / "ref_front_median.png").astype(np.int16)
    sd = np.load(ref_dir / "ref_front_sd.npy").astype(np.float32)
    ch = (np.abs(pre_front.astype(np.int16) - ref).max(axis=2) > np.maximum(th["clean_k"] * sd, 20)).astype(np.uint8)
    ch = cv2.morphologyEx(ch, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)) > 0
    frac = [round(float(ch[lab == i].mean()), 3) for i in sorted(set(np.unique(lab)) - {0})]
    return {"frac": frac, "min_frac": th["tubes_min_frac"], "pass": bool(frac) and min(frac) >= th["tubes_min_frac"]}


def vial_step(a, cond, layout_id, ref_dir, pre_front, media, pose_tag=None, out_name="pre_vials.png"):
    """Vial check of one pre-trial frame -> result dict (pass True/False/None). R0: deferred (no pose yet)."""
    import capture
    import vial_check as V
    model = V.vial_model(a.measurements)
    if cond == "R0" and pose_tag is None:
        tp = tubes_present(ref_dir, layout_id, pre_front, CHECKS)
        if tp is not None:                                      # picture: green = where this layout's tubes belong
            import cv2
            lab = cv2.imread(str(ref_dir / f"tubes_{layout_id}.png"), cv2.IMREAD_GRAYSCALE)
            cnt, _ = cv2.findContours((lab > 0).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            vis = pre_front.copy()
            cv2.drawContours(vis, cnt, -1, (0, 255, 0), 1)
            capture.save_rgb(media / out_name, vis)
        if tp is not None and not tp["pass"]:
            return {"pass": False, "tubes_present": tp, "warnings": model[3],
                    "error": f"tubes not at the {layout_id} spots (changed fraction per tube {tp['frac']}, need >= "
                             f"{tp['min_frac']}; pose-free start check)"}
        return {"pass": None, "deferred": "R0: the camera pose is measured after the R0 block (E rows 9/28, G8); "
                                          "run `trial_runner.py vialcheck-retro --pose r0` then", "tubes_present": tp,
                "warnings": model[3]}
    tag = pose_tag or a.pose or (None if cond in CAMERA_CONDS else "s1")
    if tag is None:
        return {"pass": False, "error": f"condition {cond} moves the camera: pass --pose <tag of this setup's PnP>"}
    try:
        cam = V.load_camera(Path(a.poses_dir) / f"{tag}.json", a.intrinsics)
        layout = V.find_layout(layout_id, a.layouts)
        ref = capture.load_rgb(ref_dir / "ref_front_median.png")
        sd = np.load(ref_dir / "ref_front_sd.npy").astype(np.float32)
    except (OSError, ValueError, KeyError, SystemExit) as e:
        return {"pass": False, "error": f"cannot check: {type(e).__name__}: {e}", "pose_tag": tag}
    method = getattr(a, "vial_method", None) or "iou"
    th = {**V.TH, "method": method, **({"across_mm": a.vial_across_mm} if getattr(a, "vial_across_mm", None) else {})}
    res, vis = V.check(pre_front, ref, sd, layout, cam, model, th)
    capture.save_rgb(media / out_name, vis)
    res.update({"pose_tag": tag, "vis": str(media / out_name), "method": method})
    return res


JOINT_KEYS = ["shoulder_pan.pos", "shoulder_lift.pos", "elbow_flex.pos", "wrist_flex.pos", "wrist_roll.pos", "gripper.pos"]


def load_joint_map(path):
    """None (the course's conversion as is, as registered) or {joint: (scale, offset)} from a JSON file
    {"joints": {"shoulder_pan.pos": {"scale": s, "offset": o}, ...}}: the value sent to the real arm is s * v + o for the
    policy's value v, and the policy sees (v_real - o) / s. Joints not listed stay as they are."""
    if not path:
        return None
    j = json.loads(Path(path).read_text())
    m = {k: (float(v.get("scale", 1.0)), float(v.get("offset", 0.0))) for k, v in j["joints"].items()}
    bad = [k for k in m if k not in JOINT_KEYS or m[k][0] <= 0]
    if bad:
        raise SystemExit(f"STOP: joint map {path}: unknown joint or scale <= 0: {bad}")
    return m


def map_obs(obs, jmap):
    if not jmap:
        return obs
    out = dict(obs)
    for k, (sc, of) in jmap.items():
        if k in out:
            out[k] = (float(out[k]) - of) / sc
    return out


def map_act(act, jmap):
    if not jmap:
        return act
    out = dict(act)
    for k, (sc, of) in jmap.items():
        if k in out:
            lo, hi = (0.0, 100.0) if k == "gripper.pos" else (-100.0, 100.0)
            out[k] = min(hi, max(lo, sc * float(out[k]) + of))
    return out


def vial_line(vc):
    """One line for the pre-trial printout: per tube IoU / cap (registered), or offset on the mat in mm (shift)."""
    if vc.get("deferred") or vc.get("error"):
        return vc.get("deferred") or vc.get("error")
    if vc.get("method") == "shift":
        return "; ".join(f"{k}: across {v.get('across_mm')} mm, along {v.get('along_mm')} mm, covered {v['cover']}, cap "
                         f"{v['cap_frac']}{'' if v['pass'] else ' <- re-place'}" for k, v in vc["vials"].items())
    return json.dumps({"union_iou": vc["union_iou"], **{k: [v["iou"], v["cap_frac"]] for k, v in vc["vials"].items()}})


def vial_fields(res):
    return {"vial_check": res, "vial_check_pass": res.get("pass"), "vial_iou_min": res.get("iou_min_seen"),
            "vial_pose_tag": res.get("pose_tag")}


def cmd_vial_retro(a):
    """Vial check of saved pre-trial frames once the camera pose exists (R0: E rows 9/28, G8). Writes the result
    into each record's vial fields; a failure is flagged for review (proposal for v2: re-label I4), not re-scored."""
    import capture
    import shutil
    res_dir, _, refs = kind_dirs(a.root, "mock" if a.mock else "real")
    path = res_dir / "trials.jsonl"
    recs = load_records(path)
    todo = [r for r in recs if r.get("cond") == a.cond and (a.redo or (r.get("vial_check") or {}).get("deferred"))]
    if not todo:
        print(f"no {a.cond} record with a deferred vial check in {path}")
        return 0
    for r in todo:
        media = local(r["pre_front"]).parent
        res = vial_step(a, r["cond"], r["layout"], refs / r["ref_tag"], capture.load_rgb(local(r["pre_front"])), media,
                        pose_tag=a.pose, out_name="pre_vials_retro.png")
        res.update({"retro": True, "retro_utc": utc()})
        r.update(vial_fields(res))
        r["vial_retro_flag"] = None if res["pass"] else \
            "vial check failed after the block: review; proposal for v2: re-label I4 and re-run from the reserve"
        print(f"  {r['uid']} a{r['attempt']} {r['layout']}: {'PASS' if res['pass'] else 'FAIL'} "
              + (f"IoU min {res.get('iou_min_seen')}, union {res.get('union_iou')}" if "vials" in res else res.get("error", "")))
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    shutil.copy2(path, path.with_name(f"trials.jsonl.pre-vialretro-{stamp}"))      # audit copy, never deleted
    tmp = path.with_name("trials.jsonl.tmp")
    tmp.write_text("".join(json.dumps(r, default=str) + "\n" for r in recs))
    tmp.replace(path)
    write_csv(res_dir, recs)
    bad = [r["uid"] for r in todo if not r["vial_check_pass"]]
    print(f"VIAL RETRO {a.cond} with pose {a.pose}: {len(todo) - len(bad)}/{len(todo)} pass"
          + (f"; FLAGGED for review: {bad}" if bad else "") + f" -> {path}")
    return 1 if bad else 0


# ---------------------------------------------------------------- status
def cmd_status(a):
    rows = load_schedule(a.schedule)
    res_dir, _, _ = kind_dirs(a.root, "mock" if a.mock else "real")
    recs = load_records(res_dir / "trials.jsonl")
    by = {}
    for r in recs:
        by.setdefault(r["uid"], []).append(r)
    print(f"schedule {a.schedule} sha256 {sha256(a.schedule)}")
    blocks = {}
    for row in rows:
        b = blocks.setdefault(row["block"], [row["day"], 0, 0, 0])
        b[1] += 1
        rr = by.get(row["uid"], [])
        if any(r.get("live_outcome") in ("S", "F") for r in rr):
            b[2] += 1
        elif rr:
            b[3] += 1
    for name, (day, n, done, inv) in blocks.items():
        print(f"  {day} {name:22s} {done:3d}/{n:<3d} scored" + (f", {inv} invalid awaiting re-run" if inv else ""))
    pending = unscored_pending(res_dir, recs)
    for uid, p in pending.items():
        print(f"  UNSCORED: {uid} ran but has no record ({p}): trial_runner.py score --uid {uid}")
    try:
        row, _ = pick(rows, recs, None, pending)
        print(f"next: {row['uid']} {row['block']} {row['cond']} {row['layout']}")
    except SystemExit as e:
        print(e)
    return 0


# ---------------------------------------------------------------- the trial
class FrameMock(pilot.MockControl):
    """Dry runs: replayed images with a per-call pixel change (so the I1 freeze flag stays quiet), no motion."""

    def __init__(self, front, wrist, freeze=False):
        super().__init__(front, wrist)
        self.n, self.freeze = 0, freeze

    def get_observation(self):
        obs = super().get_observation()
        if not self.freeze:
            self.n += 1
            for k in ("front", "wrist"):
                obs[k][0, 0] = (self.n % 256, self.n // 256 % 256, 0)
        return obs


class KeyframeWriter(threading.Thread):
    """Writes the exact policy inputs (one front/wrist pair per chunk) off the control loop."""

    def __init__(self, folder):
        super().__init__(daemon=True)
        self.q, self.folder, self.n = queue.Queue(), folder, 0

    def run(self):
        import cv2
        self.folder.mkdir(parents=True, exist_ok=True)
        while (item := self.q.get()) is not None:
            i, front, wrist = item
            cv2.imwrite(str(self.folder / f"chunk_{i:03d}_front.png"), cv2.cvtColor(front, cv2.COLOR_RGB2BGR))
            cv2.imwrite(str(self.folder / f"chunk_{i:03d}_wrist.png"), cv2.cvtColor(wrist, cv2.COLOR_RGB2BGR))
            self.n += 1


def to_mp4(folder, cam, path, fps=2.0):
    import cv2
    files = sorted(folder.glob(f"chunk_*_{cam}.png"))
    if not files:
        return None
    first = cv2.imread(str(files[0]))
    vw = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (first.shape[1], first.shape[0]))
    for f in files:
        vw.write(cv2.imread(str(f)))
    vw.release()
    return str(path)


def read_temps(control):
    """Present_Temperature (register 63) of every motor, read outside the control loop; None if unavailable."""
    try:
        bus = control.robot.bus
        return {m: int(bus.read("Present_Temperature", m, normalize=False)) for m in bus.motors}
    except Exception:  # noqa: BLE001  (mock control, bus error)
        return None


def lock_check(write):
    import camera_lock
    try:
        return camera_lock.cmd_apply("all", write=write)
    except SystemExit as e:
        print(e, file=sys.stderr)
        return 2


def score_form(defaults, given=None):
    """Live score (C 1.7). `given` (dict) answers without prompting (dry runs)."""
    try:
        import readline  # noqa: F401  (Nov 6: arrow keys edit the line instead of typing "^[[D" into the note)
    except ImportError:
        pass
    def ask(key, prompt, valid, default=None, required=True):
        if given is not None:
            v = given.get(key, default)
        else:
            while True:
                v = input(f"  {prompt}" + (f" [{default}]" if default not in (None, "") else "") + ": ").strip() or default
                if v in (None, "") and not required:
                    return None
                if v is not None and valid(v):
                    break
                print("    not valid, again")
        if v in (None, "") and not required:
            return None
        if v is None or not valid(v):
            raise SystemExit(f"STOP: score field {key}={v!r} is not valid")
        return v

    yn = lambda v: str(v).lower() in ("y", "n")
    num = lambda v: re.fullmatch(r"\d+(\.\d+)?", str(v)) is not None
    out = {"live_outcome": ask("outcome", "outcome S/F/I", lambda v: v in ("S", "F", "I"), defaults.get("outcome"))}
    s = out["live_outcome"] == "S"
    out["live_grasp"] = ask("grasp", "grasp (a vial lifted >= 1 cm for >= 1 s) y/n", yn, "y" if s else None) == "y"
    out["live_t_grasp_s"] = ask("t_grasp_s", "time to grasp, s from T0 (blank = unknown)", num, None, False)
    out["live_t_release_s"] = ask("t_release_s", "time to release, s from T0 (blank = unknown)", num,
                                  defaults.get("t_release_s") if s else None, False)
    out["live_hold_2s"] = ask("hold_2s", "seated vial held >= 2 s y/n", yn, "y" if s else "n") == "y"
    out["live_hold_05s"] = ask("hold_05s", "seated vial held >= 0.5 s y/n", yn, "y" if s else "n") == "y"
    if s and not (out["live_grasp"] and out["live_hold_2s"]):
        raise SystemExit("STOP: S needs a grasp and the 2 s hold (C 1.4); score it again as F")
    out["live_fail_code"] = ask("fail_code", "failure code F1-F7", lambda v: re.fullmatch(r"F[1-7]", v) is not None,
                                defaults.get("fail_code")) if out["live_outcome"] == "F" else None
    out["invalid_code"] = ask("invalid_code", "invalid code I1-I6", lambda v: re.fullmatch(r"I[1-6]", v) is not None,
                              defaults.get("invalid_code")) if out["live_outcome"] == "I" else None
    flags = ask("flags", "flags (rack_pushed_mm=N wall_contact regrasp_n=N oscillation second_vial_attempt)",
                lambda v: True, None, False) or ""
    out["flags"] = {kv.split("=")[0]: (kv.split("=", 1)[1] if "=" in kv else True) for kv in str(flags).split()}
    out["note"] = ask("note", "note", lambda v: True, None, False)
    for k in ("live_t_grasp_s", "live_t_release_s"):
        out[k] = None if out[k] is None else float(out[k])
    return out


def prestart(res_dir, rec, reason):
    """I0: not a trial (C 1.5). Logged; no trials.jsonl record; the reserve is not used. The pre-trial pictures are kept
    under their own names (Nov 6: a later passing attempt overwrote the frame of a failed preflight)."""
    import shutil
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for key in ("pre_front", "pre_wrist"):
        if rec.get(key) and Path(local(rec[key])).exists():
            src = Path(local(rec[key]))
            for f in [src] + [src.with_name(n) for n in ("pre_checks.png", "pre_vials.png") if key == "pre_front"]:
                if f.exists():
                    dst = f.with_name(f"{f.stem}_prestart_{stamp}{f.suffix}")
                    shutil.copy2(f, dst)
                    rec.setdefault("prestart_files", []).append(str(dst))
    append_jsonl(res_dir / "prestart.jsonl", {**rec, "end_reason": "prestart", "invalid_code": "I0", "reason": reason,
                                              "t_end": utc()})
    print(f"PRESTART ABORT (I0, not a trial): {reason}\nFix it and start the same row again.", file=sys.stderr)
    return 3


def cmd_run(a, uid=None):
    kind = "mock" if a.mock_robot else "pilot" if a.pilot else "real"
    if a.yes and not a.mock_robot:
        raise SystemExit("STOP: --yes is only for --mock-robot; the robot never moves without the operator's Enter")
    if kind == "real" and (a.cap_s, a.timeout_s, a.action_horizon, a.lang) != (CAP_S, TIMEOUT_S, HORIZON, LANG):
        raise SystemExit("STOP: scored trials use the pre-registered cap 60 s, timeout 3 s, horizon 16 and instruction")
    if a.skip_checks and kind == "real":
        raise SystemExit("STOP: --skip-checks is for --pilot and --mock-robot only (use --checks warn if the checks "
                         "themselves misbehave; it is recorded)")
    res_dir, media_root, refs = kind_dirs(a.root, kind)
    res_dir.mkdir(parents=True, exist_ok=True)
    lockf = open(res_dir / ".runner.lock", "w")
    try:
        fcntl.flock(lockf, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit("STOP: another trial_runner is running")
    sched_sha = sha256(a.schedule)
    if a.expect_schedule_sha256 and sched_sha != a.expect_schedule_sha256:
        raise SystemExit(f"STOP: schedule sha256 {sched_sha} is not the expected {a.expect_schedule_sha256}")
    if a.pilot:
        row, attempt = {"uid": a.pilot, "day": "-", "block": "PILOT", "cond": a.cond, "method": "-", "cycle": "-",
                        "layout": a.layout, "note": "unscored shakedown"}, 1
        if any(r["uid"] == a.pilot for r in load_records(res_dir / "trials.jsonl")):
            raise SystemExit(f"STOP: pilot {a.pilot} already exists")
    else:
        recs = load_records(res_dir / "trials.jsonl")
        row, attempt = pick(load_schedule(a.schedule), recs, uid, unscored_pending(res_dir, recs))
    now_pst = dt.datetime.now(PST)                                # the container clock is UTC
    today = now_pst.strftime("%b%d")
    tag = a.ref or f"{row['block']}_{row['cond']}"
    key = f"{row['uid']}_a{attempt}"
    media = media_root / key
    steps_path = res_dir / "steps" / f"{key}.jsonl"
    rec = {"uid": row["uid"], "attempt": attempt, "rerun_of": f"{row['uid']}_a{attempt - 1}" if attempt > 1 else None,
           "day": row["day"], "actual_date": now_pst.date().isoformat(), "block": row["block"], "cond": row["cond"],
           "method": row["method"], "cycle": row["cycle"], "layout": row["layout"], "schedule_note": row.get("note"),
           "operator": a.operator, "kind": kind, "mock_robot": a.mock_robot, "ref_tag": tag, "checks_mode": a.checks,
           "check_thresholds": CHECKS, "instruction": a.lang, "action_horizon": a.action_horizon, "cap_s": a.cap_s,
           "policy_timeout_s": a.timeout_s, "model_path": a.model_path, "schedule": str(a.schedule),
           "schedule_sha256": sched_sha, "runner_sha256": sha256(__file__), "pilot_sha256": sha256(pilot.__file__),
           "gtc_commit": git_head(), "groot_ref": git_head(Path("/Isaac-GR00T")) if Path("/Isaac-GR00T/.git").exists()
           else None, "course_commit": None}
    jmap = load_joint_map(getattr(a, "joint_map", None))
    rec["joint_map"] = None if not jmap else {"path": str(a.joint_map), "sha256": sha256(a.joint_map),
                                              "joints": {k: {"scale": v[0], "offset": v[1]} for k, v in jmap.items()}}
    print(f"\n=== {row['uid']} attempt {attempt}  block {row['block']}  {row['cond']}: {COND_TEXT.get(row['cond'], '')}"
          f"\n    method {row['method']}  cycle {row['cycle']}  layout {row['layout']}  ({row.get('note', '')})"
          f"\n    schedule sha256 {sched_sha[:16]}...  reference {tag}")
    if row["day"] not in ("-", today):
        print(f"    note: planned day {row['day']}, today {today}; the real date is logged (C 3.8.1)")
    if not a.yes:
        input("Reset done (C 2.1 A-B: rack by jig, vials by stencil and stencil out, nothing extra in either view, "
              "door closed, light at level). Enter = preflight ")
    rec["t_enter"] = utc()
    # 1. preflight: devices, lock, server, pre-trial frames, checks (any failure: I0, nothing moved)
    import capture
    if not a.mock_robot:
        try:
            front, wrist, arm = usbcam.find("front"), usbcam.find("wrist"), usbcam.find("follower")
        except usbcam.DeviceError as e:
            return prestart(res_dir, rec, str(e))
        rec["front_dev"], rec["wrist_dev"], rec["follower_dev"] = front, wrist, arm
        rec["lock_pre"] = lock_check(write=True)
        if rec["lock_pre"] != 0:
            return prestart(res_dir, rec, "camera lock does not read back (B 2.4)")
    try:
        client = pilot.patched_client(a.policy_host, a.policy_port, a.timeout_s)
        t = time.time()
        if not client.ping():
            return prestart(res_dir, rec, f"policy server {a.policy_host}:{a.policy_port} did not answer in {a.timeout_s} s")
        rec["ping_s"] = round(time.time() - t, 3)
    except Exception as e:  # noqa: BLE001
        return prestart(res_dir, rec, f"policy server ping failed: {type(e).__name__}: {e}")
    try:                                                       # our capture path (C5), released before LeRobot opens
        src = capture.Source(a.mock_front) if a.mock_robot else capture.Camera("front", fourcc=a.fourcc)
        try:
            pre_front = capture.mean_frames(src, 3)
        finally:
            src.close()
        src = capture.Source(a.mock_wrist) if a.mock_robot else capture.Camera("wrist", fourcc=a.wrist_fourcc)
        try:
            pre_wrist = src.read()
        finally:
            src.close()
    except SystemExit as e:
        return prestart(res_dir, rec, f"pre-trial frame: {e}")
    if a.mock_robot and a.mock_pre_front:
        pre_front = capture.load_rgb(a.mock_pre_front)
    capture.save_rgb(media / "pre_front.png", pre_front)
    capture.save_rgb(media / "pre_wrist.png", pre_wrist)
    rec["pre_front"], rec["pre_wrist"] = str(media / "pre_front.png"), str(media / "pre_wrist.png")
    if a.skip_checks:
        rec["checks"] = {"pass": None, "skipped": True}
    else:
        if not (refs / tag / "meta.json").exists():
            return prestart(res_dir, rec, f"no reference {tag} in {refs}; capture it at the block start: "
                                          f".venv/bin/python -I real/trial_runner.py reference --tag {tag} --draw")
        rec["checks"], vis = run_checks(refs / tag, pre_front, CHECKS)
        capture.save_rgb(media / "pre_checks.png", vis)
        c = rec["checks"]
        rec.update({"cleanview_pass": c["clean_view"]["pass"], "cleanview_score": c["clean_view"]["score_px"],
                    "light_ratio": c["light"]["ratio"], "drift_px": c["drift"]["max_px"], "drift_deg": c["drift"]["rot_deg"],
                    "rack_centroid_err_px": c["rack"].get("centroid_err_px"), "rack_rot_deg": c["rack"].get("rot_deg"),
                    "mat_shift_px": c["mat"].get("max_abs_px")})
        for name in ("clean_view", "light", "drift", "rack", "mat"):
            x = c[name]
            print(f"    check {name:10s} {'PASS' if x['pass'] else 'skipped' if x['pass'] is None else 'FAIL'}  "
                  + json.dumps({k: v for k, v in x.items() if k != 'pass'}, default=str)[:160])
        if not c["pass"]:
            if a.checks == "block":
                return prestart(res_dir, rec, f"pre-trial check failed (see {media / 'pre_checks.png'}: magenta = "
                                              "changed outside the ignore zones); fix the scene and press Enter again")
            print("    checks FAILED but --checks warn: continuing; recorded")
        vc = vial_step(a, row["cond"], row["layout"], refs / tag, pre_front, media)
        rec.update(vial_fields(vc))
        for w in vc.get("warnings", []):
            print("    " + w)
        state = "deferred" if vc.get("deferred") else "PASS" if vc["pass"] else "FAIL"
        print(f"    check {'vials':10s} {state}  " + vial_line(vc))
        if vc["pass"] is False:
            if a.checks == "block":
                why = vc.get("error") or (f"a tube more than {vc['thresholds']['across_mm']} mm across / "
                                          f"{vc['thresholds']['along_mm']} mm along its target, not covered, or its cap "
                                          f"at the wrong end: {vial_line(vc)}" if vc.get("method") == "shift" else
                                          f"IoU {vc['iou_min_seen']} < {vc['thresholds']['iou_min']} or a cap at the wrong end")
                return prestart(res_dir, rec, f"vials not on their targets ({why}; see {media / 'pre_vials.png'}: green "
                                              "targets, magenta seen): re-place with the stencil")
            print("    vial check FAILED but --checks warn: continuing; recorded")
    # 2. connect (the arm rises to the course initial pose)
    env = dict(re.findall(r"export (\w+)=(\S+)", Path("/root/env").read_text())) if Path("/root/env").exists() else {}
    robot_id = env.get("ROBOT_ID", "orange_robot")
    calib = Path(f"/root/.cache/huggingface/lerobot/calibration/robots/so101_follower/{robot_id}.json")
    rec["calib_sha256"] = sha256(calib) if calib.exists() else None
    from so101_eval import So100Adapter
    policy = So100Adapter(client)
    control = FrameMock(a.mock_front, a.mock_wrist, a.mock_freeze) if a.mock_robot else \
        pilot.make_real_control(front["node"], wrist["node"], a.fourcc, a.wrist_fourcc, arm["node"], robot_id)
    if not a.yes:
        input("Preflight PASS. Go to the standing spot, hands off the table. Enter = connect (the arm rises to the start "
              "pose over 3 s) ")
    rec["t_launch"] = utc()
    real_input = builtins.input

    def no_prompt(*args, **kw):
        raise RuntimeError(f"calibration prompt at connect: {args[0] if args else ''}")
    builtins.input = no_prompt                               # C finding 4: never answer LeRobot's calibration prompt
    try:
        control.connect()
    except Exception as e:  # noqa: BLE001
        builtins.input = real_input
        try:
            control.robot.bus.disconnect(disable_torque=True)
        except Exception:  # noqa: BLE001
            pass
        return prestart(res_dir, rec, f"connect failed: {type(e).__name__}: {e}" +
                        (" -> calibration mismatch: see C 5.5; do not answer the prompt" if "calibration" in str(e) else ""))
    builtins.input = real_input
    keys = pilot.KeyWatcher()
    writer = KeyframeWriter(media / "kf")
    stop, detail, t_first, n_chunk, n_act, chunk_at_key = None, None, None, 0, 0, None
    lats, periods, last_hash, runs, max_run = [], [], {}, {}, {}
    try:
        obs0 = control.get_observation()
        rec["start_joints"] = {k: float(v) for k, v in obs0.items() if k.endswith(".pos")}
        rec["temp_pre"] = read_temps(control)
        if not a.mock_robot:
            rec["lock_after_open"] = lock_check(write=False)            # B 2.4 (ii): after the client opened the stream
            if rec["lock_after_open"] != 0:
                for k in range(3):                                      # Nov 6: one write did not fix a gain jump
                    rec["lock_reapplied"], rec["lock_writes"] = lock_check(write=True), k + 1
                    if rec["lock_reapplied"] == 0:
                        break
                    control.get_observation()
                    time.sleep(0.2)
                if rec["lock_reapplied"] != 0:
                    stop, detail = "prestart", "camera lock does not hold after the stream opened"
                    raise RuntimeError(detail)
        if not a.yes:
            input("Start pose reached. Enter = start the policy (keys: s success, f safety stop, i invalid, q/space stop) ")
        writer.start()
        keys.start()
        steps_path.parent.mkdir(parents=True, exist_ok=True)
        with open(steps_path, "w") as log:
            while stop is None:
                if keys.event.is_set():
                    break
                obs = control.get_observation()
                obs["lang"] = a.lang
                for cam in ("front", "wrist"):
                    h = hashlib.md5(obs[cam].tobytes()).hexdigest()
                    runs[cam] = runs.get(cam, 0) + 1 if h == last_hash.get(cam) else 1
                    last_hash[cam], max_run[cam] = h, max(max_run.get(cam, 0), runs[cam])
                tq = time.time()
                t_first = t_first or tq
                if n_chunk == 0:
                    rec["t0_first_query"] = utc()
                try:
                    actions = policy.get_action(map_obs(obs, jmap))
                except Exception as e:  # noqa: BLE001
                    n = type(e).__name__
                    stop, detail = ("watchdog", f"no policy reply within {a.timeout_s} s") if n == "Again" else \
                        ("crash", f"policy/server: {n}: {e}")
                    break
                tr = time.time()
                lats.append(tr - tq)
                writer.q.put((n_chunk, obs["front"], obs["wrist"]))
                sent, sends = 0, []
                for act in actions[: a.action_horizon]:
                    if keys.event.is_set() or time.time() - t_first > a.cap_s:
                        break
                    tic = time.time()
                    act_r = map_act(act, jmap)
                    control.send_action(act_r)
                    control.update_log_action(act_r)
                    sends.append(tic)
                    sent += 1
                    d_ = time.time() - tic
                    if d_ < 1.0 / 30:
                        time.sleep(1.0 / 30 - d_)
                periods += [1000 * (b - a_) for a_, b in zip(sends, sends[1:])]
                n_act += sent
                log.write(json.dumps({"chunk": n_chunk, "t_query_s": round(tq - t_first, 4), "t_reply_s": round(tr - t_first, 4),
                                      "latency_s": round(tr - tq, 4), "sent": sent,
                                      "send_t_s": [round(s - t_first, 4) for s in sends],
                                      "joints": {k: float(v) for k, v in obs.items() if k.endswith(".pos")},
                                      "actions": actions[: a.action_horizon],
                                      **({"actions_sent": [map_act(x, jmap) for x in actions[: sent]]} if jmap else {})},
                                     default=float) + "\n")
                n_chunk += 1
                if time.time() - t_first > a.cap_s:
                    stop = "cap"
        if stop is None and keys.event.is_set():
            stop = END[keys.label]
            chunk_at_key = n_chunk - 1 if n_chunk else None
    except KeyboardInterrupt:
        stop, detail = "crash", "ctrl_c"
    except TimeoutError as e:
        stop, detail = "crash", f"camera: {e}"
    except (ConnectionError, OSError) as e:
        stop, detail = "crash", f"bus: {type(e).__name__}: {e}"
    except Exception as e:  # noqa: BLE001
        stop, detail = stop or "crash", detail or f"{type(e).__name__}: {e}"
    finally:
        keys.event.set()
        rec["t_end"] = utc()
        try:
            end = control.get_observation()                        # the scoring instant (C 1.3 step 5)
            capture.save_rgb(media / "post_front.png", end["front"])
            rec["post_front"] = str(media / "post_front.png")
            if (refs / tag / "ref_front_median.png").exists():        # descriptive: did the mat move during the trial?
                rec["mat_post"] = mat_check(capture.load_rgb(refs / tag / "ref_front_median.png"), end["front"], CHECKS,
                                            ignore=ref_ignore(refs / tag))
                rec["mat_shift_post_px"] = rec["mat_post"].get("max_abs_px")
        except Exception as e:  # noqa: BLE001
            rec["post_front_error"] = f"{type(e).__name__}: {e}"
        rec["temp_post"] = read_temps(control)
        if not a.mock_robot:
            rec["lock_end"] = lock_check(write=False)
        try:
            control.stop_logging_thread()
            control.disconnect()                                   # course: home pose over 3 s, then torque off
        except Exception as e:  # noqa: BLE001
            rec["disconnect_error"] = f"{type(e).__name__}: {e}"
            print("ARM NOT HOMED by the runner: if it holds torque, pull the 12 V plug.", file=sys.stderr)
        writer.q.put(None)
        if writer.is_alive():
            writer.join()
        if keys.is_alive():
            keys.join(timeout=1.0)                                 # terminal mode restored before the score form
    if stop == "prestart":
        return prestart(res_dir, rec, detail)
    lat_ms = np.array(lats) * 1000
    rec.update({"end_reason": stop, "end_detail": detail, "key_t_s": round(keys.t - t_first, 2) if keys.t and t_first else None,
                "chunk_at_key": chunk_at_key, "run_s": round(time.time() - t_first, 2) if t_first else 0.0,
                "n_chunks": n_chunk, "n_actions": n_act, "keyframes_written": writer.n,
                "lat_ms_med": float(np.median(lat_ms)) if lats else None,
                "lat_ms_p95": float(np.percentile(lat_ms, 95)) if lats else None,
                "lat_ms_max": float(lat_ms.max()) if lats else None, "n_lat_gt_1s": int((lat_ms > 1000 * LAT_INVALID_S).sum()),
                "act_period_ms_med": float(np.median(periods)) if periods else None,
                "act_period_ms_p95": float(np.percentile(periods, 95)) if periods else None,
                "max_identical_keyframes": max_run, "steps_jsonl": str(steps_path), "kf_dir": str(media / "kf"),
                "kf_front_mp4": to_mp4(media / "kf", "front", media / "kf_front.mp4"),
                "kf_wrist_mp4": to_mp4(media / "kf", "wrist", media / "kf_wrist.mp4")})
    auto = []
    if (detail or "").startswith("camera") or max(max_run.values() or [0]) >= FREEZE_N:
        auto.append("I1")
    if (detail or "").startswith("bus"):
        auto.append("I2")
    if stop == "watchdog" or (detail or "").startswith("policy/server") or rec["n_lat_gt_1s"]:
        auto.append("I3")
    if rec.get("lock_end") not in (None, 0):
        auto.append("I4")
    if a.model_path != PREREG_MODEL:
        auto.append("I6")
    rec["auto_invalid"] = auto
    print(f"\nEND {row['uid']}: {stop}{' (' + detail + ')' if detail else ''} after {rec['run_s']} s, {n_chunk} chunks, "
          f"{n_act} actions; latency med {rec['lat_ms_med'] or 0:.0f} ms, p95 {rec['lat_ms_p95'] or 0:.0f} ms"
          + (f"; AUTO-FLAGS {auto}" if auto else ""))
    unscored = save_unscored(res_dir, key, rec)              # Nov 7: Ctrl+C in the form lost N04B-002's record
    if not finish_score(a, res_dir, rec, key, kind, unscored):
        return 5
    return 4 if stop in ("watchdog", "crash") else 0


def score_defaults(rec):
    stop, auto = rec.get("end_reason"), rec.get("auto_invalid") or []
    return {"outcome": "S" if stop == "success_key" else "I" if (stop == "invalid_key" or auto) else "F",
            "fail_code": "F5" if stop == "safety_key" else None, "invalid_code": auto[0] if auto else None,
            "t_release_s": round(rec["key_t_s"] - 3, 1) if stop == "success_key" and rec.get("key_t_s") else None}


def save_unscored(res_dir, key, rec):
    """The trial as it ended, before the score form; kept after scoring (the record is the scored copy)."""
    p = Path(res_dir) / "unscored" / f"{key}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(rec, default=str))
    tmp.replace(p)
    return p


def finish_score(a, res_dir, rec, key, kind, unscored):
    """Score form -> record. If the form is left (Ctrl+C or a refused answer) the trial stays saved unscored."""
    if a.score_json is None:
        print("Score (C 1.4-1.7; Enter = the value in brackets):")
    try:
        rec.update(score_form(score_defaults(rec), json.loads(a.score_json) if a.score_json else None))
    except (KeyboardInterrupt, SystemExit) as e:
        print(f"\nScore form not finished ({type(e).__name__}{': ' + str(e) if str(e) else ''}). The trial is saved, "
              f"unscored, in {unscored}.\nScore it with: trial_runner.py score --uid {rec['uid']}   (next and run refuse "
              f"this row until it is scored)", file=sys.stderr)
        return False
    write_record(res_dir, rec)
    print(f"RECORD {key}: {rec['live_outcome']}" + (f" {rec['live_fail_code']}" if rec["live_fail_code"] else "")
          + (f" {rec['invalid_code']}" if rec["invalid_code"] else "") + f" -> {res_dir / 'trials.jsonl'}")
    if rec["live_outcome"] == "I" and kind == "real":
        print(f"Invalid: if the cause is fixed within 10 min, re-run now: trial_runner.py run --uid {rec['uid']}; "
              "otherwise it goes to the reserve block (C 1.5).")
    if kind != "pilot":
        try:
            recs = load_records(res_dir / "trials.jsonl")
            nxt, _ = pick(load_schedule(a.schedule), recs, None, unscored_pending(res_dir, recs))
            print(f"next: {nxt['uid']} {nxt['block']} {nxt['cond']} layout {nxt['layout']}")
        except SystemExit as e:
            print(e)
    return True


def cmd_score(a):
    """Score a trial that ran but whose score form was not finished (its unscored/<uid>_a<n>.json, no record yet)."""
    kind = "mock" if a.mock else "real"
    res_dir, _, _ = kind_dirs(a.root, kind)
    pending = unscored_pending(res_dir, load_records(res_dir / "trials.jsonl"))
    if a.uid not in pending:
        raise SystemExit(f"STOP: no unscored trial for {a.uid} in {res_dir / 'unscored'} (or it already has a record)")
    p = pending[a.uid]
    rec = json.loads(p.read_text())
    print(f"=== {rec['uid']} attempt {rec['attempt']} ({rec['block']} {rec['cond']} {rec['layout']}): ended "
          f"{rec.get('end_reason')}{' (' + rec['end_detail'] + ')' if rec.get('end_detail') else ''} after "
          f"{rec.get('run_s')} s, {rec.get('n_chunks')} chunks, key at {rec.get('key_t_s')} s"
          + (f"; AUTO-FLAGS {rec['auto_invalid']}" if rec.get("auto_invalid") else ""))
    rec["scored_after_form_interrupt_utc"] = utc()
    return 0 if finish_score(a, res_dir, rec, p.stem, rec.get("kind", kind), p) else 5


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--root", default=str(GTC), help="output root (tests); default the gtc repo")
    common.add_argument("--schedule", default=str(GTC / "config" / "schedule.csv"))
    for name in ("next", "run"):
        p = sub.add_parser(name, parents=[common])
        if name == "run":
            g = p.add_mutually_exclusive_group(required=True)
            g.add_argument("--uid")
            g.add_argument("--pilot", help="unscored shakedown run name (needs --cond, --layout)")
            p.add_argument("--cond", default="R1")
            p.add_argument("--layout", default="L00")
        p.add_argument("--operator", default="AMR")
        p.add_argument("--ref", help="reference tag (default <block>_<cond>)")
        p.add_argument("--checks", choices=["block", "warn"], default="block")
        p.add_argument("--skip-checks", action="store_true", help="pilot and mock only")
        p.add_argument("--expect-schedule-sha256")
        p.add_argument("--model-path", default=PREREG_MODEL, help="the path groot-server serves (docker inspect)")
        p.add_argument("--lang", default=LANG)
        p.add_argument("--cap-s", type=float, default=CAP_S)
        p.add_argument("--timeout-s", type=float, default=TIMEOUT_S)
        p.add_argument("--action-horizon", type=int, default=HORIZON)
        p.add_argument("--policy-host", default="localhost")
        p.add_argument("--policy-port", type=int, default=5555)
        p.add_argument("--fourcc", default="MJPG")
        p.add_argument("--wrist-fourcc", default="MJPG")
        p.add_argument("--yes", action="store_true", help="no Enter prompts (mock only)")
        p.add_argument("--score-json", help="score answers as JSON instead of the form (dry runs)")
        p.add_argument("--mock-robot", action="store_true")
        p.add_argument("--mock-freeze", action="store_true", help="mock frames never change (tests the I1 flag)")
        p.add_argument("--mock-front", default=str(GTC / "results" / "c1" / "nominal_front_rgb.png"))
        p.add_argument("--mock-wrist", default=str(GTC / "results" / "c1" / "nominal_wrist_rgb.png"))
        p.add_argument("--mock-pre-front", help="pre-trial front frame for the checks (tests)")
        p.add_argument("--joint-map", help="JSON per-joint scale/offset between the policy's values and the real arm's "
                       "(default none: the course's conversion as is, as registered)")
    for p in [sub.choices["next"], sub.choices["run"]] + [sub.add_parser("vialcheck-retro", parents=[common])]:
        p.add_argument("--pose", help="results/poses tag of the current camera setup (default s1; R0 rows: deferred)")
        p.add_argument("--poses-dir", default=str(GTC / "results" / "poses"))
        p.add_argument("--intrinsics", default=str(GTC / "config" / "c920_intrinsics.json"))
        p.add_argument("--layouts", default=str(GTC / "config" / "layouts.json"))
        p.add_argument("--measurements", default=str(GTC / "results" / "rig" / "measurements.jsonl"))
        p.add_argument("--vial-method", choices=["iou", "shift"], default="iou",
                       help="iou: B 5.5 as registered; shift: split at the targets, offset in mm (addendum entry 2 draft)")
        p.add_argument("--vial-across-mm", type=float, help="shift: across-axis limit in mm (default real/vial_check.py TH)")
    p = sub.choices["vialcheck-retro"]
    p.add_argument("--cond", default="R0")
    p.add_argument("--redo", action="store_true", help="also records already checked")
    p.add_argument("--mock", action="store_true")
    p = sub.add_parser("reference", parents=[common])
    p.add_argument("--tag", required=True)
    p.add_argument("--frames", type=int, default=20)
    p.add_argument("--source", default="camera:front")
    p.add_argument("--draw", action="store_true")
    p.add_argument("--ignore-rects", help="x0,y0,x1,y1;... (px)")
    p.add_argument("--ignore-from", help="copy the ignore mask of another reference (same camera pose)")
    p.add_argument("--replace", action="store_true")
    p.add_argument("--mock", action="store_true", help="write to the dry-run refs")
    p.add_argument("--note", default="")
    p = sub.add_parser("status", parents=[common])
    p.add_argument("--mock", action="store_true")
    p = sub.add_parser("score", parents=[common], help="score a trial whose score form was not finished")
    p.add_argument("--uid", required=True)
    p.add_argument("--score-json", help="score answers as JSON instead of the form (tests)")
    p.add_argument("--mock", action="store_true")
    a = ap.parse_args(argv)
    a.schedule = Path(a.schedule)
    if a.cmd == "reference":
        return cmd_reference(a)
    if a.cmd == "status":
        return cmd_status(a)
    if a.cmd == "score":
        return cmd_score(a)
    if a.cmd == "vialcheck-retro":
        if not a.pose:
            raise SystemExit("STOP: --pose is required (the R0 PnP tag, e.g. r0)")
        return cmd_vial_retro(a)
    if a.cmd == "next":
        a.pilot = None
    return cmd_run(a, getattr(a, "uid", None))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
