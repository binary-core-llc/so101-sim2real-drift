#!/usr/bin/env python3
"""Camera pose by ChArUco (B section 4.4), for R0 and for the mount's tilt/roll reach.

    .venv/bin/python -I calib/pose.py measure --tag r0_p1 --square-mm 29.97 [--note lens_height_cm=40.0 ...]
    .venv/bin/python -I calib/pose.py mean --tags r0_p1 r0_p2 r0_p3 r0_p4 r0_p5 --out r0     # 5 placements
    .venv/bin/python -I calib/pose.py diff r0 tilt_max                # b - a in B 1.3 terms (board untouched)
    .venv/bin/python -I calib/pose.py hud [--ref s1]                  # live absolute angles (+ delta to a saved pose)
    .venv/bin/python -I calib/pose.py hud --target s1 --square-mm 29.97   # six errors to the S1 target (step C5)
    .venv/bin/python -I calib/pose.py hud --base s1 --offset tilt_down_deg=6 --tol-mm 2 --tol-deg 0.3   # R4 from R1
    .venv/bin/python -I calib/pose.py reach tilt_max                  # absolute depression vs 67.3 / 69.3 deg
    .venv/bin/python -I calib/pose.py note r0 course_35cm_measured_cm=35.4 ...   # add tape/gauge readings

measure: lock read back, 20 frames, corners averaged per ID (IDs in >= 15 frames), solvePnP IPPE + LM with
config/c920_intrinsics.json; reprojection RMS must be <= 0.30 px (else redo). With config/board_in_E.json
(B 4.2 sled) the pose is in the sim frame E: centre C_E, R_E_cv, quaternions (CV and USD camera), depression,
heading, roll. Without it the pose is in the board frame only, and diff/hud work relative to that frame (enough
for the tilt and roll reach, since the board is not touched between the two measurements).
Writes results/poses/<tag>.json and the raw frames to media/poses/<tag>/.
hud --target s1: the target is the sim's render point (build decision D4), the Camera_OmniVision_OV9782_Right
prim in the C1 dump (results/c1/frames_sim.json), all DR at centre. Needs config/board_in_E.json. Shows the six
errors (measured - target, B 1.3 terms) and the move that removes each; green within E_premortem row 22
(<= 3 mm per axis, <= 0.5 deg per angle; aim <= 0.3 deg).
hud --base TAG: the target is a saved pose in E (results/poses/TAG.json, e.g. the X2 mean s1 or a cycle's GT).
--offset KEY=VALUE (repeatable) moves either target by B 1.3 terms, the same keys and signs as diff: tilt_down_deg,
pan_deg, roll_deg, depth_mm (+ toward the back wall), lateral_mm (+ toward the camera wall), height_mm (+ up).
--tol-mm / --tol-deg set the green band (default E row 22); the camera is set without the angle gauge (Nov 5).
hud --ghost (with --target or --base): on the live image, the board's outline and corner squares as the target pose
would see them (green), the live board the same way (magenta; the printed top-left square half filled in both), and
one arrow from the live board's centre: where the board moves when the largest correction (against its band) alone
is made, with that move in words. Line magenta up on green by eye; the six numbers in the panel stay the judge.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))  # sibling modules (python -I skips the script dir)

import camera_lock  # noqa: E402
import capture  # noqa: E402
import charuco as C  # noqa: E402
import live  # noqa: E402

GTC = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get("GTC_POSES_DIR", GTC / "results" / "poses"))   # override: dry runs only
INTR = GTC / "config" / "c920_intrinsics.json"
BOARD = GTC / "config" / "board_in_E.json"
FRAMES_SIM = GTC / "results" / "c1" / "frames_sim.json"
MAX_RMS = 0.30
TOL_MM, TOL_DEG, AIM_DEG = 3.0, 0.5, 0.3          # E_premortem row 22 (R1 nominal; aim <= 0.3 deg)
# S1 by tape (step C1, decision D4), as rounded there: (value, half of the last digit)
S1_TAPE = {"height_above_floor_cm": (46.05, 0.005), "from_front_edge_cm": (23.96, 0.005),
              "from_left_wall_cm": (5.17, 0.005), "depression_deg": (54.3, 0.05), "roll_deg": (1.6, 0.05),
              "pan_toward_back_wall_deg": (8.8, 0.05)}
# error key, label, scale to the unit, unit, tolerance, move when the error is + / when it is -
AXES = (("depth_m", "x", 1000, "mm", TOL_MM, "move {:.1f} mm toward the open front", "move {:.1f} mm toward the back wall"),
        ("lateral_m", "y", 1000, "mm", TOL_MM, "move {:.1f} mm away from the camera wall", "move {:.1f} mm toward the camera wall"),
        ("height_m", "z", 1000, "mm", TOL_MM, "move {:.1f} mm down", "move {:.1f} mm up"),
        ("tilt_down_deg", "tilt", 1, "deg", TOL_DEG, "tilt {:.2f} deg up", "tilt {:.2f} deg down"),
        ("pan_deg", "pan", 1, "deg", TOL_DEG, "pan {:.2f} deg toward the open front", "pan {:.2f} deg toward the back wall"),
        ("roll_deg", "roll", 1, "deg", TOL_DEG, "roll {:.2f} deg counter-clockwise (from behind)",
         "roll {:.2f} deg clockwise (from behind)"))


def sha(p):
    p = Path(p)
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None


def load_K(path):
    j = json.loads(Path(path).read_text())
    return np.array(j["K"]), np.array(j["dist"]), j


def measure_frames(frames, K, dist, square_mm, T_E_K=None):
    det = C.Detector(square_mm)
    dets = [det.detect(f) for f in frames]
    avg = C.average_corners(dets, min_frac=0.75)
    if avg is None or len(avg["ids"]) < 6:
        raise SystemExit("STOP: the board is not seen in enough frames (hands, arm or glare in the way?)")
    sol = C.solve_pose(avg, K, dist)
    rec = C.pose_record(sol, T_E_K)
    per = []
    for d in dets:                                   # per-frame poses: the noise floor (B 4.4 step 4)
        if d is not None and len(d["ids"]) >= 6:
            s = C.solve_pose(d, K, dist)
            if s:
                per.append(np.linalg.inv(s["T_cv_K"]))
    if per:
        P = np.array([p[:3, 3] for p in per])
        rec["frame_sd_pos_mm"] = float(1000 * P.std(0).max())
        rec["frame_sd_rot_deg"] = float(np.std([C.angle_between(per[0][:3, :3], p[:3, :3]) for p in per]))
    rec.update({"n_frames": len(frames), "n_frames_detected": avg["n_frames"], "corner_ids": avg["ids"].tolist(),
                "corner_frame_sd_px": avg["frame_sd_px"], "rms_ok": rec["rms_px"] <= MAX_RMS})
    return rec


def frame_E(rec):
    """R_E_cv and C_E: real E when board_in_E was known, else the board frame laid flat (R_E_K = diag(1,-1,-1))."""
    if "R_E_cv" in rec:
        return np.array(rec["R_E_cv"]), np.array(rec["C_E_m"]), "E"
    F = np.diag([1.0, -1.0, -1.0])
    return F @ np.array(rec["R_K_cv"]), F @ np.array(rec["C_K_m"]), "board (no board_in_E.json)"


def diff(a, b):
    Ra, Ca, fa = frame_E(a)
    Rb, Cb, fb = frame_E(b)
    pa = {"angles": C.angles(Ra), "C_E_m": Ca.tolist(), "R_E_cv": Ra.tolist()}
    pb = {"angles": C.angles(Rb), "C_E_m": Cb.tolist(), "R_E_cv": Rb.tolist()}
    d = C.delta(pa, pb)
    d["frame"] = fa if fa == fb else f"{fa} vs {fb}"
    return d


def cmd_measure(a, frames=None, write=True):
    K, dist, intr = load_K(a.intrinsics)
    T_E_K, board = (C.board_in_E(a.board_in_e) if Path(a.board_in_e).exists() else (None, None))
    lock_ok = None
    if frames is None:
        if a.source.startswith("camera:"):
            lock_ok = camera_lock.cmd_apply(a.source.split(":", 1)[1], write=False) == 0
            if not lock_ok:
                raise SystemExit("STOP: camera lock does not read back; run camera_lock.py apply front")
        src = capture.open_source(a.source)
        try:
            frames = [src.read() for _ in range(a.frames)]
        finally:
            ident = src.identity
            src.close()
    else:
        ident = {"product": "provided frames"}
    rec = measure_frames(frames, K, dist, a.square_mm, T_E_K)
    rec.update({"tag": a.tag, "utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                "camera": ident, "lock_readback_ok": lock_ok, "square_mm": a.square_mm,
                "intrinsics_sha256": sha(a.intrinsics), "board_in_E_sha256": sha(a.board_in_e) if board else None,
                "board_in_E": board, "notes": dict(n.split("=", 1) for n in (a.note or []))})
    if write:
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / f"{a.tag}.json").write_text(json.dumps(rec, indent=1))
        for i, f in enumerate(frames):
            capture.save_rgb((OUT / "media" if "GTC_POSES_DIR" in os.environ else GTC / "media" / "poses") / a.tag
                             / f"frame_{i:03d}.png", f)
    show(rec)
    return rec


def show(rec):
    print(f"{rec.get('tag', '')}: RMS {rec['rms_px']:.3f} px ({'ok' if rec['rms_px'] <= MAX_RMS else 'REDO: > 0.30 px'}), "
          f"{rec['n_corners']} corners, frame SD {rec.get('frame_sd_pos_mm', float('nan')):.2f} mm / "
          f"{rec.get('frame_sd_rot_deg', float('nan')):.3f} deg")
    if "C_E_m" in rec:
        c, g = rec["C_E_m"], rec["angles"]
        print(f"  lens C_E ({c[0]:.4f}, {c[1]:.4f}, {c[2]:.4f}) m; depression {g['depression_deg']:.2f}, "
              f"heading {g['heading_deg']:.2f}, roll {g['roll_deg']:.2f} deg")
    else:
        g = rec["angles_board_frame"]
        print(f"  no board_in_E.json: board-frame angles depression {g['depression_deg']:.2f}, heading {g['heading_deg']:.2f}, "
              f"roll {g['roll_deg']:.2f} deg (relative use only)")


def load(tag):
    p = OUT / f"{tag}.json"
    if not p.exists():
        raise SystemExit(f"STOP: no pose {p}")
    return json.loads(p.read_text())


def cmd_mean(tags, out):
    recs = [load(t) for t in tags]
    Rs, Cs = zip(*[frame_E(r)[:2] for r in recs])
    qs = np.array([C.rot_to_quat(R) for R in Rs])
    qs[np.sum(qs * qs[0], axis=1) < 0] *= -1
    q = qs.mean(0)
    q /= np.linalg.norm(q)
    w, x, y, z = q
    R = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
                  [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
                  [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)]])
    Cm = np.mean(Cs, axis=0)
    ang = [C.angles(Ri) for Ri in Rs]
    frame = frame_E(recs[0])[2]
    rec = {"tag": out, "mean_of": list(tags), "frame": frame, "rms_px": max(r["rms_px"] for r in recs),
           "n_corners": min(r["n_corners"] for r in recs),
           "spread": {"pos_sd_mm": (1000 * np.std(Cs, axis=0)).round(3).tolist(),
                      **{f"{k}_sd": float(np.std([g[k] for g in ang])) for k in ("depression_deg", "heading_deg", "roll_deg")}},
           "notes": {k: v for r in recs for k, v in r.get("notes", {}).items()},
           "utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    if frame == "E":
        rec.update({"C_E_m": Cm.tolist(), "R_E_cv": R.tolist(), "q_wxyz_cv": C.rot_to_quat(R),
                    "q_wxyz_usd": C.rot_to_quat(R @ np.diag([1.0, -1.0, -1.0])), "angles": C.angles(R)})
    else:
        F = np.diag([1.0, -1.0, -1.0])
        rec.update({"C_K_m": (F @ Cm).tolist(), "R_K_cv": (F @ R).tolist(), "angles_board_frame": C.angles(R)})
    (OUT / f"{out}.json").write_text(json.dumps(rec, indent=1))
    show(rec)
    print(f"  spread over {len(recs)} placements: pos SD {rec['spread']['pos_sd_mm']} mm, depression SD "
          f"{rec['spread']['depression_deg_sd']:.3f}, heading SD {rec['spread']['heading_deg_sd']:.3f}, "
          f"roll SD {rec['spread']['roll_deg_sd']:.3f} deg (accept 0.5 mm / 0.3 deg, B 4.2)")
    return rec


def cmd_reach(tag):
    """Absolute angle below horizontal of a measured pose, against the sim's 54.27 deg + 13 / + 15 deg
    (67.3 and 69.3 deg); saved into the pose record."""
    rec = load(tag)
    R, _, frame = frame_E(rec)
    dep = C.angles(R)["depression_deg"]
    f = json.loads((GTC / "results" / "c1" / "frames_sim.json").read_text())
    sim = f["camera_external_D455"]["optical_axis_deg_below_horizontal"]
    res = {"depression_deg": dep, "frame": frame, "sim_nominal_deg": sim, "extra_vs_sim_deg": dep - sim,
           "reaches_67.3": dep >= 67.3, "reaches_69.3": dep >= 69.3}
    rec["reach"] = res
    (OUT / f"{tag}.json").write_text(json.dumps(rec, indent=1))
    note = "" if frame == "E" else " (board frame: absolute only if the board lies level)"
    print(f"{tag}: {dep:.2f} deg below horizontal{note}; sim nominal {sim:.2f} -> {dep - sim:+.2f} deg extra; "
          f"reaches 67.3 deg (sim + 13): {'YES' if res['reaches_67.3'] else 'no'}; 69.3 deg (sim + 15): "
          f"{'YES' if res['reaches_69.3'] else 'no'}")
    return res


def print_diff(d, a, b):
    print(f"{b} - {a} ({d['frame']}): tilt_down {d['tilt_down_deg']:+.2f} deg, pan {d['pan_deg']:+.2f} deg, "
          f"roll {d['roll_deg']:+.2f} deg, lateral {1000 * d['lateral_m']:+.1f} mm, depth {1000 * d['depth_m']:+.1f} mm, "
          f"height {1000 * d['height_m']:+.1f} mm (total rotation {d['rotation_total_deg']:.2f} deg)")


def quat_to_rot(q):
    w, x, y, z = np.asarray(q, float) / np.linalg.norm(q)
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
                     [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
                     [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)]])


OFFSET_KEYS = {"tilt_down_deg", "pan_deg", "roll_deg", "depth_mm", "lateral_mm", "height_mm"}


def base_target(tag):
    """Target = a saved pose in E (results/poses/TAG.json)."""
    rec = load(tag)
    R, Cm, frame = frame_E(rec)
    if frame != "E":
        raise SystemExit(f"STOP: pose {tag} has no E frame (measured without board_in_E.json); it can't be a target")
    return {"name": tag, "desc": "saved pose", "C_E_m": Cm.tolist(), "R_E_cv": R.tolist(), "angles": C.angles(R),
            "source": f"results/poses/{tag}.json ({rec.get('utc', 'no time')})"}


def offset_target(tgt, offsets):
    """tgt moved by B 1.3 offsets (the terms diff prints), so measured - target = diff(tgt's pose, measured) - offsets."""
    bad = set(offsets) - OFFSET_KEYS
    if bad:
        raise SystemExit(f"STOP: unknown offset {sorted(bad)}; use {sorted(OFFSET_KEYS)}")
    g = dict(tgt["angles"])
    g["depression_deg"] += offsets.get("tilt_down_deg", 0.0)
    g["heading_deg"] += offsets.get("pan_deg", 0.0)
    g["roll_deg"] += offsets.get("roll_deg", 0.0)
    Cm = np.array(tgt["C_E_m"]) + np.array([offsets.get(k, 0.0) for k in ("depth_mm", "lateral_mm", "height_mm")]) / 1000
    R = C.rot_from_angles(g["depression_deg"], g["heading_deg"], g["roll_deg"])
    name = tgt["name"] + "".join(f" {k}{v:+g}" for k, v in offsets.items())
    return {**tgt, "name": name, "C_E_m": Cm.tolist(), "R_E_cv": R.tolist(), "angles": C.angles(R),
            "offsets": dict(offsets)}


def load_target(name, path=FRAMES_SIM):
    """Target pose in E. s1 = the render point (D4): the USD world matrix of Camera_OmniVision_OV9782_Right from the
    C1 dump, flipped to the CV camera; cross-checked against Isaac Lab's pos_w / quat_w_ros in the same dump, and
    expressed in tape terms (Base / Left panel faces) against the S1 tape values (step C1)."""
    if name != "s1":
        raise SystemExit(f"STOP: unknown target {name!r} (only s1)")
    f = json.loads(Path(path).read_text())
    cam = f["camera_external_D455"]
    M = np.array(cam["world_usd"]["matrix_row_major_usd"])             # rows 0-2 = local axes in E, row 3 = position
    U, _, Vt = np.linalg.svd(M[:3, :3].T)                              # drop the prim's 1e-6 scale
    R = U @ Vt @ np.diag([1.0, -1.0, -1.0])                            # USD camera -> CV camera
    Cm = M[3, :3]
    tc = cam["tiled_camera"]
    cross = {"pos_mm": float(1000 * np.linalg.norm(Cm - np.array(tc["pos_w"]))),
             "rot_deg": C.angle_between(R, quat_to_rot(tc["quat_w_ros"]))}
    p = f["lightbox_panels"]
    g = C.angles(R)
    tape = {"height_above_floor_cm": 100 * (Cm[2] - p["Base"]["world_bbox_max"][2]),
            "from_front_edge_cm": 100 * (Cm[0] - p["Base"]["world_bbox_min"][0]),
            "from_left_wall_cm": 100 * (p["Left"]["world_bbox_min"][1] - Cm[1]),
            "depression_deg": g["depression_deg"], "roll_deg": g["roll_deg"],
            "pan_toward_back_wall_deg": g["heading_deg"] + 90}
    mismatch = {k: (tape[k], v) for k, (v, tol) in S1_TAPE.items() if abs(tape[k] - v) > tol + 1e-9}
    return {"name": name, "desc": "render point", "C_E_m": Cm.tolist(), "R_E_cv": R.tolist(), "angles": g, "tape": tape,
            "cross_check": cross, "tape_mismatch": mismatch,
            "source": f"{Path(path).name} camera_external_D455 ({cam['prim_path'].rsplit('/', 1)[-1]})"}


def target_errors(rec, tgt, tol_mm=TOL_MM, tol_deg=TOL_DEG, aim_deg=AIM_DEG):
    """Measured - target per axis (B 1.3: actual - nominal; the move is the opposite), green within the band
    (default E row 22)."""
    R, Cm, frame = frame_E(rec)
    if frame != "E":
        raise SystemExit("STOP: the target needs the pose in E: measure the sled into config/board_in_E.json first")
    d = C.delta(tgt, {"angles": C.angles(R), "C_E_m": Cm.tolist(), "R_E_cv": R.tolist()})
    rows = []
    for key, label, scale, unit, _, plus, minus in AXES:
        v = d[key] * scale
        tol = tol_mm if unit == "mm" else tol_deg
        rows.append({"axis": label, "error": v, "unit": unit, "ok": abs(v) <= tol, "tol": tol,
                     "aim_ok": unit == "mm" or abs(v) <= aim_deg, "move": (plus if v > 0 else minus).format(abs(v))})
    return rows


def target_lines(rows, rec, tgt):
    """(text, ok) per panel line; ok None = neutral."""
    g = rec["angles"]
    out = [(f"target {tgt['name']} ({tgt['desc']}), RMS {rec['rms_px']:.2f} px", None),
           (f"now: {g['depression_deg']:.2f} deg down, heading {g['heading_deg']:.2f}, roll {g['roll_deg']:+.2f}", None),
           (f"want: {tgt['angles']['depression_deg']:.2f} deg down, heading {tgt['angles']['heading_deg']:.2f}, "
            f"roll {tgt['angles']['roll_deg']:+.2f}", None), ("", None)]
    for r in rows:
        tag = "OK" if r["ok"] and r["aim_ok"] else f"OK, aim <= {AIM_DEG:g}" if r["ok"] else "MOVE"
        fmt = "{:+6.1f}" if r["unit"] == "mm" else "{:+6.2f}"
        out += [(f"{r['axis']:<5}{fmt.format(r['error'])} {r['unit']}   {tag}", r["ok"]), (f"      -> {r['move']}", r["ok"])]
    bad = sum(not r["ok"] for r in rows)
    band = "E row 22 (3 mm, 0.5 deg)" if (rows[0]["tol"], rows[3]["tol"]) == (TOL_MM, TOL_DEG) else \
        f"{rows[0]['tol']:g} mm, {rows[3]['tol']:g} deg"
    out += [("", None), ("ALL GREEN: tighten, then read again" if not bad else f"NOT YET: {bad} of 6 outside {band}", not bad)]
    return out


GHOST_RGB, LIVE_RGB, ARROW_RGB = (60, 230, 60), (255, 0, 255), (255, 220, 0)


def board_shapes(square_mm):
    """The board's outline and its four corner squares in the board frame K (m); the origin's square first."""
    s = square_mm / 1000
    W, H = C.SPEC["cols"] * s, C.SPEC["rows"] * s
    sq = lambda x, y: np.array([[x, y, 0], [x + s, y, 0], [x + s, y + s, 0], [x, y + s, 0]])
    return {"outline": np.array([[0, 0, 0], [W, 0, 0], [W, H, 0], [0, H, 0]]),
            "squares": [sq(0, 0), sq(W - s, 0), sq(W - s, H - s), sq(0, H - s)], "centre": np.array([[W / 2, H / 2, 0]])}


def project(T_cv_K, pts, K, dist):
    """Image points of board-frame points, or None if any lies behind the camera."""
    P = (T_cv_K[:3, :3] @ np.asarray(pts, float).T).T + T_cv_K[:3, 3]
    if (P[:, 2] <= 0.01).any():
        return None
    return cv2.projectPoints(P, np.zeros(3), np.zeros(3), K, dist)[0].reshape(-1, 2)


def board_px(T_cv_K, shapes, K, dist):
    out = {"outline": project(T_cv_K, shapes["outline"], K, dist), "centre": project(T_cv_K, shapes["centre"], K, dist),
           "squares": [project(T_cv_K, q, K, dist) for q in shapes["squares"]]}
    return None if out["outline"] is None or out["centre"] is None or any(q is None for q in out["squares"]) else out


def draw_board(img, px, rgb):
    """Outline and corner squares; the origin's square (printed top-left) half filled, so a 180 deg turn shows."""
    over = img.copy()
    cv2.fillPoly(over, [np.round(px["squares"][0]).astype(np.int32)], rgb)
    img[:] = cv2.addWeighted(over, 0.35, img, 0.65, 0)
    for poly, th in [(px["outline"], 3)] + [(q, 2) for q in px["squares"]]:
        cv2.polylines(img, [np.round(poly).astype(np.int32)], True, rgb, th, cv2.LINE_AA)


def pose_T_cv_K(R_E_cv, C_E, T_E_K):
    return np.linalg.inv(C.T(R_E_cv, C_E)) @ T_E_K


def largest_fix(rows, rec):
    """(row, (R, C) of the measured pose with only that axis corrected) for the error largest against its band."""
    r = max(rows, key=lambda r: abs(r["error"]) / r["tol"])
    if r["ok"]:
        return None, None
    R, Cm, _ = frame_E(rec)
    Cm = Cm.copy()
    i = [x[1] for x in AXES].index(r["axis"])
    if r["unit"] == "mm":
        Cm[(0, 1, 2)[i]] -= r["error"] / 1000                  # x = depth, y = lateral, z = height (E axes)
    else:
        g = C.angles(R)
        key = ("depression_deg", "heading_deg", "roll_deg")[i - 3]
        g[key] -= r["error"]
        R = C.rot_from_angles(g["depression_deg"], g["heading_deg"], g["roll_deg"])
    return r, (R, Cm)


def ghost_view(f, ghost, live_px, fix_px, fix_row):
    """The live frame with the board as the target pose would see it (green), the live board (magenta) and one arrow:
    where the board moves in the image when the largest correction alone is made."""
    img = f.copy()
    if ghost is not None:
        draw_board(img, ghost, GHOST_RGB)
    if live_px is not None:
        draw_board(img, live_px, LIVE_RGB)
    if fix_row is not None and live_px is not None and fix_px is not None:
        a, b = live_px["centre"][0], fix_px["centre"][0]
        v = b - a
        n = float(np.hypot(*v))
        if n >= 2:
            b = a + v / n * max(n, 60.0)                          # at least 60 px long: a direction cue
            cv2.arrowedLine(img, tuple(np.round(a).astype(int)), tuple(np.round(b).astype(int)), (0, 0, 0), 9,
                            cv2.LINE_AA, tipLength=0.25)
            cv2.arrowedLine(img, tuple(np.round(a).astype(int)), tuple(np.round(b).astype(int)), ARROW_RGB, 5,
                            cv2.LINE_AA, tipLength=0.25)
    img = live.put_lines(img, ["green: board from the target pose   magenta: live board"], color=(255, 255, 255))
    if fix_row is not None:
        img = live.put_lines(img, [f"FIRST: {fix_row['move']}"], org=(8, 52), scale=0.8, color=ARROW_RGB)
    return img


def panel(frame, lines, width=600):
    h = frame.shape[0]
    side = np.zeros((h, width, 3), np.uint8)
    for i, (text, ok) in enumerate(lines):
        col = (255, 255, 255) if ok is None else (60, 230, 60) if ok else (255, 70, 70)
        side = live.put_lines(side, [text], org=(10, 24 + 22 * i), scale=0.5, color=col)
    return np.hstack([frame, side])


def cmd_hud(a):
    K, dist, _ = load_K(a.intrinsics)
    T_E_K = C.board_in_E(a.board_in_e)[0] if Path(a.board_in_e).exists() else None
    ref = load(a.ref) if a.ref else None
    tgt = None
    offsets = {k: float(v) for k, v in (o.split("=", 1) for o in a.offset or [])}
    if a.target and a.base:
        raise SystemExit("STOP: give --target s1 or --base TAG, not both")
    if offsets and not (a.target or a.base):
        raise SystemExit("STOP: --offset needs --target s1 or --base TAG")
    if a.target or a.base:
        if T_E_K is None:
            raise SystemExit(f"STOP: --{'target' if a.target else 'base'} needs {a.board_in_e} (sled readings, B 4.2 / D7)")
    aim = AIM_DEG if a.target and not offsets and (a.tol_mm, a.tol_deg) == (TOL_MM, TOL_DEG) else a.tol_deg
    if a.base:
        tgt = offset_target(base_target(a.base), offsets)
        g = tgt["angles"]
        print(f"target {tgt['name']}: {tgt['source']}; lens C_E ({', '.join(f'{v:.4f}' for v in tgt['C_E_m'])}) m; "
              f"{g['depression_deg']:.2f} deg down, heading {g['heading_deg']:.2f}, roll {g['roll_deg']:+.2f}; "
              f"green within {a.tol_mm:g} mm / {a.tol_deg:g} deg")
    elif a.target:
        tgt = load_target(a.target)
        t, c = tgt["tape"], tgt["cross_check"]
        print(f"target {a.target}: {tgt['source']}; lens C_E ({', '.join(f'{v:.4f}' for v in tgt['C_E_m'])}) m = "
              f"{t['height_above_floor_cm']:.2f} cm above the foam floor, {t['from_front_edge_cm']:.2f} cm from the open "
              f"front edge, {t['from_left_wall_cm']:.2f} cm from the left wall; {t['depression_deg']:.2f} deg down, pan "
              f"{t['pan_toward_back_wall_deg']:.2f} deg toward the back wall, roll {t['roll_deg']:+.2f} deg; "
              f"vs Isaac Lab pos_w/quat_w_ros {c['pos_mm']:.3f} mm / {c['rot_deg']:.4f} deg")
        for k, (have, want) in tgt["tape_mismatch"].items():
            print(f"  WARNING: {k} {have:.3f} here vs {want} in the S1 tape values")
        if offsets:
            tgt = offset_target(tgt, offsets)
            print(f"  moved by {offsets}: {tgt['angles']['depression_deg']:.2f} deg down; green within "
                  f"{a.tol_mm:g} mm / {a.tol_deg:g} deg")
    if a.ghost and not tgt:
        raise SystemExit("STOP: --ghost needs --target s1 or --base TAG")
    shapes = board_shapes(a.square_mm)
    ghost = board_px(pose_T_cv_K(np.array(tgt["R_E_cv"]), np.array(tgt["C_E_m"]), T_E_K), shapes, K, dist) \
        if a.ghost else None
    if a.ghost and ghost is None:
        print("WARNING: the board is not in front of the target pose; no ghost drawn")
    src = capture.open_source(a.source)
    buf, st = [], {"line": "collecting frames...", "lines": [("collecting frames...", None)], "live": None,
                   "fix": (None, None)}

    def step():
        f = src.read()
        buf.append(f)
        if len(buf) >= 5:
            try:
                rec = measure_frames(buf, K, dist, a.square_mm, T_E_K)
                R, _, frame = frame_E(rec)
                g = C.angles(R)
                st["line"] = (f"absolute ({'E' if frame == 'E' else 'board'}): {g['depression_deg']:.2f} deg below horizontal, "
                              f"heading {g['heading_deg']:.2f}, roll {g['roll_deg']:+.2f}  RMS {rec['rms_px']:.2f}")
                if ref:
                    d = diff(ref, rec)
                    st["line"] += (f" | vs {a.ref}: tilt {d['tilt_down_deg']:+.2f} roll {d['roll_deg']:+.2f} "
                                   f"pan {d['pan_deg']:+.2f} dz {1000 * d['height_m']:+.1f} mm")
                if tgt:
                    rows = target_errors(rec, tgt, a.tol_mm, a.tol_deg, aim)
                    st["lines"] = target_lines(rows, rec, tgt)
                    if a.ghost:
                        T_K_cv = C.T(np.array(rec["R_K_cv"]), rec["C_K_m"])
                        st["live"] = board_px(np.linalg.inv(T_K_cv), shapes, K, dist)
                        row, fixed = largest_fix(rows, rec)
                        st["fix"] = (row, board_px(pose_T_cv_K(*fixed, T_E_K), shapes, K, dist) if row else None)
            except SystemExit as e:
                st["line"] = str(e)
                st["lines"] = [(str(e), False)]
                st["live"], st["fix"] = None, (None, None)
            buf.clear()
        if tgt:
            view = ghost_view(f, ghost, st["live"], st["fix"][1], st["fix"][0]) if a.ghost else f
            return panel(view, st["lines"] + [("q quit", None)]), [t for t, _ in st["lines"]]
        return live.put_lines(f, [st["line"], "q quit"], scale=0.6), [st["line"]]

    title = f"pose to {tgt['name']}" if tgt else f"pose {'vs ' + a.ref if a.ref else 'absolute'}"
    try:
        live.run(step, {"q": lambda: "quit"}, title, headless=a.headless_frames is not None,
                 max_frames=a.headless_frames)
    finally:
        src.close()
    print("\n".join(t for t, _ in st["lines"]) if tgt else st["line"])


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["measure", "mean", "diff", "hud", "note", "reach"])
    ap.add_argument("args", nargs="*")
    ap.add_argument("--tag")
    ap.add_argument("--tags", nargs="*")
    ap.add_argument("--out")
    ap.add_argument("--ref")
    ap.add_argument("--target", choices=["s1"])
    ap.add_argument("--base", help="hud: a saved pose tag in E as the target")
    ap.add_argument("--offset", action="append", help="hud: KEY=VALUE added to the target (B 1.3 terms)")
    ap.add_argument("--ghost", action="store_true", help="hud with a target: draw the board as the target pose would see "
                    "it (green) over the live board (magenta), and an arrow for the largest correction")
    ap.add_argument("--tol-mm", type=float, default=TOL_MM)
    ap.add_argument("--tol-deg", type=float, default=TOL_DEG)
    ap.add_argument("--frames", type=int, default=20)
    ap.add_argument("--source", default="camera:front")
    ap.add_argument("--intrinsics", default=str(INTR))
    ap.add_argument("--board-in-e", default=str(BOARD))
    ap.add_argument("--square-mm", type=float, default=30.0)
    ap.add_argument("--note", action="append")
    ap.add_argument("--headless-frames", type=int, default=None)
    a = ap.parse_args(argv)
    if a.cmd in ("measure", "hud") and not Path(a.intrinsics).exists():
        raise SystemExit(f"STOP: {a.intrinsics} not found; calibrate the lens first (intrinsics_solve.py)")
    if a.cmd == "measure":
        cmd_measure(a)
    elif a.cmd == "mean":
        cmd_mean(a.tags, a.out)
    elif a.cmd == "diff":
        d = diff(load(a.args[0]), load(a.args[1]))
        print_diff(d, a.args[0], a.args[1])
    elif a.cmd == "reach":
        cmd_reach(a.args[0])
    elif a.cmd == "note":
        rec = load(a.args[0])
        rec.setdefault("notes", {}).update(dict(n.split("=", 1) for n in a.args[1:]))
        (OUT / f"{a.args[0]}.json").write_text(json.dumps(rec, indent=1))
        print(f"{a.args[0]} notes: {rec['notes']}")
    else:
        cmd_hud(a)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
