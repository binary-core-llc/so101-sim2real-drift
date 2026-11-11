#!/usr/bin/env python3
"""Judge clips (C 4.2): one clip per trial from a block's continuous judge-phone video, t_launch - 2 s to t_end + 3 s.

    .venv/bin/python -I tools/cut_judge_clips.py --block N04B-R0 --video media/real/judge/raw/20261108/JUDGE_N04B-R0_x.MOV \
        [--start-utc 2026-11-08T06:30:00Z] [--slate VIDEO_S=UTC] [--no-motion] [--dry-run]
Clock: video time = UTC - start. The start is, in order of preference: --slate (the video time of a filmed UTC clock
and the UTC it shows), --start-utc, or the file's own creation time (ffprobe). Then, unless --no-motion, the start is
refined by motion: at t_launch the arm rises to the start pose (3 s), the first motion after at least 4 s of stillness
in the judge view. For every trial the onset is searched within +-20 s (--scan-s) of where the clock puts it; the median of
(onset - t_launch) over the trials corrects the start, and every trial's residual is logged (a residual above 1.5 s
is flagged). Trials without t_launch (a rebuilt record) are cut from the corrected clock with their file times.
A recording that stops inside the 3 s post-roll is cut to its end (post_roll_s logged); one that starts inside the 2 s
lead or during the 3 s rise is cut from its start (pre_roll_s logged, negative if after t_launch; Nov 9, G1's per-trial
recordings). --still-s (default 4) sets the stillness the onset needs and --scan-s (default 20) the search window;
per-trial recordings that start a few seconds before the launch use 1 and 8 (a 40 s window there is mostly policy
motion, which lifts the noise threshold above the rise). Phone portrait videos: the rotation flag is read so the motion scan sees upright frames.
Clips are re-encoded (frame-accurate cuts) to media/real/judge/clips/<uid>_a<n>.mp4; the log goes to
results/real/judge_clips_<block>.json.
"""
import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

GTC = Path(__file__).resolve().parents[1]
FPS_SCAN, W_SCAN = 10, 160
RISE_S = 3.0                                               # t_launch: the arm rises to the start pose


def utc(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def probe(video):
    out = json.loads(subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams",
                                     str(video)], capture_output=True, text=True, check=True).stdout)
    tags = {**out["format"].get("tags", {}), **next((s.get("tags", {}) for s in out["streams"] if s.get("codec_type") == "video"), {})}
    created = tags.get("com.apple.quicktime.creationdate") or tags.get("creation_time")
    return float(out["format"]["duration"]), created, tags


def rotation(video):
    """The video stream's display rotation in degrees (side data, else the old 'rotate' tag), 0 if none."""
    out = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_streams", "-of", "json",
                                     str(video)], capture_output=True, text=True, check=True).stdout)["streams"][0]
    for sd in out.get("side_data_list", []):
        if "rotation" in sd:
            return int(round(float(sd["rotation"])))
    return int(out.get("tags", {}).get("rotate", 0))


def motion(video, t0, dur):
    """(times, motion energy) at FPS_SCAN between video seconds t0 and t0 + dur (grey, 160 px wide)."""
    t0 = max(0.0, t0)
    h = None
    p = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t0:.3f}", "-t", f"{dur:.3f}", "-i", str(video), "-vf",
                        f"fps={FPS_SCAN},scale={W_SCAN}:-2,format=gray", "-f", "rawvideo", "-"], capture_output=True, check=True)
    p2 = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                         "-of", "json", str(video)], capture_output=True, text=True, check=True)
    s = json.loads(p2.stdout)["streams"][0]
    w_, h_ = s["width"], s["height"]
    if rotation(video) % 180 == 90:                            # phone portrait video: ffmpeg auto-rotates the frames
        w_, h_ = h_, w_
    h = int(round(h_ * W_SCAN / w_ / 2) * 2)
    fr = np.frombuffer(p.stdout, np.uint8)
    n = len(fr) // (W_SCAN * h)
    fr = fr[:n * W_SCAN * h].reshape(n, h, W_SCAN).astype(np.float32)
    e = np.r_[0.0, np.abs(np.diff(fr, axis=0)).mean(axis=(1, 2))]
    return t0 + np.arange(n) / FPS_SCAN, e


def onset(times, e, expect, still_s=4.0):
    """First rise above the noise after >= still_s of stillness, nearest to `expect`."""
    noise = np.median(e) + 3 * 1.4826 * np.median(np.abs(e - np.median(e)))
    thr = max(noise, 1.0)
    quiet = e < thr
    k = int(still_s * FPS_SCAN)
    cands = [times[i] for i in range(k, len(e)) if e[i] >= thr and quiet[i - k:i].all()]
    return min(cands, key=lambda t: abs(t - expect)) if cands else None


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--block", required=True)
    ap.add_argument("--video", required=True)
    ap.add_argument("--start-utc")
    ap.add_argument("--slate", help="VIDEO_S=UTC: the video second at which the filmed clock shows UTC")
    ap.add_argument("--no-motion", action="store_true")
    ap.add_argument("--still-s", type=float, default=4.0, help="stillness before the motion onset (s)")
    ap.add_argument("--scan-s", type=float, default=20.0, help="onset search window, +- s around the clock's t_launch")
    ap.add_argument("--out-dir", default=str(GTC / "media" / "real" / "judge" / "clips"))
    ap.add_argument("--records", default=str(GTC / "results" / "real" / "trials.jsonl"))
    ap.add_argument("--log", default=None)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    video = Path(a.video)
    dur, created, tags = probe(video)
    if a.slate:
        vs, u = a.slate.split("=", 1)
        start, source = utc(u) - dt.timedelta(seconds=float(vs)), "slate"
    elif a.start_utc:
        start, source = utc(a.start_utc), "given"
    elif created:
        start, source = utc(created), "file creation time"
    else:
        raise SystemExit("STOP: no slate, no --start-utc and no creation time in the file")
    recs = [json.loads(l) for l in open(a.records)]
    recs = [r for r in recs if r.get("block") == a.block]
    if not recs:
        raise SystemExit(f"STOP: no records of block {a.block}")
    vt = lambda u: (utc(u) - start).total_seconds()
    resid = {}
    if not a.no_motion:
        for r in recs:
            if not r.get("t_launch"):
                continue
            exp = vt(r["t_launch"])
            if not (0 <= exp <= dur):
                continue
            t, e = motion(video, exp - a.scan_s, 2 * a.scan_s)
            o = onset(t, e, exp, a.still_s)
            if o is not None:
                resid[f"{r['uid']}_a{r['attempt']}"] = o - exp
        if resid:
            corr = float(np.median(list(resid.values())))     # motion later in the video than the clock says:
            start = start - dt.timedelta(seconds=corr)         # the video started earlier than assumed
            resid = {k: round(v - corr, 2) for k, v in resid.items()}
        else:
            corr = None
    else:
        corr = None
    log = {"block": a.block, "video": str(video), "duration_s": dur, "start_source": source,
           "start_utc": start.isoformat(), "motion_correction_s": corr, "creation_tags": tags, "clips": []}
    Path(a.out_dir).mkdir(parents=True, exist_ok=True)
    for r in recs:
        key = f"{r['uid']}_a{r['attempt']}"
        rr = r.get("record_recovery", {}).get("times_from_files", {})
        t_from = r.get("t_launch") or rr.get("first_keyframe_saved")
        t_to = r.get("t_end") or rr.get("post_front_saved")
        if not (t_from and t_to):
            log["clips"].append({"key": key, "error": "no times"})
            continue
        lead = 2.0 if r.get("t_launch") else 8.0              # a rebuilt record starts at T0, not at the launch
        s, e_ = vt(t_from) - lead, vt(t_to) + 3.0
        item = {"key": key, "video_from_s": round(s, 2), "video_to_s": round(e_, 2), "residual_s": resid.get(key),
                "flag": bool(resid.get(key) is not None and abs(resid[key]) > 1.5), "rebuilt_times": not r.get("t_launch")}
        if s < 0 and r.get("t_launch") and vt(t_from) + RISE_S > 0 and vt(t_to) <= dur:   # started in the lead or the rise
            item.update(video_from_s=0.0, pre_roll_s=round(vt(t_from), 2))
            s = 0.0
        if 0 <= s and vt(t_to) <= dur < e_:                   # the recording stopped inside the 3 s post-roll
            e_ = dur
            item.update(video_to_s=round(e_, 2), post_roll_s=round(dur - vt(t_to), 2))
        if not (0 <= s and e_ <= dur):
            item["error"] = "outside the video"
        elif not a.dry_run:
            out = Path(a.out_dir) / f"{key}.mp4"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{s:.3f}", "-to", f"{e_:.3f}", "-i", str(video), "-c:v",
                            "libx264", "-preset", "veryfast", "-crf", "20", "-an", str(out)], check=True)
            item["clip"] = str(out)
        log["clips"].append(item)
        print(f"{key}: {s:8.2f} -> {e_:8.2f} s" + (f"  residual {resid[key]:+.2f} s" if key in resid else "")
              + ("  FLAG" if item["flag"] else "") + (f"  {item['error']}" if "error" in item else ""))
    lp = Path(a.log) if a.log else GTC / "results" / "real" / f"judge_clips_{a.block}.json"
    lp.write_text(json.dumps(log, indent=1, default=str))
    print(f"start {start.isoformat()} ({source}" + (f", motion {corr:+.2f} s" if corr is not None else "") + f") -> {lp}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
