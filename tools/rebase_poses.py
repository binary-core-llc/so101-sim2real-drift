#!/usr/bin/env python3
"""Re-express saved ChArUco poses in E with the current config/board_in_E.json (after the sled datums improve).

    .venv/bin/python -I tools/rebase_poses.py --tags r0_p1 r0_p2 r0_p3 r0_p4 r0_p5 [--board-in-e config/board_in_E.json]
    then re-run: .venv/bin/python -I calib/pose.py mean --tags r0_p1 ... --out r0

Every pose record keeps the board-frame pose (R_K_cv, C_K_m) from the 20-frame solve, so the E fields (C_E_m, R_E_cv,
quaternions, angles, board_in_E and its sha256) are recomputed exactly as calib/charuco.pose_record makes them; the
solve itself, the frames and the board-frame pose are untouched. An audit copy <tag>.json.pre-rebase-<UTC> is kept
next to each record, and the record gets a "rebased" entry (UTC, old and new board_in_E sha256).
Mean records (pose.py mean) are not rebased: re-run mean on the rebased placements.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "calib"))  # python -I skips the script dir

import charuco as C  # noqa: E402

GTC = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get("GTC_POSES_DIR", GTC / "results" / "poses"))   # same override as calib/pose.py
E_KEYS = ("C_E_m", "R_E_cv", "q_wxyz_cv", "q_wxyz_usd", "angles")


def rebase(rec, T_E_K, board, board_sha):
    if "mean_of" in rec:
        raise SystemExit(f"STOP: {rec.get('tag')} is a mean record; rebase its placements and re-run pose.py mean")
    T_K_cv = C.T(np.array(rec["R_K_cv"]), rec["C_K_m"])
    new = C.pose_record({"T_cv_K": np.linalg.inv(T_K_cv), "rms_px": rec["rms_px"], "n_corners": rec["n_corners"]}, T_E_K)
    out = dict(rec)
    out.pop("angles_board_frame", None)
    out.update({k: new[k] for k in E_KEYS})
    out.update({"board_in_E": board, "board_in_E_sha256": board_sha,
                "rebased": {"utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                            "from_board_in_E_sha256": rec.get("board_in_E_sha256"), "to_board_in_E_sha256": board_sha}})
    return out


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--tags", nargs="+", required=True)
    ap.add_argument("--board-in-e", default=str(GTC / "config" / "board_in_E.json"))
    a = ap.parse_args(argv)
    T_E_K, board = C.board_in_E(a.board_in_e)
    board_sha = hashlib.sha256(Path(a.board_in_e).read_bytes()).hexdigest()
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for tag in a.tags:
        p = OUT / f"{tag}.json"
        if not p.exists():
            raise SystemExit(f"STOP: no pose {p}")
        rec = json.loads(p.read_text())
        if rec.get("board_in_E_sha256") == board_sha:
            print(f"{tag}: already on this board_in_E.json, unchanged")
            continue
        out = rebase(rec, T_E_K, board, board_sha)
        shutil.copy2(p, p.with_name(f"{p.name}.pre-rebase-{stamp}"))
        p.write_text(json.dumps(out, indent=1))
        c0, c1 = rec.get("C_E_m"), out["C_E_m"]
        moved = (f"lens moved {1000 * np.linalg.norm(np.subtract(c1, c0)):.2f} mm" if c0 else "was in the board frame")
        g = out["angles"]
        print(f"{tag}: C_E ({c1[0]:.4f}, {c1[1]:.4f}, {c1[2]:.4f}) m, depression {g['depression_deg']:.2f}, heading "
              f"{g['heading_deg']:.2f}, roll {g['roll_deg']:.2f} deg ({moved})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
