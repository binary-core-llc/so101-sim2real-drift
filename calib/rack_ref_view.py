#!/usr/bin/env python3
"""Live rack view against a block reference at a measured camera pose (Nov 9, S1): the trial runner's own pre-trial
checks (drift, rack, clean view, light, mat) on the live front camera, the reference's rack outline in green and the rack
now in magenta (the runner's yellow mask), and the push and turn that bring the rack back, until the checks pass.

    .venv/bin/python -I calib/rack_ref_view.py [--ref N04-G1_R1] [--pose s1]        # q quits
Why: calib/rack_view.py takes its mm from the L-jig board frame at R0, which does not hold at S1. Here the push comes
from the yellow-mask centroids (reference and now) lifted to the rack's mid height with the measured pose (a guide,
about +-20 %), and the turn from the runner's mask rotation, scaled to a turn about the vertical with the rack's model
projected at the pose. Push words follow B's E axes (+x away from the robot, +y toward the camera wall); a turn is given
seen from above. The rack sits inside the drift check's static region, so a small turn of the rack also moves the drift
reading (N04-013: rack 0.46 deg in the image -> drift 1.65 px, with the mat edges at 0.2-0.3 px). AIM = rack and drift
pass with drift <= --aim-drift px, the rack's image turn <= --aim-deg and its centroid <= --aim-px. Hands out of the
view while it reads; the runner's check with the door on stays the one that counts.
On quit: results/rig/rack_ref_view_last.json and rack_ref_view_last.png.
"""
import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import cv2
import numpy as np

GTC = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(GTC / "calib"), str(GTC / "real"), str(GTC / "tools")]

import camera_lock  # noqa: E402
import capture  # noqa: E402
import live  # noqa: E402
import scene_check as SC  # noqa: E402
import trial_runner as T  # noqa: E402
import vial_check as V  # noqa: E402

GREEN, MAGENTA = (0, 255, 0), (255, 0, 255)


def centroid(m):
    return np.argwhere(m).mean(axis=0)[::-1]


def lift(uv, R, C, K, dist, z):
    """Distorted pixel -> point on the plane z in E."""
    u = cv2.undistortPoints(np.float32([[uv]]), K, dist, P=K).reshape(2)
    d = np.array([(u[0] - K[0, 2]) / K[0, 0], (u[1] - K[1, 2]) / K[1, 1], 1.0]) @ R.T
    return C + (z - C[2]) / d[2] * d


def yaw_per_image_deg(R, C, K, shape, z0, h):
    """Turn about the vertical in E (deg) per degree of the runner's image rotation, from the rack model at the pose."""
    m0, _ = SC.rack_mask(R, C, K, shape, 0, 0, 0.0, z0, h)
    m1, _ = SC.rack_mask(R, C, K, shape, 0, 0, 1.0, z0, h)
    return 1.0 / T.rack_pose(m0, m1, T.CHECKS)["rot_deg"]


def zooms(vis, corners, half=30, s=4):
    """4x crops around the reference outline's top corners (a 0.5 deg turn is about 1 px at full size)."""
    out = []
    for x, y in corners:
        x0, y0 = int(np.clip(x - half, 0, vis.shape[1] - 2 * half)), int(np.clip(y - half, 0, vis.shape[0] - 2 * half))
        out.append(cv2.resize(vis[y0:y0 + 2 * half, x0:x0 + 2 * half], None, fx=s, fy=s, interpolation=cv2.INTER_NEAREST))
    row = np.hstack(out)
    return np.hstack([row, np.zeros((row.shape[0], vis.shape[1] - row.shape[1], 3), np.uint8)])


def turn_words(dyaw):
    """Turn of the rack now against the reference (E yaw, deg, + = counter-clockwise seen from above) -> the undo."""
    if abs(dyaw) < 0.05:
        return "no turn"
    return f"turn {abs(dyaw):.2f} deg {'clockwise' if dyaw > 0 else 'counter-clockwise'} seen from above"


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", default="N04-G1_R1")
    ap.add_argument("--pose", default="s1")
    ap.add_argument("--source", default="camera:front")
    ap.add_argument("--aim-drift", type=float, default=1.0)
    ap.add_argument("--aim-deg", type=float, default=0.2)
    ap.add_argument("--aim-px", type=float, default=1.0)
    ap.add_argument("--mat-top-z", type=float, default=0.035)
    ap.add_argument("--rack-h-cm", type=float, default=7.85)
    ap.add_argument("--poses-dir", default=str(GTC / "results" / "poses"))
    ap.add_argument("--intrinsics", default=str(GTC / "config" / "c920_intrinsics.json"))
    ap.add_argument("--headless-frames", type=int)
    ap.add_argument("--out", default=str(GTC / "results" / "rig" / "rack_ref_view_last"))
    a = ap.parse_args(argv)
    rdir = GTC / "media" / "real" / "refs" / a.ref
    ref = capture.load_rgb(rdir / "ref_front_median.png")
    lo, hi = T.CHECKS["yellow_hsv_lo"], T.CHECKS["yellow_hsv_hi"]
    ref_m = T.yellow_mask(ref, lo, hi)
    ref_cnt, _ = cv2.findContours(ref_m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    pts = max(ref_cnt, key=cv2.contourArea).reshape(-1, 2)
    corners = [pts[np.argmin(pts.sum(axis=1))], pts[np.argmax(pts[:, 0] - pts[:, 1])]]   # top-left, top-right
    R, C, K, dist = V.load_camera(Path(a.poses_dir) / f"{a.pose}.json", a.intrinsics)
    h = a.rack_h_cm / 100
    z_mid = a.mat_top_z + 0.5 * h
    k_yaw = yaw_per_image_deg(R, C, K, ref.shape[:2], a.mat_top_z, h)
    p_ref = lift(centroid(ref_m), R, C, K, dist, z_mid)
    if a.source.startswith("camera:"):
        if camera_lock.cmd_apply(a.source.split(":", 1)[1], write=True) != 0:
            raise SystemExit("STOP: camera lock does not read back")
    src = capture.open_source(a.source)
    st = {"rec": None, "view": None}

    def step():
        f = src.read()
        c, _ = T.run_checks(rdir, f, T.CHECKS)
        d, rk = c["drift"], c["rack"]
        cur_m = T.yellow_mask(f, lo, hi)
        vis = f.copy()
        cv2.drawContours(vis, ref_cnt, -1, GREEN, 1)
        cnt, _ = cv2.findContours(cur_m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        cv2.drawContours(vis, cnt, -1, MAGENTA, 1)
        lines = []
        if "rot_deg" in rk:
            e = 1000 * (lift(centroid(cur_m), R, C, K, dist, z_mid) - p_ref)
            dyaw = rk["rot_deg"] * k_yaw
            move = f"{SC.push(e[0], e[1])}; {turn_words(dyaw)}"
            aim = (rk["pass"] and d["pass"] and d["max_px"] <= a.aim_drift and abs(rk["rot_deg"]) <= a.aim_deg
                   and rk["centroid_err_px"] <= a.aim_px)
            lines.append(f"rack {rk['centroid_err_px']:.2f} px, turn {rk['rot_deg']:+.2f} deg in the image "
                         f"(runner: 2 px, 1 deg) {'PASS' if rk['pass'] else 'FAIL'}; drift {d['max_px']:.2f} px "
                         f"(limit {d['limit_px']:.2f}) {'PASS' if d['pass'] else 'FAIL'}")
            lines.append(f"move: {move} (E: {e[0]:+.1f} / {e[1]:+.1f} mm, turn {dyaw:+.2f} deg)")
        else:
            aim, move, e, dyaw = False, None, None, None
            lines.append(f"rack: {rk.get('reason', 'not measured')}")
        others = {k: c[k]["pass"] for k in ("clean_view", "light", "mat")}
        lines.append("clean view {}, light {:.3f}, mat {}".format(
            "PASS" if others["clean_view"] else "FAIL", c["light"]["ratio"],
            "PASS" if others["mat"] else "skipped" if others["mat"] is None else "FAIL") + "  (door on for the real check)")
        head = (f"rack vs {a.ref} at {a.pose}: " + ("AIM - ready (hands out, door on, then the runner)" if aim else
                "rack and drift PASS (outside AIM)" if rk.get("pass") and d["pass"] else "rack or drift FAIL"))
        st["rec"] = {"utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "ref": a.ref, "pose": a.pose,
                     "aim": aim, "move": move, "push_E_mm": None if e is None else [round(float(v), 2) for v in e[:2]],
                     "turn_E_deg": None if dyaw is None else round(float(dyaw), 3), "yaw_per_image_deg": round(k_yaw, 3),
                     "checks": c}
        st["view"] = np.vstack([vis, zooms(vis, corners), live.text_panel([head] + lines + ["q quit"], vis.shape[1])])
        if a.headless_frames is not None:
            print("\n".join([head] + lines))
        return st["view"], []

    try:
        live.run(step, {"q": lambda: "quit"}, f"rack vs {a.ref}", headless=a.headless_frames is not None,
                 max_frames=a.headless_frames)
    finally:
        src.close()
        if st["rec"] is not None:
            Path(a.out).parent.mkdir(parents=True, exist_ok=True)
            Path(a.out + ".json").write_text(json.dumps(st["rec"], indent=1, default=str))
            capture.save_rgb(a.out + ".png", st["view"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
