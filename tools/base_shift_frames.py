#!/usr/bin/env python3
"""When did the robot base move? (Nov 9, after N05-012.) Saved frames only, no robot.

    .venv/bin/python -I tools/base_shift_frames.py [--ref-trial N05-012] [--out results/rig/base_shift_frames]
The sled checks of 11:25 and 11:27 PST (results/poses/s1_check_n05012*.json) put the base turned about 2.6 deg
counter-clockwise seen from above against s1, about a point near the pan axis (calib/base_view.base_move). Three
series, each against the reference trial's own frame (N05-012, whose first frames come before its trial):
A. front, start pose: kf/chunk_000_front.png of every trial at S1 since --since-utc (the first observation, the arm at
   the course start pose, a commanded pose). The arm's shift = normalised cross-correlation of the blurred grey image
   over the reference's orange parts (+-30 px, sub-pixel by a parabola), minus the scene's shift (camera drift: walls
   and mat outside the runner's ignore zones, rack, arm and large changes left out), minus the shift the start-joint
   differences alone give (course USD forward kinematics, tools/arm_fk.py, through the measured S1 camera). mm at the
   arm's mean depth. Expected for the sled's base move: the same forward kinematics with the base moved.
B. wrist, start pose: kf/chunk_000_wrist.png. ECC (Euclidean) on the mat's outer edges (rack, tubes, gripper left out).
   The image x shift is fitted on the start readings of shoulder_pan and wrist_roll (least squares over the trials);
   the residual is given as an equivalent base turn with the fitted px per pan unit and 1.1885 deg per pan unit (the
   real calibrated pan range, 237.7 deg over 200 units, addendum entry 1). A base turn and a pan turn of the same angle
   about nearly the same vertical axis move the wrist camera alike.
C. front, the base's left flange (the perforated tab next to the camera wall, image x 556-638, y 268-312): its image
   rotation (ECC Euclidean) against the reference trial's pre-trial frame, in every saved frame where it shows: the DEV
   clean photos of Nov 8 (taken with the sled's last seatings, base at s1), the block references, every trial's
   pre-trial and start frames, and every keyframe of the reference trial. Expected for the sled's base move: the
   rotation of the flange's projected model points. (The arm passing over the flange, pan below about -10, upsets it.)
D. control for C: the same reading in the other trials' keyframes with the arm turned right (pan >= --control-pan),
   where the arm is away from the flange as in the reference trial's last chunks. Slow (several minutes).
Writes <out>.json and <out>.png (series C over time, and the flange crops).
"""
import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import cv2
import numpy as np

GTC = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(GTC / "tools"), str(GTC / "calib")]

import arm_fk as A  # noqa: E402
import capture  # noqa: E402
import pose as P  # noqa: E402

COURSE = {"shoulder_pan.pos": (-110, 110), "shoulder_lift.pos": (-100, 100), "elbow_flex.pos": (-100, 90),
          "wrist_flex.pos": (-95, 95), "wrist_roll.pos": (-160, 160), "gripper.pos": (-10, 100)}   # posecheck_compare
ARM_LINKS = ("shoulder", "upper_arm", "lower_arm", "wrist", "gripper", "jaw")
FLANGE = (556, 638, 268, 312)                     # x0, x1, y0, y1 (px, front frame at S1)
DEG_PER_PAN_UNIT = 237.7 / 200
ECC_CRIT = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 300, 1e-7)


def to_sim_rad(v):
    out = []
    for k, (lo, hi) in COURSE.items():
        n = v[k] / 100.0 if k == "gripper.pos" else (v[k] + 100.0) / 200.0
        out.append(np.radians(lo + n * (hi - lo)))
    return out


def hsv(rgb):
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)


def orange(rgb):
    return cv2.inRange(hsv(rgb), (0, 150, 50), (14, 255, 255)) > 0


def yellow(rgb):
    return cv2.inRange(hsv(rgb), (15, 90, 90), (38, 255, 255)) > 0


def dil(m, r):
    return cv2.dilate(m.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))) > 0


def grey(rgb, s=1.5):
    return cv2.GaussianBlur(cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32), (0, 0), s)


def load(p):
    return capture.load_rgb(p)


def local(p):
    p = str(p)
    return GTC / p.split("/gtc/", 1)[1] if "/gtc/" in p else Path(p)


def pst(utc):
    return (dt.datetime.fromisoformat(utc) - dt.timedelta(hours=8)).strftime("%b %d %H:%M:%S")


def ncc_shift(ref, cur, mask, s=30):
    """Shift (dx, dy) of cur against ref over the ref pixels in mask: cur(x + dx, y + dy) ~ ref(x, y)."""
    ys, xs = np.nonzero(mask)
    keep = (xs >= s) & (xs < ref.shape[1] - s) & (ys >= s) & (ys < ref.shape[0] - s)
    ys, xs = ys[keep], xs[keep]
    if len(xs) < 200:
        return None, None
    a = ref[ys, xs] - ref[ys, xs].mean()
    a /= np.linalg.norm(a)
    sc = np.full((2 * s + 1, 2 * s + 1), -1.0)
    for dy in range(-s, s + 1):
        for dx in range(-s, s + 1):
            b = cur[ys + dy, xs + dx]
            b = b - b.mean()
            sc[dy + s, dx + s] = float(a @ b / (np.linalg.norm(b) + 1e-9))
    iy, ix = np.unravel_index(np.argmax(sc), sc.shape)

    def sub(m1, m0, p1):
        d = m1 - 2 * m0 + p1
        return 0.0 if d >= 0 else 0.5 * (m1 - p1) / d
    fx = sub(sc[iy, ix - 1], sc[iy, ix], sc[iy, ix + 1]) if 0 < ix < 2 * s else 0.0
    fy = sub(sc[iy - 1, ix], sc[iy, ix], sc[iy + 1, ix]) if 0 < iy < 2 * s else 0.0
    return np.array([ix - s + fx, iy - s + fy]), float(sc[iy, ix])


def ecc_euclid(ref_g, cur_g, mask, centre):
    """ECC Euclidean from ref to cur over mask: image rotation (deg) and the shift of centre (px), and the ECC score."""
    W = np.eye(2, 3, dtype=np.float32)
    try:
        cc, W = cv2.findTransformECC(ref_g, cur_g, W, cv2.MOTION_EUCLIDEAN, ECC_CRIT, mask.astype(np.uint8), 1)
    except cv2.error:
        return None
    return float(np.degrees(np.arctan2(W[1, 0], W[0, 0]))), W[:, :2] @ centre + W[:, 2] - centre, float(cc)


class Cam:
    def __init__(self, pose="s1"):
        pr = P.load(pose)
        j = json.loads((GTC / "config" / "c920_intrinsics.json").read_text())
        self.K, self.dist = np.array(j["K"]), np.array(j["dist"]).ravel()
        R, C = np.array(pr["R_E_cv"]), np.array(pr["C_E_m"])
        self.Rcv, self.C = R.T, C
        self.rvec, self.tvec = cv2.Rodrigues(R.T)[0], -R.T @ C

    def project(self, X):
        uv = cv2.projectPoints(X.reshape(-1, 1, 3), self.rvec, self.tvec, self.K, self.dist)[0].reshape(-1, 2)
        return uv, (X - self.C) @ self.Rcv[2]


class Robot:
    def __init__(self):
        st, self.chain = A.load_chain()
        tris = A.link_meshes(st)
        self.pts = {k: np.unique(tris[k].reshape(-1, 3), axis=0)[::7] for k in ARM_LINKS + ("base",)}

    def points(self, links, joints, M=None):
        poses = A.fk(self.chain, to_sim_rad(joints) if joints else [0.0] * 6)
        X = np.vstack([self.pts[k] @ poses[k][:3, :3].T + poses[k][:3, 3] for k in links])
        return X if M is None else X @ M[:3, :3].T + M[:3, 3]


def in_mask(cam, X, mask):
    u, z = cam.project(X)
    h, w = mask.shape
    ui = np.round(u).astype(int)
    ok = (z > 0) & (ui[:, 0] >= 0) & (ui[:, 0] < w) & (ui[:, 1] >= 0) & (ui[:, 1] < h)
    ok[ok] = mask[ui[ok, 1], ui[ok, 0]]
    return ok


def sled_move(checks):
    """Mean base move of the sled checks against s1, as a 4x4 map of base points (E at s1)."""
    ref = P.load("s1")
    Ra, Ca, _ = P.frame_E(ref)
    yaws, ts = [], []
    for t in checks:
        Rb, Cb, _ = P.frame_E(P.load(t))
        RM = Ra @ Rb.T
        yaws.append(np.arctan2(RM[1, 0], RM[0, 0]))
        ts.append(Ca - RM @ Cb)
    y = float(np.mean(yaws))
    M = np.eye(4)
    M[:3, :3] = [[np.cos(y), -np.sin(y), 0], [np.sin(y), np.cos(y), 0], [0, 0, 1]]
    M[:3, 3] = np.mean(ts, axis=0)
    return M, float(np.degrees(y))


def wrist_edges(rgb):
    """Band around the mat's outer edges in a wrist frame (rack, tubes and gripper left out)."""
    h = hsv(rgb)
    dark = (h[..., 2] < 90).astype(np.uint8)
    _, lab, st, _ = cv2.connectedComponentsWithStats(dark)
    m = (lab == 1 + np.argmax(st[1:, cv2.CC_STAT_AREA])).astype(np.uint8)
    cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    fill = np.zeros_like(m)
    cv2.drawContours(fill, cnts, -1, 1, -1)
    edge = cv2.morphologyEx(fill, cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0
    edge &= ~dil(cv2.inRange(h, (0, 90, 90), (38, 255, 255)) > 0, 15) & ~dil((h[..., 2] > 150) & (fill > 0), 10)
    edge[:12], edge[-12:], edge[:, :12], edge[:, -12:] = False, False, False, False
    return dil(edge, 6)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref-trial", default="N05-012")
    ap.add_argument("--since-utc", default="2026-11-08T21:11:00+00:00", help="the sled's last seating (D04)")
    ap.add_argument("--ignore-from", default="N05-RACK_R2")
    ap.add_argument("--checks", nargs="*", default=["s1_check_n05012", "s1_check_n05012_b"])
    ap.add_argument("--control-pan", type=float, default=40.0, help="series D: pan reading from which a keyframe counts")
    ap.add_argument("--out", default=str(GTC / "results" / "rig" / "base_shift_frames"))
    a = ap.parse_args(argv)
    recs = [json.loads(l) for l in open(GTC / "results" / "real" / "trials.jsonl")]
    trials = [r for r in recs if r.get("t_launch") and r["t_launch"] >= a.since_utc and r.get("start_joints")]
    ref_rec = [r for r in trials if r["uid"] == a.ref_trial][-1]
    media = {r["uid"]: local(r["pre_front"]).parent for r in trials}
    ignore = cv2.imread(str(GTC / "media" / "real" / "refs" / a.ignore_from / "ignore_mask.png"), cv2.IMREAD_GRAYSCALE) > 0
    cam, robot = Cam(), Robot()
    f_px = float(cam.K[0, 0])
    M, yaw = sled_move(a.checks)
    out = {"utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "ref_trial": a.ref_trial,
           "sled_base_move": {"checks": a.checks, "yaw_deg": round(yaw, 3), "t_mm": [round(1000 * v, 2) for v in M[:3, 3]]}}

    # A. front, start pose
    R = load(media[a.ref_trial] / "kf" / "chunk_000_front.png")
    Rg = grey(R)
    arm_m = dil(orange(R), 4) & ~dil(yellow(R), 6)
    arm_m[:, :380] = False
    X0 = robot.points(ARM_LINKS, ref_rec["start_joints"])
    ok = in_mask(cam, X0, arm_m)
    u0, z0 = cam.project(X0[ok])
    exp = (cam.project(robot.points(ARM_LINKS, ref_rec["start_joints"], M)[ok])[0] - u0).mean(axis=0)
    z_arm = float(z0.mean())
    mm = lambda px: float(np.hypot(*px)) * z_arm / f_px * 1000      # noqa: E731
    out["A_front_start"] = {"expected_px": [round(float(v), 2) for v in exp], "expected_mm": round(mm(exp), 1),
                            "arm_depth_m": round(z_arm, 3), "rows": []}
    print(f"A. front, start pose, against {a.ref_trial}: the sled's base move would shift the arm "
          f"({exp[0]:+.2f}, {exp[1]:+.2f}) px = {mm(exp):.1f} mm at {z_arm:.3f} m")
    for r in trials:
        C = load(media[r["uid"]] / "kf" / "chunk_000_front.png")
        Cg = grey(C)
        static = ~ignore & ~dil(yellow(R) | yellow(C), 12) & ~dil(orange(R) | orange(C), 12) & ~dil(np.abs(Rg - Cg) > 60, 9)
        s_sh, _ = ncc_shift(Rg, Cg, static & (Rg > 8), s=8)
        a_sh, a_sc = ncc_shift(Rg, Cg, arm_m)
        u1 = cam.project(robot.points(ARM_LINKS, r["start_joints"])[ok])[0]
        j_sh = (u1 - u0).mean(axis=0)
        rel = a_sh - s_sh - j_sh
        row = {"uid": r["uid"], "t0_utc": r["t0_first_query"], "scene_px": s_sh.round(2).tolist(),
               "arm_px": a_sh.round(2).tolist(), "arm_ncc": round(a_sc, 3), "joints_px": j_sh.round(2).tolist(),
               "arm_vs_scene_px": rel.round(2).tolist(), "norm_px": round(float(np.hypot(*rel)), 2), "mm": round(mm(rel), 1)}
        out["A_front_start"]["rows"].append(row)
        print(f"  {r['uid']:8s} {pst(r['t0_first_query'])} PST  arm {row['arm_px']} scene {row['scene_px']} joints "
              f"{row['joints_px']} -> ({rel[0]:+.2f}, {rel[1]:+.2f}) = {row['norm_px']:.2f} px, {row['mm']:.1f} mm")

    # B. wrist, start pose
    W0 = load(media[a.ref_trial] / "kf" / "chunk_000_wrist.png")
    W0g, W0m = grey(W0, 2), wrist_edges(W0)
    rows = []
    for r in trials:
        Wc = load(media[r["uid"]] / "kf" / "chunk_000_wrist.png")
        e = ecc_euclid(W0g, grey(Wc, 2), W0m & wrist_edges(Wc), np.zeros(2))
        j, j0 = r["start_joints"], ref_rec["start_joints"]
        rows.append({"uid": r["uid"], "t0_utc": r["t0_first_query"], "rot_deg": round(e[0], 3),
                     "tx_px": round(float(e[1][0]), 2), "ty_px": round(float(e[1][1]), 2), "ecc": round(e[2], 3),
                     "d_pan_units": round(j["shoulder_pan.pos"] - j0["shoulder_pan.pos"], 3),
                     "d_wrist_roll_units": round(j["wrist_roll.pos"] - j0["wrist_roll.pos"], 3)})
    X = np.array([[q["d_pan_units"], q["d_wrist_roll_units"], 1.0] for q in rows])
    y = np.array([q["tx_px"] for q in rows])
    coef = np.linalg.lstsq(X, y, rcond=None)[0]
    px_per_deg = coef[0] / DEG_PER_PAN_UNIT
    for q, res in zip(rows, y - X @ coef):
        q["tx_resid_px"], q["base_turn_equiv_deg"] = round(float(res), 2), round(float(-res / px_per_deg), 3)
    out["B_wrist_start"] = {"fit_px": {"per_pan_unit": round(float(coef[0]), 3), "per_wrist_roll_unit": round(float(coef[1]), 3),
                                       "const": round(float(coef[2]), 3)},
                            "px_per_deg_turn": round(float(px_per_deg), 3),
                            "expected_px_for_sled_move": round(abs(yaw * px_per_deg), 1), "rows": rows}
    print(f"B. wrist, start pose: x shift = {coef[0]:+.2f} px per pan unit ({px_per_deg:+.2f} px per deg) "
          f"{coef[1]:+.2f} px per wrist-roll unit; the sled's {yaw:.2f} deg turn would be {abs(yaw * px_per_deg):.1f} px")
    for q in rows:
        print(f"  {q['uid']:8s} {pst(q['t0_utc'])} PST  tx {q['tx_px']:+6.2f} px (pan {q['d_pan_units']:+.2f}, roll "
              f"{q['d_wrist_roll_units']:+.2f}) -> residual {q['tx_resid_px']:+.2f} px = {q['base_turn_equiv_deg']:+.2f} deg")

    # C. the left flange
    x0, x1, y0, y1 = FLANGE
    centre = np.array([(x0 + x1) / 2, (y0 + y1) / 2])
    cx0, cy0 = x0 - 40, y0 - 40                                     # ECC on a crop around the flange (fast)
    crop = lambda p: grey(load(p), 1.2)[cy0:y1 + 40, cx0:x1 + 40]      # noqa: E731
    Fref = crop(media[a.ref_trial] / "pre_front.png")
    fm = np.zeros(Fref.shape, bool)
    fm[y0 - cy0:y1 - cy0, x0 - cx0:x1 - cx0] = True
    centre_c = centre - [cx0, cy0]
    Xb = robot.points(("base",), None)
    u0, _ = cam.project(Xb)
    sel = (u0[:, 0] >= x0) & (u0[:, 0] < x1) & (u0[:, 1] >= y0) & (u0[:, 1] < y1) & (Xb[:, 2] > 0.03)
    u1, _ = cam.project(robot.points(("base",), None, M))
    We, _ = cv2.estimateAffinePartial2D(u0[sel].astype(np.float32), u1[sel].astype(np.float32))
    exp_rot = float(np.degrees(np.arctan2(We[1, 0], We[0, 0])))
    items = []
    for k in ("D01", "D02", "D03", "D04"):
        d = json.loads((GTC / "results" / "photoset_dev" / f"{k}.json").read_text())
        items.append((d["captured_utc"], f"{k} clean (sled seated, base at s1)", GTC / d["files"]["clean"]))
    for tag in ("N04-G1_R1_1325_day_20261109T070521Z", "N04-G1_R1", "N05-C_R1", "N05-RACK_R1", "N05-RACK_R2"):
        m = json.loads((GTC / "media" / "real" / "refs" / tag / "meta.json").read_text())
        items.append((m["utc"], "ref " + tag.split("_2026")[0], GTC / "media" / "real" / "refs" / tag / "ref_front_median.png"))
    for r in trials:
        items.append((r["t_launch"], f"{r['uid']} pre", media[r["uid"]] / "pre_front.png"))
        items.append((r["t0_first_query"], f"{r['uid']} start", media[r["uid"]] / "kf" / "chunk_000_front.png"))
    t0 = dt.datetime.fromisoformat(ref_rec["t0_first_query"])
    for s in map(json.loads, open(local(ref_rec["steps_jsonl"]))):
        if s["chunk"] == 0:
            continue
        t = (t0 + dt.timedelta(seconds=s["t_query_s"])).isoformat()
        items.append((t, f"{a.ref_trial} chunk {s['chunk']:02d} ({s['t_query_s']:.1f} s, pan {s['joints']['shoulder_pan.pos']:+.1f})",
                      media[a.ref_trial] / "kf" / f"chunk_{s['chunk']:03d}_front.png"))
    out["C_flange"] = {"region_px": FLANGE, "expected_rot_deg_for_sled_move": round(exp_rot, 2), "rows": []}
    print(f"C. left flange, image rotation against {a.ref_trial} pre: the sled's base move would turn it {exp_rot:+.2f} deg")
    for t, lab, p in sorted(items):
        e = ecc_euclid(Fref, crop(p), fm, centre_c)
        row = {"utc": t, "label": lab, "path": str(Path(p).relative_to(GTC))}
        if e is not None:
            row.update({"rot_deg": round(e[0], 2), "centre_shift_px": e[1].round(2).tolist(), "ecc": round(e[2], 3)})
        out["C_flange"]["rows"].append(row)
        print(f"  {pst(t)} PST {lab:42s} " + ("ECC failed" if e is None else
              f"rot {e[0]:+.2f} deg, centre ({e[1][0]:+.2f}, {e[1][1]:+.2f}) px, ECC {e[2]:.3f}"))

    # D. control for C: the other trials' keyframes with the arm turned right (pan >= 40), as in N05-012's late chunks
    out["D_flange_control"] = []
    print(f"D. control: left flange in the other trials' keyframes with pan >= {a.control_pan:g}")
    for r in trials if a.control_pan is not None else []:
        if r["uid"] == a.ref_trial:
            continue
        v = []
        for s in map(json.loads, open(local(r["steps_jsonl"]))):
            if s["joints"]["shoulder_pan.pos"] >= a.control_pan:
                e = ecc_euclid(Fref, crop(media[r["uid"]] / "kf" / f"chunk_{s['chunk']:03d}_front.png"), fm, centre_c)
                if e is not None:
                    v.append((s["joints"]["shoulder_pan.pos"], e[0], e[2]))
        row = {"uid": r["uid"], "n": len(v)}
        if v:
            rot = np.array([x[1] for x in v])
            row.update({"pan_range": [round(min(x[0] for x in v), 1), round(max(x[0] for x in v), 1)],
                        "rot_deg_median": round(float(np.median(rot)), 2), "rot_deg_min": round(float(rot.min()), 2),
                        "rot_deg_max": round(float(rot.max()), 2), "ecc_min": round(min(x[2] for x in v), 3)})
        out["D_flange_control"].append(row)
        print(f"  {r['uid']:8s} " + (f"{row['n']} keyframes, pan {row['pan_range'][0]:+.1f} to {row['pan_range'][1]:+.1f}: rot "
                                     f"median {row['rot_deg_median']:+.2f}, {row['rot_deg_min']:+.2f} to {row['rot_deg_max']:+.2f} "
                                     f"deg, ECC >= {row['ecc_min']:.3f}" if v else "no keyframe with the arm turned that far"))

    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out + ".json").write_text(json.dumps(out, indent=1, default=float))
    rows_c =[q for q in out["C_flange"]["rows"] if "rot_deg" in q]
    W_, H_ = 900, 260
    plot = np.full((H_, W_, 3), 255, np.uint8)
    lo, hi = -4.0, 2.0
    yv = lambda v: int(H_ - 20 - (v - lo) / (hi - lo) * (H_ - 40))      # noqa: E731
    for v in (-3, -2, -1, 0, 1):
        cv2.line(plot, (40, yv(v)), (W_ - 10, yv(v)), (220, 220, 220), 1)
        cv2.putText(plot, f"{v:+d}", (4, yv(v) + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
    cv2.line(plot, (40, yv(exp_rot)), (W_ - 10, yv(exp_rot)), (200, 120, 0), 1)
    for i, q in enumerate(rows_c):
        col = (220, 0, 0) if q["label"].startswith(a.ref_trial + " chunk") else (0, 0, 0)
        cv2.circle(plot, (40 + int(i * (W_ - 60) / max(1, len(rows_c) - 1)), yv(q["rot_deg"])), 3, col, -1)
    cv2.putText(plot, f"left flange image rotation (deg) vs {a.ref_trial} pre, in time order (black: D photos, references, "
                f"pre/start frames; red: {a.ref_trial} keyframes; orange line: sled move)", (40, 14),
                cv2.FONT_HERSHEY_SIMPLEX, 0.37, (0, 0, 0), 1)
    picks = [q for q in rows_c if q["label"].split(" (")[0] in ("D04 clean", f"{a.ref_trial} start",
             f"{a.ref_trial} chunk 37", f"{a.ref_trial} chunk 44", f"{a.ref_trial} chunk 70")]
    crops = [cv2.resize(load(GTC / q["path"])[y0 - 20:y1 + 10, x0 - 20:x1], None, fx=2, fy=2,
                        interpolation=cv2.INTER_NEAREST) for q in picks]
    crops = [cv2.putText(c.copy(), q["label"].split(" (")[0], (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
             for c, q in zip(crops, picks)]
    strip = np.hstack(crops)
    strip = np.hstack([strip, np.zeros((strip.shape[0], max(0, W_ - strip.shape[1]), 3), np.uint8)])[:, :W_]
    cv2.imwrite(a.out + ".png", cv2.cvtColor(np.vstack([plot, strip]), cv2.COLOR_RGB2BGR))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
