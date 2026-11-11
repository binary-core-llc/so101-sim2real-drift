#!/usr/bin/env python3
"""Write a trial record that the runner lost after the trial ran (e.g. Ctrl+C in the score form), from what is on disk.

    .venv/bin/python -I tools/recover_trial_record.py --uid N04B-002 --attempt 1 --gtc-commit <sha at run time> \
        --score-json '{"outcome": "F", "fail_code": "F5", "flags": "wall_contact", "note": "..."}' \
        --end-reason safety_key --reason "..." [--dry-run]
Rebuilt with the runner's own functions: the pre-trial checks (run_checks on the saved pre_front.png against the
block reference), the tubes-present / vial fields (vial_step), the post-trial mat check (mat_check on post_front.png),
chunk / action / latency / period statistics from the step log (as the runner sums them), the freeze check from the
lossless keyframes, file hashes and the schedule row. Fields only the runner held in memory (camera-lock readbacks at
connect and end, servo temperatures, the start-pose reading, ping, the exact t_enter / t_launch / key time / run_s, the
END line) are null and listed in record_recovery.not_recoverable; times rebuilt from file times are listed as such.
The trial keeps its uid and attempt (it is not re-run, C 1.5). An audit copy of trials.jsonl is kept.
"""
import argparse
import datetime as dt
import json
import shutil
import sys
import tempfile
import types
from pathlib import Path

import numpy as np

GTC = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(GTC / "calib"), str(GTC / "real")]

import capture  # noqa: E402
import calib_report  # noqa: E402
import trial_runner as T  # noqa: E402


def cpath(p):
    """A path as the runner records it (inside the container)."""
    return "/workspace/gtc/" + str(Path(p).resolve().relative_to(GTC))


def mtime_utc(p):
    return dt.datetime.fromtimestamp(Path(p).stat().st_mtime, dt.timezone.utc).isoformat(timespec="milliseconds")


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--uid", required=True)
    ap.add_argument("--attempt", type=int, required=True)
    ap.add_argument("--gtc-commit", required=True, help="the gtc HEAD when the trial ran (git log)")
    ap.add_argument("--score-json", required=True)
    ap.add_argument("--end-reason", required=True, choices=sorted(set(T.END.values()) | {"cap"}))
    ap.add_argument("--reason", required=True, help="why the runner did not write the record")
    ap.add_argument("--operator", default="AMR")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    res_dir, media_root, refs = T.kind_dirs(GTC, "real")
    path = res_dir / "trials.jsonl"
    recs = T.load_records(path)
    if any(r["uid"] == a.uid and r["attempt"] == a.attempt for r in recs):
        raise SystemExit(f"STOP: {a.uid} attempt {a.attempt} already has a record")
    rows = T.load_schedule(GTC / "config" / "schedule.csv")
    row = next(r for r in rows if r["uid"] == a.uid)
    key = f"{a.uid}_a{a.attempt}"
    media, steps_path = media_root / key, res_dir / "steps" / f"{key}.jsonl"
    tag = f"{row['block']}_{row['cond']}"
    same_block = [r for r in recs if r.get("block") == row["block"] and r.get("kind") == "real"]
    if not same_block:
        raise SystemExit("STOP: no complete record of the same block to take the run settings from")
    ref_rec = same_block[-1]
    pre = [r for r in (json.loads(l) for l in open(res_dir / "prestart.jsonl")) if r["uid"] == a.uid]
    rec = {"uid": row["uid"], "attempt": a.attempt, "rerun_of": f"{row['uid']}_a{a.attempt - 1}" if a.attempt > 1 else None,
           "day": row["day"], "actual_date": dt.datetime.fromtimestamp(steps_path.stat().st_mtime, T.PST).date().isoformat(),
           "block": row["block"], "cond": row["cond"], "method": row["method"], "cycle": row["cycle"],
           "layout": row["layout"], "schedule_note": row.get("note"), "operator": a.operator, "kind": "real",
           "mock_robot": False, "ref_tag": tag, "checks_mode": ref_rec["checks_mode"], "check_thresholds": T.CHECKS,
           "instruction": T.LANG, "action_horizon": T.HORIZON, "cap_s": T.CAP_S, "policy_timeout_s": T.TIMEOUT_S,
           "model_path": ref_rec["model_path"], "schedule": ref_rec["schedule"],
           "schedule_sha256": T.sha256(GTC / "config" / "schedule.csv"), "runner_sha256": T.sha256(GTC / "real" / "trial_runner.py"),
           "pilot_sha256": T.sha256(GTC / "real" / "pilot.py"), "gtc_commit": a.gtc_commit, "groot_ref": ref_rec.get("groot_ref"),
           "course_commit": None}
    for k in ("model_path", "groot_ref", "checks_mode"):
        if pre and pre[-1].get(k) not in (None, rec[k]):
            raise SystemExit(f"STOP: {k} differs between the block's records and this row's prestart entry")
    if pre:
        rec.update({k: pre[-1].get(k) for k in ("front_dev", "wrist_dev", "follower_dev")})
    pre_front = capture.load_rgb(media / "pre_front.png")
    rec["pre_front"], rec["pre_wrist"] = cpath(media / "pre_front.png"), cpath(media / "pre_wrist.png")
    rec["checks"], _ = T.run_checks(refs / tag, pre_front, T.CHECKS)
    c = rec["checks"]
    rec.update({"cleanview_pass": c["clean_view"]["pass"], "cleanview_score": c["clean_view"]["score_px"],
                "light_ratio": c["light"]["ratio"], "drift_px": c["drift"]["max_px"], "drift_deg": c["drift"]["rot_deg"],
                "rack_centroid_err_px": c["rack"].get("centroid_err_px"), "rack_rot_deg": c["rack"].get("rot_deg"),
                "mat_shift_px": c["mat"].get("max_abs_px")})
    va = types.SimpleNamespace(measurements=str(GTC / "results" / "rig" / "measurements.jsonl"), pose=None,
                               poses_dir=str(GTC / "results" / "poses"), intrinsics=str(GTC / "config" / "c920_intrinsics.json"),
                               layouts=str(GTC / "config" / "layouts.json"))
    scratch = Path(tempfile.mkdtemp(prefix=f"recover_{key}_"))
    rec.update(T.vial_fields(T.vial_step(va, row["cond"], row["layout"], refs / tag, pre_front, scratch)))
    rec["calib_sha256"] = T.sha256(Path.home() / f".cache/huggingface/lerobot/calibration/robots/so101_follower/{calib_report.env_ids()[0]}.json")
    chunks = [json.loads(l) for l in open(steps_path)]
    lat = np.array([ch["latency_s"] for ch in chunks]) * 1000
    periods = [1000 * (b - x) for ch in chunks for x, b in zip(ch["send_t_s"], ch["send_t_s"][1:])]
    runs, last, max_run = {}, {}, {}
    for i in range(len(chunks)):
        for cam in ("front", "wrist"):
            h = hash(capture.load_rgb(media / "kf" / f"chunk_{i:03d}_{cam}.png").tobytes())
            runs[cam] = runs.get(cam, 0) + 1 if h == last.get(cam) else 1
            last[cam], max_run[cam] = h, max(max_run.get(cam, 0), runs[cam])
    last_send = chunks[-1]["send_t_s"][-1] if chunks[-1]["send_t_s"] else chunks[-1]["t_reply_s"]
    stopped_by_key = chunks[-1]["sent"] < len(chunks[-1]["actions"]) and last_send < T.CAP_S
    rec["start_joints"] = None
    rec.update({"end_reason": a.end_reason, "end_detail": None, "key_t_s": None,
                "chunk_at_key": len(chunks) - 1 if a.end_reason != "cap" else None, "run_s": None,
                "n_chunks": len(chunks), "n_actions": sum(ch["sent"] for ch in chunks),
                "keyframes_written": len(chunks), "lat_ms_med": float(np.median(lat)), "lat_ms_p95": float(np.percentile(lat, 95)),
                "lat_ms_max": float(lat.max()), "n_lat_gt_1s": int((lat > 1000 * T.LAT_INVALID_S).sum()),
                "act_period_ms_med": float(np.median(periods)) if periods else None,
                "act_period_ms_p95": float(np.percentile(periods, 95)) if periods else None,
                "max_identical_keyframes": max_run, "steps_jsonl": cpath(steps_path),
                "kf_dir": cpath(media / "kf"), "kf_front_mp4": cpath(media / "kf_front.mp4"),
                "kf_wrist_mp4": cpath(media / "kf_wrist.mp4"),
                "post_front": cpath(media / "post_front.png")})
    rec["mat_post"] = T.mat_check(capture.load_rgb(refs / tag / "ref_front_median.png"), capture.load_rgb(media / "post_front.png"), T.CHECKS,
                                  ignore=T.ref_ignore(refs / tag))
    rec["mat_shift_post_px"] = rec["mat_post"].get("max_abs_px")
    auto = []
    if max(max_run.values()) >= T.FREEZE_N:
        auto.append("I1")
    if rec["n_lat_gt_1s"]:
        auto.append("I3")
    if rec["model_path"] != T.PREREG_MODEL:
        auto.append("I6")
    rec["auto_invalid"] = auto
    for k in ("t_enter", "t_launch", "t0_first_query", "t_end", "temp_pre", "temp_post", "lock_pre", "lock_after_open",
              "lock_reapplied", "lock_writes", "lock_end", "ping_s"):
        rec[k] = None
    score = json.loads(a.score_json)
    rec.update(T.score_form({}, score))
    rec["record_recovery"] = {
        "utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "by": "tools/recover_trial_record.py",
        "reason": a.reason,
        "rebuilt": ["run settings and hashes (schedule row, runner/pilot/schedule sha256 now, unchanged since the run; gtc "
                    "commit at run time given)", "pre-trial checks (run_checks on pre_front.png vs " + tag + ")",
                    "tubes-present and vial fields (vial_step)", "post-trial mat check (mat_check on post_front.png)",
                    "chunk, action, latency and period statistics (step log)", "freeze check (lossless keyframes)",
                    "calibration file sha256 (now)", "devices (this row's prestart entry; same USB identities)" if pre else
                    "devices: not recoverable"],
        "end_reason_source": f"operator: '{a.end_reason}' key pressed; the step log stops mid-chunk at {last_send:.2f} s "
                             f"({'consistent' if stopped_by_key else 'NOT consistent'} with a key stop before the {T.CAP_S} s cap)",
        "times_from_files": {"pre_front_saved": mtime_utc(media / "pre_front.png"),
                             "first_keyframe_saved": mtime_utc(media / "kf" / "chunk_000_front.png"),
                             "last_send_after_t0_s": round(last_send, 2),
                             "steps_log_closed": mtime_utc(steps_path), "post_front_saved": mtime_utc(media / "post_front.png")},
        "not_recoverable": ["the END line (end detail, AUTO-FLAGS as printed)", "camera-lock readbacks at preflight, after the "
                            "stream opened and at the end (so I4 cannot be evaluated)", "servo temperatures before and after",
                            "the start-pose joint reading", "server ping time", "exact t_enter, t_launch, t0_first_query, "
                            "t_end, key_t_s and run_s (file times above instead)"]}
    if not stopped_by_key and a.end_reason != "cap":
        raise SystemExit("STOP: the step log does not end like a key stop; check the end reason")
    print(json.dumps({k: rec[k] for k in ("uid", "attempt", "live_outcome", "live_fail_code", "flags", "note", "end_reason",
                                          "n_chunks", "n_actions", "drift_px", "cleanview_pass", "light_ratio",
                                          "rack_centroid_err_px", "mat_shift_px", "mat_shift_post_px", "auto_invalid",
                                          "max_identical_keyframes")}, default=str, indent=1))
    print(json.dumps(rec["record_recovery"]["times_from_files"], indent=1), rec["record_recovery"]["end_reason_source"])
    if a.dry_run:
        print("dry run: nothing written")
        return 0
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    shutil.copy2(path, path.with_name(f"trials.jsonl.pre-recover-{a.uid.lower()}-{stamp}"))
    T.write_record(res_dir, rec)
    print(f"RECORD {key}: {rec['live_outcome']} {rec['live_fail_code'] or ''} written (recovered) -> {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
