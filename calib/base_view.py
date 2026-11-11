#!/usr/bin/env python3
"""Live base view (Nov 9, after N05-012): where the robot base sits against its S1 position, read from the ChArUco
board on the sled (the sled seats on the base, so the board moves with the base while the camera stays put), and the
turn and slide that bring the base back.

    .venv/bin/python -I calib/base_view.py [--base s1] [--frames 5]        # q quits
Each reading is the PnP of --frames frames (pose.py measure_frames, board_in_E.json). With the camera fixed, a point p
of the base now sits at M p in the base's frame at --base, M = T_base * T_now^-1 (T = camera pose in E). The base's
turn is M's yaw (+ = counter-clockwise seen from above); its slide is where M puts the pan axis (the shoulder joint
of the course USD, tools/arm_fk.py: (-0.0269, 0.0208) m in E) against where it was. The undo is shown as a turn about
the pan axis (the centre of the round turntable on top of the base), then the slide of the pan axis.
The six numbers of `pose.py diff BASE now` are shown too, green within the limits of Nov 9 (each position 1.5 mm, pan
0.3 deg, tilt and roll 0.2 deg). Ghost (as pose.py hud --ghost): green = the board as it would sit with the base back
at --base, magenta = the live board; moving the base moves magenta.
The board moves with the base only while the sled stays seated: re-seat it (B 4.2 method) before each reading counts.
On quit: results/rig/base_view_last.json and base_view_last.png.
"""
import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))  # sibling modules (python -I skips the script dir)

import camera_lock  # noqa: E402
import capture  # noqa: E402
import charuco as C  # noqa: E402
import live  # noqa: E402
import pose as P  # noqa: E402

GTC = Path(__file__).resolve().parents[1]
PAN_AXIS_E = np.array([-0.0269, 0.0208, 0.0949])      # shoulder joint origin at the course root (arm_fk.fk, all joints 0)
PLATE_X_E = (-0.0881, -0.0011)                        # base bottom plate, rear (door side) and front edges in E (USD mesh)
LIMITS = {"lateral_mm": 1.5, "depth_mm": 1.5, "height_mm": 1.5, "pan_deg": 0.3, "tilt_down_deg": 0.2, "roll_deg": 0.2}


def base_move(ref, rec):
    """The base now against the base at ref: yaw (deg, + = counter-clockwise seen from above) and the pan axis's shift
    (m, E of ref), from the camera pose in E at ref (Ra, Ca) and now (Rb, Cb)."""
    Ra, Ca, _ = P.frame_E(ref)
    Rb, Cb, _ = P.frame_E(rec)
    RM = Ra @ Rb.T
    tM = Ca - RM @ Cb
    yaw = float(np.degrees(np.arctan2(RM[1, 0], RM[0, 0])))
    tilt = float(np.degrees(np.arccos(np.clip(RM[2, 2], -1.0, 1.0))))
    return yaw, RM @ PAN_AXIS_E + tM - PAN_AXIS_E, tilt


def undo_words(yaw, shift_m, min_deg=0.05, min_mm=0.5):
    """The turn about the pan axis, then the slide of the pan axis, that put the base back."""
    out = []
    if abs(yaw) >= min_deg:
        rad = np.radians(abs(yaw))
        rear, front = 1000 * rad * (PAN_AXIS_E[0] - PLATE_X_E[0]), 1000 * rad * (PLATE_X_E[1] - PAN_AXIS_E[0])
        to_cam, to_right = "toward the camera wall", "toward the right wall"
        cw = yaw > 0                                         # the base turned counter-clockwise: undo clockwise
        out.append(f"turn the base {abs(yaw):.2f} deg {'clockwise' if cw else 'counter-clockwise'} seen from above, about "
                   f"the turntable centre: rear edge (door side) {rear:.1f} mm {to_cam if cw else to_right}, front edge "
                   f"{front:.1f} mm {to_right if cw else to_cam}")
    dx, dy = -1000 * shift_m[0], -1000 * shift_m[1]
    slide = []
    if abs(dx) >= min_mm:
        slide.append(f"{abs(dx):.1f} mm {'toward the back wall' if dx > 0 else 'toward the open front'}")
    if abs(dy) >= min_mm:
        slide.append(f"{abs(dy):.1f} mm {'toward the camera wall' if dy > 0 else 'toward the right wall'}")
    if slide:
        out.append("then slide it " + " and ".join(slide))
    return out or ["stay"]


def diff_rows(d):
    v = {"lateral_mm": 1000 * d["lateral_m"], "depth_mm": 1000 * d["depth_m"], "height_mm": 1000 * d["height_m"],
         "pan_deg": d["pan_deg"], "tilt_down_deg": d["tilt_down_deg"], "roll_deg": d["roll_deg"]}
    return {k: (float(x), bool(abs(x) <= LIMITS[k])) for k, x in v.items()}


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="s1", help="saved pose in E (results/poses/TAG.json) where the base belongs")
    ap.add_argument("--frames", type=int, default=5, help="frames per reading")
    ap.add_argument("--source", default="camera:front")
    ap.add_argument("--square-mm", type=float, default=29.97)
    ap.add_argument("--intrinsics", default=str(P.INTR))
    ap.add_argument("--board-in-e", default=str(P.BOARD))
    ap.add_argument("--headless-frames", type=int)
    ap.add_argument("--out", default=str(GTC / "results" / "rig" / "base_view_last"))
    a = ap.parse_args(argv)
    K, dist, _ = P.load_K(a.intrinsics)
    T_E_K = C.board_in_E(a.board_in_e)[0]
    ref = P.load(a.base)
    shapes = P.board_shapes(a.square_mm)
    ghost = P.board_px(P.pose_T_cv_K(np.array(ref["R_E_cv"]), np.array(ref["C_E_m"]), T_E_K), shapes, K, dist)
    if a.source.startswith("camera:"):
        if camera_lock.cmd_apply(a.source.split(":", 1)[1], write=False) != 0:
            raise SystemExit("STOP: camera lock does not read back; run camera_lock.py apply front")
    src = capture.open_source(a.source)
    buf, st = [], {"lines": [("collecting frames...", None)], "live": None, "rec": None, "view": None}

    def step():
        f = src.read()
        buf.append(f)
        if len(buf) >= a.frames:
            try:
                rec = P.measure_frames(buf, K, dist, a.square_mm, T_E_K)
                yaw, shift, tilt = base_move(ref, rec)
                rows = diff_rows(P.diff(ref, rec))
                ok = all(p for _, p in rows.values())
                lines = [(f"base vs {a.base}: {'WITHIN THE LIMITS' if ok else 'OUTSIDE THE LIMITS'}  (sled seated? hands "
                          f"out?)", ok),
                         (f"base now: turned {yaw:+.2f} deg (+ = counter-clockwise seen from above); pan axis moved "
                          f"{1000 * shift[0]:+.1f} mm in x (+ toward the back wall), {1000 * shift[1]:+.1f} mm in y "
                          f"(+ toward the camera wall), {1000 * shift[2]:+.1f} mm up", None)]
                lines += [("UNDO: " + w if i == 0 else "      " + w, None) for i, w in enumerate(undo_words(yaw, shift))]
                lines += [(f"pose.py diff {a.base} now: {k} {v:+.2f} (limit {LIMITS[k]:g})", p) for k, (v, p) in rows.items()]
                lines.append((f"RMS {rec['rms_px']:.2f} px, {len(rec['corner_ids'])} corners", rec["rms_ok"]))
                T_K_cv = C.T(np.array(rec["R_K_cv"]), rec["C_K_m"])
                st["live"] = P.board_px(np.linalg.inv(T_K_cv), shapes, K, dist)
                st["lines"] = lines
                st["rec"] = {"utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "base": a.base,
                             "within_limits": ok, "yaw_deg": round(yaw, 3), "base_z_tilt_deg": round(tilt, 3),
                             "pan_axis_shift_mm": [round(1000 * float(v), 2) for v in shift],
                             "undo": undo_words(yaw, shift), "diff": {k: round(v, 3) for k, (v, _) in rows.items()},
                             "limits": LIMITS, "rms_px": rec["rms_px"], "n_corners": len(rec["corner_ids"]),
                             "frames": a.frames, "C_E_m": rec["C_E_m"], "R_E_cv": rec["R_E_cv"]}
            except SystemExit as e:
                st["lines"], st["live"] = [(str(e), False)], None
            buf.clear()
        view = P.ghost_view(f, ghost, st["live"], None, None)
        col = {None: (255, 255, 255), True: (60, 230, 60), False: (255, 70, 70)}
        st["view"] = np.vstack([view, live.text_panel([(t, col[o]) for t, o in st["lines"] + [("q quit", None)]],
                                                      view.shape[1])])
        if a.headless_frames is not None and len(buf) == 0:
            print("\n".join(t for t, _ in st["lines"]))
        return st["view"], [t for t, _ in st["lines"]]

    try:
        live.run(step, {"q": lambda: "quit"}, f"base vs {a.base}", headless=a.headless_frames is not None,
                 max_frames=a.headless_frames)
    finally:
        src.close()
        if st["rec"] is not None:
            Path(a.out).parent.mkdir(parents=True, exist_ok=True)
            Path(a.out + ".json").write_text(json.dumps(st["rec"], indent=1))
            capture.save_rgb(a.out + ".png", st["view"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
