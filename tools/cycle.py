#!/usr/bin/env python3
"""Correction-cycle tool (D_software C16): photo -> ground truth -> estimate -> operator card -> applied -> check.

Fixed order (D C16): clean photo, then the board in for ground truth, then compute, then apply with the HUD, then the
board out, then a check photo, then the cycle's trials.

    .venv/bin/python -I tools/cycle.py photo    --cycle M2C1 --kind camera|rack [--suffix check]
        3 frames from the front camera (lock applied and read back), frame 2 is the photo:
        media/real/cycles/<cycle>/<suffix or clean>_{0,1,2}.png; record results/real/cycles/<cycle>.json.
    (ground truth, camera cycles) .venv/bin/python -I calib/pose.py measure --tag <cycle>_gt --square-mm 29.97
    .venv/bin/python -I tools/cycle.py estimate --cycle M2C1 [--method E3] [--nominal s1] [--reference-photo REF.png]
        E3 on the GPU (our Isaac container's python, e3/estimate.py --backend torch): camera cycles differential
        against the nominal reference photo (default: the S1 block reference), rack cycles with the camera at the nominal
        pose. Writes results/real/cycles/<cycle>_E3.json and prints the operator card (correction = -delta):
        camera: the pose.py HUD command (target = the measured ground truth + the correction, tolerance 2 mm / 0.5 deg);
        rack: the push in mm along E x / y and the turn, and the reading tools/scene_check.py should then show.
    .venv/bin/python -I tools/cycle.py check    --cycle M2C1 [--after-tag M2C1_after]
        camera: the pose after the correction (pose.py measure --tag <cycle>_after) against the HUD target; a miss above
        0.5 deg or 2 mm -> redo (B_methods). rack: tools/scene_check.py's reading against the target.
"""
import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

GTC = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(GTC / "calib"), str(GTC / "tools")]
CYC_R = GTC / "results" / "real" / "cycles"
CYC_M = GTC / "media" / "real" / "cycles"
DEFAULT_REF = "media/real/refs/N04-G1_R1/ref_front_median.png"
TOL_MM, TOL_DEG = 2.0, 0.5
HUD_KEYS = (("tilt_down_deg", "tilt_down_deg", 1), ("pan_deg", "pan_deg", 1), ("roll_deg", "roll_deg", 1),
            ("depth_m", "depth_mm", 1000), ("lateral_m", "lateral_mm", 1000), ("height_m", "height_mm", 1000))


def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def load(cycle):
    p = CYC_R / f"{cycle}.json"
    return json.loads(p.read_text()) if p.exists() else {"cycle": cycle, "steps": []}


def save(rec):
    CYC_R.mkdir(parents=True, exist_ok=True)
    (CYC_R / f"{rec['cycle']}.json").write_text(json.dumps(rec, indent=1, default=float))


def cmd_photo(a):
    import capture
    import camera_lock
    rec = load(a.cycle)
    rec.setdefault("kind", a.kind)
    if rec["kind"] != a.kind:
        raise SystemExit(f"STOP: {a.cycle} is a {rec['kind']} cycle")
    lock_ok = camera_lock.cmd_apply("front", write=False) == 0 if a.source.startswith("camera:") else None
    if lock_ok is False:
        raise SystemExit("STOP: camera lock does not read back; run camera_lock.py apply front")
    src = capture.open_source(a.source)
    try:
        frames = [src.read() for _ in range(3)]
    finally:
        src.close()
    name = a.suffix or "clean"
    for i, f in enumerate(frames):
        capture.save_rgb(CYC_M / a.cycle / f"{name}_{i}.png", f)
    rec[f"{name}_photo"] = f"media/real/cycles/{a.cycle}/{name}_1.png"
    rec["steps"].append({"utc": utc(), "step": f"photo {name}", "lock_readback_ok": lock_ok})
    save(rec)
    print(f"{a.cycle}: {name} photo -> {rec[f'{name}_photo']}")
    return 0


def run_e3(mode, photo, out, nominal_pose, reference_photo=None):
    W = "/workspace/gtc"
    cmd = ["sim/run_sim.sh", "e3cycle", "python", "/workspace/e3/estimate.py", mode, "--backend", "torch",
           "--scene-cache", "/workspace/e3/cache/scene.npz", "--photo", f"{W}/{photo}",
           "--intrinsics", f"{W}/config/c920_intrinsics.json", "--frames", f"{W}/results/c1/frames_sim.json",
           "--out", f"{W}/{out}", "--png", f"{W}/{str(out).replace('.json', '.png')}"]
    if mode == "camera":
        cmd += ["--nominal-pose", f"{W}/{nominal_pose}"] + (["--reference-photo", f"{W}/{reference_photo}"] if reference_photo else [])
    else:
        cmd += ["--camera-pose", f"{W}/{nominal_pose}"]
    p = subprocess.run(cmd, cwd=GTC, env={"NET": "none", **__import__("os").environ}, capture_output=True, text=True)
    if p.returncode != 0 or not (GTC / out).exists():
        raise SystemExit(f"STOP: E3 failed ({p.returncode}):\n{p.stdout[-1500:]}\n{p.stderr[-1500:]}")
    return json.loads((GTC / out).read_text())


def cmd_estimate(a):
    rec = load(a.cycle)
    if "clean_photo" not in rec:
        raise SystemExit(f"STOP: no clean photo for {a.cycle}; run `cycle.py photo` first")
    out = Path("results/real/cycles") / f"{a.cycle}_{a.method}.json"
    nominal = f"results/poses/{a.nominal}.json"
    if a.method != "E3":
        raise SystemExit("STOP: only E3 runs here (E1 is judged on photos only under K4; e1/e1_estimate.py)")
    if rec["kind"] == "camera":
        est = run_e3("camera", rec["clean_photo"], out, nominal, a.reference_photo or DEFAULT_REF)
        corr = {hud: -mul * est["camera_delta"][k] for k, hud, mul in HUD_KEYS}
        gt_tag = f"{a.cycle}_gt"
        if not (GTC / "results" / "poses" / f"{gt_tag}.json").exists():
            print(f"NOTE: no ground truth pose {gt_tag} yet (calib/pose.py measure --tag {gt_tag}); the HUD needs it")
        hud = (f".venv/bin/python -I calib/pose.py hud --base {gt_tag} " +
               " ".join(f"--offset {k}={v:+.2f}" for k, v in corr.items()) + f" --tol-mm {TOL_MM:g} --tol-deg {TOL_DEG:g}")
        rec["E3"] = {"estimate": str(out), "correction_hud": corr, "hud_command": hud}
        print(f"{a.cycle} E3 camera delta (actual - nominal): " +
              ", ".join(f"{k} {est['camera_delta'][k]:+.4f}" for k, _, _ in HUD_KEYS))
        print("OPERATOR CARD (camera): move the camera by the correction with the HUD; board on the sled first:\n  " + hud)
    else:
        est = run_e3("rack", rec["clean_photo"], out, nominal)
        d = est["rack_delta"]
        corr = {"x_mm": -1000 * d["x_m"], "y_mm": -1000 * d["y_m"], "yaw_deg": -d["yaw_deg"]}
        rec["E3"] = {"estimate": str(out), "correction": corr}
        words = []
        if abs(corr["x_mm"]) >= 0.5:
            words.append(f"{abs(corr['x_mm']):.1f} mm {'toward the back wall' if corr['x_mm'] > 0 else 'toward the robot'}")
        if abs(corr["y_mm"]) >= 0.5:
            words.append(f"{abs(corr['y_mm']):.1f} mm {'toward the camera wall' if corr['y_mm'] > 0 else 'toward the right wall'}")
        if abs(corr["yaw_deg"]) >= 0.2:
            words.append(f"turn {abs(corr['yaw_deg']):.1f} deg {'counter-clockwise' if corr['yaw_deg'] > 0 else 'clockwise'} (from above, about corner O)")
        print(f"{a.cycle} E3 rack delta (actual - nominal): x {1000 * d['x_m']:+.1f} mm, y {1000 * d['y_m']:+.1f} mm, yaw {d['yaw_deg']:+.2f} deg")
        print("OPERATOR CARD (rack): move the rack " + ("; ".join(words) or "nowhere (within 0.5 mm / 0.2 deg)") +
              ".\n  Check with: .venv/bin/python -I tools/scene_check.py --pose " + a.nominal +
              " (its rack line should change by the same amounts)")
    rec["steps"].append({"utc": utc(), "step": f"estimate {a.method}", "out": str(out)})
    save(rec)
    return 0


def cmd_check(a):
    import charuco as C
    rec = load(a.cycle)
    if rec.get("kind") != "camera":
        raise SystemExit("STOP: check is for camera cycles; for a rack cycle compare tools/scene_check.py readings")
    gt = json.loads((GTC / "results" / "poses" / f"{a.cycle}_gt.json").read_text())
    af = json.loads((GTC / "results" / "poses" / f"{a.after_tag or a.cycle + '_after'}.json").read_text())
    d = C.delta({"angles": gt["angles"], "C_E_m": gt["C_E_m"], "R_E_cv": gt["R_E_cv"]},
                {"angles": af["angles"], "C_E_m": af["C_E_m"], "R_E_cv": af["R_E_cv"]})
    corr = rec["E3"]["correction_hud"]
    miss = {"tilt_down_deg": d["tilt_down_deg"] - corr["tilt_down_deg"], "pan_deg": d["pan_deg"] - corr["pan_deg"],
            "roll_deg": d["roll_deg"] - corr["roll_deg"], "depth_mm": 1000 * d["depth_m"] - corr["depth_mm"],
            "lateral_mm": 1000 * d["lateral_m"] - corr["lateral_mm"], "height_mm": 1000 * d["height_m"] - corr["height_mm"]}
    ok = all(abs(miss[k]) <= TOL_DEG for k in ("tilt_down_deg", "pan_deg", "roll_deg")) and \
        all(abs(miss[k]) <= TOL_MM for k in ("depth_mm", "lateral_mm", "height_mm"))
    rec["check"] = {"utc": utc(), "applied_vs_correction_miss": miss, "pass": ok}
    rec["steps"].append({"utc": utc(), "step": "check", "pass": ok})
    save(rec)
    print(f"{a.cycle}: applied move vs E3's correction: " + ", ".join(f"{k} {v:+.2f}" for k, v in miss.items()) +
          (" -> OK" if ok else f" -> REDO (limits {TOL_DEG} deg / {TOL_MM} mm)"))
    return 0 if ok else 1


def main(argv):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("photo")
    p.add_argument("--cycle", required=True)
    p.add_argument("--kind", choices=["camera", "rack"], required=True)
    p.add_argument("--suffix")
    p.add_argument("--source", default="camera:front")
    p = sub.add_parser("estimate")
    p.add_argument("--cycle", required=True)
    p.add_argument("--method", default="E3")
    p.add_argument("--nominal", default="s1", help="results/poses/<tag>.json: the real nominal camera pose")
    p.add_argument("--reference-photo", help=f"camera cycles: the nominal reference photo (default {DEFAULT_REF})")
    p = sub.add_parser("check")
    p.add_argument("--cycle", required=True)
    p.add_argument("--after-tag")
    a = ap.parse_args(argv)
    return {"photo": cmd_photo, "estimate": cmd_estimate, "check": cmd_check}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
