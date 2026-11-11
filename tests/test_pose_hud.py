#!/usr/bin/env python3
"""HUD target mode (`pose.py hud --target s1`) on rendered views of the real print.

    .venv/bin/python -I tests/test_pose_hud.py
Target: the render point from results/c1/frames_sim.json (D4), checked against Isaac Lab's pos_w / quat_w_ros and
the S1 tape values (step C1). The sled board sits at the B 4.2 CAD placement (test values, not readings). The camera is put
at the exact target, then moved by single offsets (the made-up test lens of tests/make_synthetic_calib.py).
1. Geometry: the board corners projected exactly -> PnP -> the HUD's errors equal the injected offsets within
   0.01 mm / 0.001 deg, with the E row 22 colour and the move back to the target.
2. Rendered views measured as the HUD does (5 frames): exact pose -> all six errors within 1 mm / 0.1 deg (T11's
   absolute bounds) and ALL GREEN; each offset -> its axis within 0.6 mm / 0.1 deg of the injected value, the
   others within 1 mm / 0.15 deg (the render's own bias reaches about 0.1 deg at the S1 view, where the print is
   only about 170 px wide; part 1 checks the HUD's arithmetic), the colour and the move direction as in 1.
3. The CLI, headless, on rendered frames: exact pose prints ALL GREEN, the +5 mm case prints NOT YET; without
   board_in_E.json it stops.
4. Saved-pose targets (`hud --base TAG --offset ... --tol-mm --tol-deg`, the gauge-free M2 moves of Nov 5): the base
   is a made-up R1 pose near the target (+1/-2/0 mm, +0.2/-0.3/+0.1 deg; test values). Exact geometry: the camera
   at base + offsets reads zero on all six axes; at the base it reads tilt -6.00 red with "tilt 6.00 deg down";
   +0.4 deg past the level is red at 0.3 deg and green at 0.5. CLI on rendered frames: base + 6 deg prints ALL
   GREEN at 2 mm / 0.3 deg, base + 6.5 prints NOT YET with that band; --target with --base, and --offset alone, stop.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np

GTC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GTC / "calib"))
sys.path.insert(0, str(GTC / "tests"))
import capture  # noqa: E402
import charuco as C  # noqa: E402
import pose  # noqa: E402
from make_synthetic_calib import DIST, K  # noqa: E402
from test_pose_synthetic import R_E_cv  # noqa: E402

BOARD = {"d_x_mm": 101.1, "d_y_mm": 89.2, "h_K_mm": 9.9, "yaw_deg": 0.0, "method": "test: B 4.2 CAD intent"}
# name: (offset in E mm (x, y, z), angle offsets deg (depression, heading, roll), axis, want, green, move direction)
CASES = {"x+2mm": ((2, 0, 0), (0, 0, 0), "x", 2.0, True, "mm toward the open front"),
         "y+5mm": ((0, 5, 0), (0, 0, 0), "y", 5.0, False, "mm away from the camera wall"),
         "z-2.5mm": ((0, 0, -2.5), (0, 0, 0), "z", -2.5, True, "mm up"),
         "tilt+0.4": ((0, 0, 0), (0.4, 0, 0), "tilt", 0.4, True, "deg up"),
         "pan-0.7": ((0, 0, 0), (0, -0.7, 0), "pan", -0.7, False, "deg toward the back wall"),
         "roll+1": ((0, 0, 0), (0, 0, 1.0), "roll", 1.0, False, "deg counter-clockwise")}


def views(tex, H, T_E_K, C_E, ang, n=5):
    T_cv_K = np.linalg.inv(C.T(R_E_cv(*ang), C_E)) @ T_E_K
    return [np.repeat(C.render_view(tex, H, K, DIST, T_cv_K, noise=1.5, blur=0.7, rng=np.random.default_rng(i))[:, :, None], 3, 2)
            for i in range(n)]


def exact_rec(T_cv_K, T_E_K):
    obj = C.make_board(30.0).getChessboardCorners().astype(np.float64)
    rv, tv = cv2.Rodrigues(T_cv_K[:3, :3])[0], T_cv_K[:3, 3]
    img = cv2.projectPoints(obj, rv, tv, K, DIST)[0].reshape(-1, 2)
    sol = C.solve_pose({"ids": np.arange(len(obj)), "img": img, "obj": obj}, K, DIST)
    return C.pose_record(sol, T_E_K)


def check_case(rows, axis, want, green, move, tol, tol_other):
    r = rows[axis]
    others = max(abs(o["error"]) / (tol_other[0] if o["unit"] == "mm" else tol_other[1]) for k, o in rows.items() if k != axis)
    good = (abs(r["error"] - want) <= (tol[0] if r["unit"] == "mm" else tol[1]) and r["ok"] == green and others <= 1
            and move in r["move"])
    return good, (f"{axis} {r['error']:+.3f} {r['unit']} (want {want:+.1f}) {'green' if r['ok'] else 'red'} (want "
                  f"{'green' if green else 'red'}) '{r['move']}'; others max "
                  f"{max(abs(o['error']) for k, o in rows.items() if k != axis):.3f}  {'ok' if good else 'FAIL'}")


def main():
    ok = True
    tgt = pose.load_target("s1")
    t, c = tgt["tape"], tgt["cross_check"]
    R_t = np.array(tgt["R_E_cv"])
    rebuilt = C.angle_between(R_t, R_E_cv(*(tgt["angles"][k] for k in ("depression_deg", "heading_deg", "roll_deg"))))
    print(f"  target: C_E {np.round(tgt['C_E_m'], 5).tolist()} m; {t['height_above_floor_cm']:.3f} cm above the floor, "
          f"{t['from_front_edge_cm']:.3f} from the front edge, {t['from_left_wall_cm']:.3f} from the left wall; "
          f"depression {t['depression_deg']:.3f}, pan {t['pan_toward_back_wall_deg']:.3f} toward the back wall, "
          f"roll {t['roll_deg']:+.3f} deg")
    print(f"  vs Isaac Lab pos_w/quat_w_ros: {c['pos_mm']:.4f} mm / {c['rot_deg']:.4f} deg; tape mismatches "
          f"{tgt['tape_mismatch'] or 'none'}; rebuilt from its 3 angles {rebuilt:.5f} deg")
    ok &= c["pos_mm"] <= 0.01 and c["rot_deg"] <= 0.01 and not tgt["tape_mismatch"] and rebuilt <= 0.001

    tmp = Path(tempfile.mkdtemp())
    (tmp / "board.json").write_text(json.dumps(BOARD))
    T_E_K, _ = C.board_in_E(tmp / "board.json")
    tex, H, _ = C.pdf_texture(300)
    C_t = np.array(tgt["C_E_m"])
    a_t = tuple(tgt["angles"][k] for k in ("depression_deg", "heading_deg", "roll_deg"))

    print("  1. exact geometry")
    for name, (dpos, dang, axis, want, green, move) in [("exact", ((0, 0, 0), (0, 0, 0), "x", 0.0, True, ""))] + list(CASES.items()):
        T_cv_K = np.linalg.inv(C.T(R_E_cv(*np.add(a_t, dang)), C_t + np.array(dpos) / 1000)) @ T_E_K
        rec = exact_rec(T_cv_K, T_E_K)
        rows = {r["axis"]: r for r in pose.target_errors(rec, tgt)}
        good, text = check_case(rows, axis, want, green, move, (0.01, 0.001), (0.01, 0.001))
        ok &= good
        print(f"     {name:8s} {text}")

    print("  2. rendered views")
    rec = pose.measure_frames(views(tex, H, T_E_K, C_t, a_t), K, DIST, 30.0, T_E_K)
    rows = pose.target_errors(rec, tgt)
    lines = pose.target_lines(rows, rec, tgt)
    good = all(abs(r["error"]) <= (1.0 if r["unit"] == "mm" else 0.1) for r in rows) and lines[-1][0].startswith("ALL GREEN")
    ok &= good
    print(f"     exact    RMS {rec['rms_px']:.3f} px, {rec['n_corners']} corners | "
          + "  ".join(f"{r['axis']} {r['error']:+.2f}" for r in rows) + f" | {lines[-1][0]}  {'ok' if good else 'FAIL'}")

    for name, (dpos, dang, axis, want, green, move) in CASES.items():
        rec = pose.measure_frames(views(tex, H, T_E_K, C_t + np.array(dpos) / 1000, tuple(np.add(a_t, dang))),
                                  K, DIST, 30.0, T_E_K)
        rows = {r["axis"]: r for r in pose.target_errors(rec, tgt)}
        good, text = check_case(rows, axis, want, green, move, (0.6, 0.1), (1.0, 0.15))
        ok &= good
        print(f"     {name:8s} {text}")

    print("  3. CLI, headless")
    intr = tmp / "intr.json"
    intr.write_text(json.dumps({"K": K.tolist(), "dist": DIST.tolist(), "note": "test lens (make_synthetic_calib)"}))
    for name, dpos, want in (("exact", (0, 0, 0), "ALL GREEN"), ("y+5mm", (0, 5, 0), "NOT YET")):
        d = tmp / name
        for i, f in enumerate(views(tex, H, T_E_K, C_t + np.array(dpos) / 1000, a_t)):
            capture.save_rgb(d / f"f{i:02d}.png", f)
        p = subprocess.run([sys.executable, "-I", str(GTC / "calib" / "pose.py"), "hud", "--target", "s1", "--source", str(d),
                            "--intrinsics", str(intr), "--board-in-e", str(tmp / "board.json"), "--headless-frames", "5"],
                           capture_output=True, text=True)
        out = p.stdout.strip().splitlines()
        good = p.returncode == 0 and any(line.startswith(want) for line in out) and not any("WARNING" in x for x in out)
        ok &= good
        print(f"     {name:6s} exit {p.returncode}: {out[-1] if out else p.stderr.strip()[-200:]}  {'ok' if good else 'FAIL'}")
    p = subprocess.run([sys.executable, "-I", str(GTC / "calib" / "pose.py"), "hud", "--target", "s1", "--source", str(tmp / "exact"),
                        "--intrinsics", str(intr), "--board-in-e", str(tmp / "missing.json"), "--headless-frames", "5"],
                       capture_output=True, text=True)
    good = p.returncode != 0 and "needs" in p.stderr
    ok &= good
    print(f"     without board_in_E: exit {p.returncode}, '{p.stderr.strip().splitlines()[-1]}'  {'ok' if good else 'FAIL'}")

    print("  4. saved-pose targets with offsets")
    rt = max(C.angle_between(C.rot_from_angles(*ang), R_E_cv(*ang)) for ang in (a_t, tuple(np.add(a_t, (6, -0.5, 1)))))
    ok &= rt <= 1e-9
    print(f"     rot_from_angles vs the test's R_E_cv: {rt:.1e} deg  {'ok' if rt <= 1e-9 else 'FAIL'}")
    poses = tmp / "poses"
    poses.mkdir()
    pose.OUT = poses
    C_b, a_b = C_t + np.array([1.0, -2.0, 0.0]) / 1000, tuple(np.add(a_t, (0.2, -0.3, 0.1)))
    base = exact_rec(np.linalg.inv(C.T(R_E_cv(*a_b), C_b)) @ T_E_K, T_E_K)
    (poses / "r1base.json").write_text(json.dumps(base))
    bt = pose.base_target("r1base")

    def rows_at(dpos, dang, offsets, tol_deg=0.3):
        T_cv_K = np.linalg.inv(C.T(R_E_cv(*np.add(a_b, dang)), C_b + np.array(dpos) / 1000)) @ T_E_K
        return {r["axis"]: r for r in pose.target_errors(exact_rec(T_cv_K, T_E_K), pose.offset_target(bt, offsets), 2.0, tol_deg, tol_deg)}

    for name, dpos, dang, offs in (("R4 +6", (0, 0, 0), (6, 0, 0), {"tilt_down_deg": 6.0}),
                                   ("R5 +1.5", (0, 0, 0), (1.5, 0, 0), {"tilt_down_deg": 1.5}),
                                   ("mixed", (-1.5, 2.0, 2.0), (-5.8, 0.4, -0.3),
                                    {"tilt_down_deg": -5.8, "pan_deg": 0.4, "roll_deg": -0.3, "depth_mm": -1.5,
                                     "lateral_mm": 2.0, "height_mm": 2.0})):
        rows = rows_at(dpos, dang, offs)
        worst = max(abs(r["error"]) for r in rows.values())
        good = worst <= 0.01 and all(r["ok"] for r in rows.values())
        ok &= good
        print(f"     {name:8s} at base + offsets: max |error| {worst:.4f}, all green  {'ok' if good else 'FAIL'}")
    good, text = check_case(rows_at((0, 0, 0), (0, 0, 0), {"tilt_down_deg": 6.0}), "tilt", -6.0, False, "tilt 6.00 deg down",
                            (0.01, 0.001), (0.01, 0.001))
    ok &= good
    print(f"     at base  {text}")
    for tol, green in ((0.3, False), (0.5, True)):
        good, text = check_case(rows_at((0, 0, 0), (6.4, 0, 0), {"tilt_down_deg": 6.0}, tol), "tilt", 0.4, green,
                                "deg up", (0.01, 0.001), (0.01, 0.001))
        ok &= good
        print(f"     +6.4 at {tol} deg  {text}")

    env = {"GTC_POSES_DIR": str(poses), "PATH": "/usr/bin:/bin"}
    for name, dang, want in (("base+6", (6, 0, 0), "ALL GREEN"), ("base+6.5", (6.5, 0, 0), "NOT YET: 1 of 6 outside 2 mm, 0.3 deg")):
        d = tmp / name
        for i, f in enumerate(views(tex, H, T_E_K, C_b, tuple(np.add(a_b, dang)))):
            capture.save_rgb(d / f"f{i:02d}.png", f)
        p = subprocess.run([sys.executable, "-I", str(GTC / "calib" / "pose.py"), "hud", "--base", "r1base", "--offset",
                            "tilt_down_deg=6", "--tol-mm", "2", "--tol-deg", "0.3", "--source", str(d), "--intrinsics",
                            str(intr), "--board-in-e", str(tmp / "board.json"), "--headless-frames", "5"],
                           capture_output=True, text=True, env=env)
        out = p.stdout.strip().splitlines()
        tilt = next((x for x in out if x.startswith("tilt")), "")
        good = p.returncode == 0 and any(line.startswith(want) for line in out)
        ok &= good
        print(f"     {name:8s} exit {p.returncode}: {tilt.strip()} | {out[-1] if out else p.stderr.strip()[-200:]}  "
              f"{'ok' if good else 'FAIL'}")
    for args, why in ((["--target", "s1", "--base", "r1base"], "not both"), (["--offset", "tilt_down_deg=6"], "needs")):
        p = subprocess.run([sys.executable, "-I", str(GTC / "calib" / "pose.py"), "hud", *args, "--source", str(tmp / "exact"),
                            "--intrinsics", str(intr), "--board-in-e", str(tmp / "board.json"), "--headless-frames", "5"],
                           capture_output=True, text=True, env=env)
        good = p.returncode != 0 and why in p.stderr
        ok &= good
        print(f"     {' '.join(args)}: exit {p.returncode}, '{p.stderr.strip().splitlines()[-1]}'  {'ok' if good else 'FAIL'}")
    print("HUD TARGET TEST", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
