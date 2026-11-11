#!/usr/bin/env python3
"""Blind copies of the judge clips (C 1.4 / 4.2): random codes, shuffled, the key sealed by its hash.

    .venv/bin/python -I tools/blind_rename.py --keys N04B-001_a1 ... | --blocks N04B-R0 [N04-R0 ...] [--batch A]
For every trial key with a judge clip (media/real/judge/clips/<key>.mp4): a random code (6 hex digits) and copies
media/real/judge/blind/<code>.mp4 and, if the trial has one, <code>_wrist.mp4 (its wrist keyframe video; the front
keyframes are not copied, they show the camera pitch). The key (code -> trial) is written to
media/real/judge/blind_key_<utc>.json (git-ignored, not to be opened until blind scoring is done) and its SHA-256 to
results/real/blind_key_<utc>.sha256 (committed). A scoring sheet in shuffled order with C 4.1's columns goes to
results/real/blind_scores_<utc>.csv.
--batch NAME (Nov 9, two blind batches, entry 3): the copies go to media/real/judge/blind/<NAME>/, the key to
media/real/judge/sealed/blind_key_<NAME>_<utc>.json, its SHA-256 to results/real/blind_key_<NAME>_<utc>.sha256 and the
sheet to results/real/blind_scores_<NAME>_<utc>.csv, so each batch has its own folder, codes and sheet.
Exploratory column (addendum entry 2), every trial: tube_contact = none | touched | closed (the gripper never touches a
tube / touches or pushes one without closing on it / closes with a tube between the jaws, lifted or not).
"""
import argparse
import csv
import datetime as dt
import hashlib
import json
import secrets
import shutil
import sys
from pathlib import Path

GTC = Path(__file__).resolve().parents[1]
JUDGE = GTC / "media" / "real" / "judge"
COLS = ["blind_code", "judge", "scored_utc", "outcome", "t_release_s", "hold_2s", "hold_05s", "grasp", "fail_code",
        "tilt_borderline", "confidence", "tube_contact", "note"]


def main(argv):
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--keys", nargs="+")
    g.add_argument("--blocks", nargs="+")
    ap.add_argument("--records", default=str(GTC / "results" / "real" / "trials.jsonl"))
    ap.add_argument("--batch", help="blind batch name: own folder, key and sheet")
    a = ap.parse_args(argv)
    recs = [json.loads(l) for l in open(a.records)]
    if a.blocks:
        keys = [f"{r['uid']}_a{r['attempt']}" for r in recs if r.get("block") in a.blocks and r.get("live_outcome") in ("S", "F")]
    else:
        keys = list(a.keys)
    by = {f"{r['uid']}_a{r['attempt']}": r for r in recs}
    missing = [k for k in keys if not (JUDGE / "clips" / f"{k}.mp4").exists()]
    if missing:
        raise SystemExit(f"STOP: no judge clip for {missing}")
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    codes = set()
    key = {}
    for k in keys:
        c = secrets.token_hex(3)
        while c in codes:
            c = secrets.token_hex(3)
        codes.add(c)
        key[c] = k
    order = sorted(key, key=lambda c: secrets.randbits(64))
    bdir = JUDGE / "blind" / a.batch if a.batch else JUDGE / "blind"
    tag = f"{a.batch}_{stamp}" if a.batch else stamp
    if a.batch and bdir.exists() and any(bdir.iterdir()):
        raise SystemExit(f"STOP: {bdir} is not empty")
    bdir.mkdir(parents=True, exist_ok=True)
    for c in order:
        k = key[c]
        shutil.copyfile(JUDGE / "clips" / f"{k}.mp4", bdir / f"{c}.mp4")
        wr = by.get(k, {}).get("kf_wrist_mp4")
        if wr:
            src = GTC / str(wr).replace("/workspace/gtc/", "")
            if src.exists():
                shutil.copyfile(src, bdir / f"{c}_wrist.mp4")
    kdir = JUDGE / "sealed" if a.batch else JUDGE
    kdir.mkdir(parents=True, exist_ok=True)
    kp = kdir / f"blind_key_{tag}.json"
    kp.write_text(json.dumps({"utc": stamp, "key": key}, indent=1, sort_keys=True))
    h = hashlib.sha256(kp.read_bytes()).hexdigest()
    (GTC / "results" / "real" / f"blind_key_{tag}.sha256").write_text(f"{h}  {kp.relative_to(GTC)}\n")
    with open(GTC / "results" / "real" / f"blind_scores_{tag}.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        for c in order:
            w.writerow({"blind_code": c})
    print(f"{len(order)} blind clips -> {bdir}; key {kp.name} sealed, sha256 {h[:16]}...; "
          f"sheet results/real/blind_scores_{tag}.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
