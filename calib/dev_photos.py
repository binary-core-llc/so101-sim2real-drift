#!/usr/bin/env python3
"""E3 development photos (D_software C17 DEV set; B section 7, simplified per E_premortem G14).

    .venv/bin/python -I calib/dev_photos.py --id D01 --desc "S1 camera, rack nominal, layout L00" --layout L00 \
        [--rack-x-cm 0 --rack-y-cm 0 --rack-yaw-deg 0] [--square-mm 29.97] [--check]
Per photo: (1) board and hands out of view -> the clean photo (3 frames, frame 2 is the photo);
(2) board sled placed -> 20 frames -> camera pose by ChArUco = the ground truth (pose.py; needs
config/c920_intrinsics.json, else the frames are kept and the pose is computed later with --recompute);
(3) with --check (every 4th photo, G14) the board comes off and back on for a second 20-frame measurement.
Files: media/photoset_dev/raw/<id>/clean_0..2.png, board_after_000..019.png [, board_check_*],
media/photoset_dev/undist/<id>_clean_undist.png (centred pinhole, C920x fx, B 3.6), and
results/photoset_dev/<id>.json (description, intended offsets, GT pose, lock readback, camera identity, hashes).
"""
import argparse
import datetime as dt
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))  # sibling modules (python -I skips the script dir)

import camera_lock  # noqa: E402
import capture  # noqa: E402
import charuco as C  # noqa: E402
import pose  # noqa: E402

GTC = Path(__file__).resolve().parents[1]


def sha(p):
    p = Path(p)
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None


def ask(msg, yes):
    if yes:
        print(f"  {msg} [auto]")
    else:
        input(f"  {msg} - press Enter ")


def grab(src, n):
    return [src.read() for _ in range(n)]


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True)
    ap.add_argument("--desc", required=True)
    ap.add_argument("--layout", default=None)
    ap.add_argument("--rack-x-cm", type=float, default=0.0)
    ap.add_argument("--rack-y-cm", type=float, default=0.0)
    ap.add_argument("--rack-yaw-deg", type=float, default=0.0)
    ap.add_argument("--camera-label", default="S1")
    ap.add_argument("--square-mm", type=float, default=30.0)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--source", default="camera:front")
    ap.add_argument("--clean-source", default=None, help="test only")
    ap.add_argument("--board-source", default=None, help="test only")
    ap.add_argument("--intrinsics", default=str(pose.INTR))
    ap.add_argument("--board-in-e", default=str(pose.BOARD))
    ap.add_argument("--yes", action="store_true", help="do not wait for Enter (tests)")
    ap.add_argument("--out-root", default=str(GTC), help="test only: where results/ and media/ go")
    a = ap.parse_args(argv)
    MEDIA, RES = Path(a.out_root) / "media" / "photoset_dev", Path(a.out_root) / "results" / "photoset_dev"
    raw = MEDIA / "raw" / a.id
    if (RES / f"{a.id}.json").exists():
        raise SystemExit(f"STOP: {a.id} already exists; use a new --id")
    lock_ok = None
    if a.source.startswith("camera:"):
        lock_ok = camera_lock.cmd_apply(a.source.split(":", 1)[1], write=False) == 0
        if not lock_ok:
            raise SystemExit("STOP: camera lock does not read back; run camera_lock.py apply front")
    src_clean = capture.open_source(a.clean_source or a.source)
    src_board = capture.open_source(a.board_source) if a.board_source else src_clean
    try:
        ask("Board, sled, hands and tools OUT of the camera view; wait 2 s", a.yes)
        clean = grab(src_clean, 3)
        ask("Place the board sled (seated on both lobes); hands out", a.yes)
        after = grab(src_board, 20)
        check = None
        if a.check:
            ask("Lift the sled off, then place it back (check measurement)", a.yes)
            check = grab(src_board, 20)
        ident = src_clean.identity
    finally:
        src_clean.close()
        if src_board is not src_clean:
            src_board.close()
    for i, f in enumerate(clean):
        capture.save_rgb(raw / f"clean_{i}.png", f)
    for i, f in enumerate(after):
        capture.save_rgb(raw / f"board_after_{i:03d}.png", f)
    for i, f in enumerate(check or []):
        capture.save_rgb(raw / f"board_check_{i:03d}.png", f)
    rec = {"photo_id": a.id, "set": "DEV", "captured_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "operator": "AMR", "description": a.desc, "camera_label": a.camera_label,
           "intended": {"rack_delta": {"x_m": a.rack_x_cm / 100, "y_m": a.rack_y_cm / 100, "yaw_deg": a.rack_yaw_deg}},
           "vials": {"layout_id": a.layout}, "camera": ident, "camera_lock_readback_ok": lock_ok,
           "files": {"clean": f"media/photoset_dev/raw/{a.id}/clean_1.png"}, "square_mm": a.square_mm,
           "refs": {"intrinsics_sha256": sha(a.intrinsics), "board_in_E_sha256": sha(a.board_in_e),
                    "camera_lock_sha256": sha(GTC / "config" / "camera_lock.json"),
                    "code_git": subprocess.run(["git", "-C", str(GTC), "rev-parse", "HEAD"], capture_output=True,
                                               text=True).stdout.strip()}}
    if Path(a.intrinsics).exists():
        K, dist, _ = pose.load_K(a.intrinsics)
        T_E_K = C.board_in_E(a.board_in_e)[0] if Path(a.board_in_e).exists() else None
        gt = pose.measure_frames(after, K, dist, a.square_mm, T_E_K)
        rec["gt"] = {"camera_pose": gt, "frame": "E" if T_E_K is not None else "board (no board_in_E.json)"}
        if check:
            gc = pose.measure_frames(check, K, dist, a.square_mm, T_E_K)
            d = pose.diff(gt, gc)
            rec["gt"]["check"] = {"agree_pos_mm": 1000 * float(np.linalg.norm([d["lateral_m"], d["depth_m"], d["height_m"]])),
                                  "agree_rot_deg": d["rotation_total_deg"]}
        fx = K[0, 0]
        Kp = np.array([[fx, 0, 320], [0, fx, 240], [0, 0, 1.0]])
        maps = cv2.initUndistortRectifyMap(K, dist, None, Kp, (640, 480), cv2.CV_32FC1)
        capture.save_rgb(MEDIA / "undist" / f"{a.id}_clean_undist.png", cv2.remap(clean[1], *maps, cv2.INTER_LINEAR))
        rec["files"]["undist"] = f"media/photoset_dev/undist/{a.id}_clean_undist.png"
        rec["undistort_Kp"] = Kp.tolist()
    else:
        rec["gt"] = None
        rec["note"] = "no intrinsics yet: board frames kept; compute the ground truth later"
    RES.mkdir(parents=True, exist_ok=True)
    (RES / f"{a.id}.json").write_text(json.dumps(rec, indent=1))
    g = (rec.get("gt") or {}).get("camera_pose")
    print(f"{a.id}: clean photo + {len(after)} board frames saved; GT "
          + (f"RMS {g['rms_px']:.3f} px, {g['n_corners']} corners" if g else "pending (no intrinsics)")
          + (f"; check agrees {rec['gt']['check']['agree_pos_mm']:.2f} mm / {rec['gt']['check']['agree_rot_deg']:.3f} deg"
             if g and check else "") + f" -> results/photoset_dev/{a.id}.json")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
