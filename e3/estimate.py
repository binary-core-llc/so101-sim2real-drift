#!/usr/bin/env python3
"""E3: estimate a camera or rack mis-setup from one front-camera photo by render-and-compare (D_software C12, C11).

    python -I estimate.py camera --photo P.png --nominal-pose s1.json [--start-pose X.json] --out est.json [--png ov.png]
    python -I estimate.py rack   --photo P.png --camera-pose s1.json --out est.json [--png ov.png]
    common: --intrinsics c920_intrinsics.json --frames frames_sim.json --usd-dir <course assets/usd> --photo-id ID

Photo -> segment.py (undistorted onto the renderer's ideal pinhole; classes white / mat / rack; robot, tube caps and
transitions are "don't care"). Renderer -> render.py (the course scene from the C1 dump: lightbox panels, mat, rack;
robot and tubes not rendered).
Objective (D C12): class-weighted soft IoU over white, mat and rack, plus a symmetric edge chamfer between the class
boundaries, on valid cells only: J = 1 - sum_c w_c sIoU_c / sum_c w_c + LAMBDA * chamfer_px. Coarse to fine:
160 x 120, then 320 x 240. Search (default, D C12): cross-entropy method, population 64, 15 iterations per level, full
covariance, deterministic seed (`--search nm`: the Nelder-Mead multi-start below, kept for comparison).
- camera: all 6 DoF at the lens (tx, ty, tz mm along the camera's x right, y down, z forward; rx, ry, rz deg about the
  same axes), deterministic Nelder-Mead from fixed starts around the start pose, the best polished at 320 x 240. The rack
  is at its nominal pose (the camera cycles keep it there).
- rack: (x, y) in E and yaw about corner O, the camera at the given pose; a grid at 160 x 120, then Nelder-Mead.
With --reference-photo (camera) the delta is E3(photo) - E3(nominal reference photo), not E3(photo) - the nominal pose.
Output: the Appendix C estimate (delta = actual - nominal; correction = -delta): camera_delta in B 1.3 terms (tilt_down,
pan, roll, lateral = E y, depth = E x, height = E z) plus the sim's camera_mount offsets; rack_delta (x_m, y_m, yaw_deg).
Diagnostics: per-class soft IoU, chamfer, time, overlay PNG.
"""
import argparse
import datetime as dt
import hashlib
import json
import math
import sys
import time
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import render as Rn  # noqa: E402
import segment as Sg  # noqa: E402

WEIGHTS = {1: 1.0, 2: 1.0, 3: 1.0}       # white, mat, rack
LAMBDA = 0.01                              # per px of mean chamfer at the working resolution
LEVELS = [(160, 120), (320, 240)]
CAM_STARTS = [[0, 0, 0, 0, 0, 0], [0, 0, 0, 3, 0, 0], [0, 0, 0, -3, 0, 0], [0, 0, 0, 6, 0, 0], [0, 0, 0, -6, 0, 0],
              [0, 0, 0, 0, 3, 0], [0, 0, 0, 0, -3, 0], [0, -20, 0, 0, 0, 0], [0, 20, 0, 0, 0, 0]]
CAM_STEPS = [8, 8, 12, 1.0, 1.0, 1.0]


def version_hash():
    h = hashlib.sha256()
    for f in sorted(HERE.glob("*.py")):
        h.update(f.name.encode() + f.read_bytes())
    return h.hexdigest()


# ---------------------------------------------------------------- B 1.3 terms (as gtc calib/charuco.py angles/delta)
def angles(R):
    x, y, z = R[:, 0], R[:, 1], R[:, 2]
    return {"depression_deg": math.degrees(math.asin(-z[2])), "heading_deg": math.degrees(math.atan2(z[1], z[0])),
            "roll_deg": math.degrees(math.atan2(-x[2], -y[2]))}


def b13_delta(Ra, Ca, Rb, Cb):
    a, b = angles(Ra), angles(Rb)
    dc = np.subtract(Cb, Ca)
    return {"tilt_down_deg": b["depression_deg"] - a["depression_deg"],
            "pan_deg": (b["heading_deg"] - a["heading_deg"] + 180) % 360 - 180,
            "roll_deg": b["roll_deg"] - a["roll_deg"], "lateral_m": float(dc[1]), "depth_m": float(dc[0]),
            "height_m": float(dc[2])}


# ---------------------------------------------------------------- objective
class Target:
    """The photo's soft class maps and class boundaries at one resolution."""

    def __init__(self, cls_full, w, h):
        self.w, self.h = w, h
        self.maps, self.valid = Sg.soft_maps(cls_full, w, h)
        hard = cv2.resize(cls_full, (w, h), interpolation=cv2.INTER_NEAREST)
        self.edges = boundaries(hard)
        self.dt = cv2.distanceTransform((~self.edges).astype(np.uint8), cv2.DIST_L2, 3)


def boundaries(cls):
    """Pixels where two different known classes meet (don't care, 0, never makes a boundary)."""
    e = np.zeros(cls.shape, bool)
    for a, b in ((cls[:, 1:], cls[:, :-1]), (cls[1:, :], cls[:-1, :])):
        m = (a != b) & (a > 0) & (b > 0)
        if a.shape[1] != cls.shape[1]:
            e[:, 1:] |= m
            e[:, :-1] |= m
        else:
            e[1:, :] |= m
            e[:-1, :] |= m
    return e


def score(rend, tg):
    """(J, per-class soft IoU, chamfer px) of a rendered E3 class image against the photo's target."""
    per, num, den = {}, 0.0, 0.0
    for c, w in WEIGHTS.items():
        r = (rend == c) * tg.valid
        m = tg.maps[c]
        u = np.maximum(r, m).sum()
        iou = float(np.minimum(r, m).sum() / u) if u > 0 else 1.0
        per[Rn.E3_CLASSES[c]] = iou
        num += w * iou
        den += w
    er = boundaries(np.where(tg.valid > 0.5, rend, 0))
    if er.any() and tg.edges.any():
        d1 = tg.dt[er].mean()
        dtr = cv2.distanceTransform((~er).astype(np.uint8), cv2.DIST_L2, 3)
        d2 = dtr[tg.edges].mean()
        ch = 0.5 * float(d1 + d2)
    else:
        ch = float(max(tg.w, tg.h))
    return 1.0 - num / den + LAMBDA * ch, per, ch


# ---------------------------------------------------------------- searches
def search_camera(scene, f_full, R0, C0, cls_full, log=print):
    t0 = time.time()
    best = None
    for lvl, (w, h) in enumerate(LEVELS):
        tg = Target(cls_full, w, h)
        f = f_full * w / 640

        def J(p, tg=tg, f=f, w=w, h=h):
            R, C = Rn.lens_move(R0, C0, p)
            return score(Rn.render_e3(scene, R, C, f, w, h), tg)[0]
        if lvl == 0:
            runs = []
            for s in CAM_STARTS:
                p, v, n = Rn.nelder_mead(J, np.asarray(s, float), np.asarray(CAM_STEPS, float), max_evals=400)
                runs.append((v, p))
            runs.sort(key=lambda r: r[0])
            log(f"  camera, {w}x{h}: best J {runs[0][0]:.4f} from {len(runs)} starts ({time.time() - t0:.0f} s)")
            best = runs[0][1]
        else:
            p, v, n = Rn.nelder_mead(J, best, np.asarray(CAM_STEPS, float) / 3, max_evals=300)
            best = p
            log(f"  camera, {w}x{h}: J {v:.4f} after {n} renders ({time.time() - t0:.0f} s)")
    R, C = Rn.lens_move(R0, C0, best)
    return R, C, best, time.time() - t0


def search_rack(scene, f_full, R, C, cls_full, log=print):
    t0 = time.time()
    w, h = LEVELS[0]
    tg = Target(cls_full, w, h)
    f = f_full * w / 640
    st = Rn.render(scene.static, R, C, f, w, h, depth=True)
    grid = [(dx, dy, yw) for dx in np.arange(-45, 45.1, 5) for dy in np.arange(-45, 45.1, 5) for yw in np.arange(-24, 24.1, 3)]
    vals = [score(Rn.render_e3(scene, R, C, f, w, h, (dx / 1000, dy / 1000, yw), static=st), tg)[0] for dx, dy, yw in grid]
    x = np.array(grid[int(np.argmin(vals))], float)
    log(f"  rack grid {w}x{h}: best {x} J {min(vals):.4f} ({len(grid)} renders, {time.time() - t0:.0f} s)")
    for w, h in LEVELS:
        tg = Target(cls_full, w, h)
        f = f_full * w / 640
        st = Rn.render(scene.static, R, C, f, w, h, depth=True)

        def J(q, tg=tg, f=f, w=w, h=h, st=st):
            return score(Rn.render_e3(scene, R, C, f, w, h, (q[0] / 1000, q[1] / 1000, q[2]), static=st), tg)[0]
        x, v, n = Rn.nelder_mead(J, x, np.array([2.0, 2.0, 1.0]), max_evals=200)
        log(f"  rack {w}x{h}: {np.round(x, 2)} J {v:.4f} ({time.time() - t0:.0f} s)")
    return x, time.time() - t0


# ---------------------------------------------------------------- CEM (D C12's registered search) over a batch renderer
class NumpyBackend:
    """Batch interface over render.py (CPU). A GPU backend (render_gpu.py) has the same two methods."""
    name = "numpy-cpu"

    def __init__(self, scene):
        self.scene, self._st = scene, {}

    def camera_images(self, R0, C0, P, f, w, h):
        out = []
        for p in P:
            R, C = Rn.lens_move(R0, C0, p)
            out.append(Rn.render_e3(self.scene, R, C, f, w, h))
        return out

    def rack_images(self, R, C, Q, f, w, h):
        key = (w, h, R.tobytes(), C.tobytes())
        if key not in self._st:
            self._st = {key: Rn.render(self.scene.static, R, C, f, w, h, depth=True)}
        st = self._st[key]
        return [Rn.render_e3(self.scene, R, C, f, w, h, (q[0] / 1000, q[1] / 1000, q[2]), static=st) for q in Q]


CEM = {"camera": [dict(level=0, sd=[12, 12, 15, 4.0, 4.0, 2.5], n=64, iters=15, elite=16, floor=[0.2, 0.2, 0.3, 0.02, 0.02, 0.02]),
                  dict(level=1, sd=[3, 3, 4, 0.6, 0.6, 0.4], n=64, iters=15, elite=16, floor=[0.05, 0.05, 0.08, 0.005, 0.005, 0.005])],
       "rack": [dict(level=0, sd=[20, 20, 8.0], n=64, iters=15, elite=16, floor=[0.1, 0.1, 0.03]),
                dict(level=1, sd=[3, 3, 1.0], n=32, iters=10, elite=8, floor=[0.03, 0.03, 0.01])]}
ALPHA, SEED = 0.7, 0


def cem(Jb, mean, plan, log, label):
    """Deterministic cross-entropy method with a full covariance (the camera's tilt and height trade off along a narrow
    valley, which a per-axis sd cannot follow): per level, population n from N(mean, S), the best `elite` refit the
    mean and S (smoothed by ALPHA, with a floor on the diagonal); the best sample so far is kept in the population."""
    rng = np.random.default_rng(SEED)
    best_x, best_v = np.asarray(mean, float), None
    for lv in plan:
        J = Jb[lv["level"]]
        mean = best_x.copy()
        S = np.diag(np.asarray(lv["sd"], float) ** 2)
        floor = np.diag(np.asarray(lv["floor"], float) ** 2)
        best_v = float(J([best_x])[0])
        for it in range(lv["iters"]):
            L = np.linalg.cholesky(S + 1e-12 * np.eye(len(mean)))
            P = mean + rng.standard_normal((lv["n"], len(mean))) @ L.T
            P[0] = best_x
            v = np.asarray(J(P), float)
            o = np.argsort(v)
            if v[o[0]] < best_v:
                best_v, best_x = float(v[o[0]]), P[o[0]].copy()
            el = P[o[:lv["elite"]]]
            mean = ALPHA * el.mean(0) + (1 - ALPHA) * mean
            S = ALPHA * np.cov(el.T) + (1 - ALPHA) * S + floor
        log(f"  {label} CEM level {lv['level']}: J {best_v:.4f}")
    return best_x, best_v


def search_camera_cem(be, f_full, R0, C0, cls_full, log=print):
    t0 = time.time()
    Jb = {}
    for lvl, (w, h) in enumerate(LEVELS):
        tg, f = Target(cls_full, w, h), f_full * w / 640
        Jb[lvl] = (lambda P, tg=tg, f=f, w=w, h=h: [score(im, tg)[0] for im in be.camera_images(R0, C0, P, f, w, h)])
    p, v = cem(Jb, np.zeros(6), CEM["camera"], log, "camera")
    R, C = Rn.lens_move(R0, C0, p)
    return R, C, p, time.time() - t0


def search_rack_cem(be, f_full, R, C, cls_full, log=print):
    t0 = time.time()
    Jb = {}
    for lvl, (w, h) in enumerate(LEVELS):
        tg, f = Target(cls_full, w, h), f_full * w / 640
        Jb[lvl] = (lambda Q, tg=tg, f=f, w=w, h=h: [score(im, tg)[0] for im in be.rack_images(R, C, Q, f, w, h)])
    x, v = cem(Jb, np.zeros(3), CEM["rack"], log, "rack")
    return x, time.time() - t0


# ---------------------------------------------------------------- main
def load_pose(path):
    r = json.loads(Path(path).read_text())
    return np.array(r["R_E_cv"], float), np.array(r["C_E_m"], float)


def overlay(rgb_ideal, rend, w, h):
    big = cv2.resize(rend, (640, 480), interpolation=cv2.INTER_NEAREST)
    out = rgb_ideal.copy()
    e = boundaries(big)
    out[e] = (255, 0, 255)
    return out


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["camera", "rack"])
    ap.add_argument("--photo", required=True)
    ap.add_argument("--photo-id")
    ap.add_argument("--nominal-pose", help="camera: the real nominal pose (pose.py JSON in E); delta = estimate - this")
    ap.add_argument("--start-pose", help="camera: search start (default the nominal pose)")
    ap.add_argument("--reference-photo", help="camera: the nominal reference photo (same block, camera at the nominal "
                    "pose). E3 is run on it too and the delta is the change between the two estimates, so a constant "
                    "model bias (e.g. a mat turned against the simulation) cancels")
    ap.add_argument("--camera-pose", help="rack: the camera pose to render from (pose.py JSON in E)")
    ap.add_argument("--intrinsics", required=True)
    ap.add_argument("--frames", required=True)
    ap.add_argument("--usd-dir", help="the course's assets/usd (not needed with --scene-cache)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--png")
    ap.add_argument("--search", choices=["cem", "nm"], default="cem", help="cem: D C12's registered search (default)")
    ap.add_argument("--backend", choices=["numpy", "torch"], default="numpy",
                    help="renderer for the CEM search: numpy (CPU) or torch (CUDA, render_gpu.py; identical class images)")
    ap.add_argument("--scene-cache", help="cache/scene.npz (render.py cache): no USD read, e.g. in our Isaac container")
    a = ap.parse_args(argv)
    t0 = time.time()
    j = json.loads(Path(a.intrinsics).read_text())
    K, dist = np.array(j["K"], float), np.array(j["dist"], float).ravel()
    rgb = cv2.imread(a.photo)[:, :, ::-1]
    rgb_i, inside = Sg.undistort(rgb, K, dist)
    cls = Sg.classify(rgb_i, inside)
    scene, rig = Rn.load_scene(a.frames, a.usd_dir, cache=a.scene_cache)
    f = float(K[0, 0])
    if a.backend == "torch":
        import render_gpu
        be = render_gpu.TorchBackend(scene)
    else:
        be = NumpyBackend(scene)
    s_cam = (lambda R0, C0, c: search_camera_cem(be, f, R0, C0, c)) if a.search == "cem" else \
        (lambda R0, C0, c: search_camera(scene, f, R0, C0, c))
    s_rack = (lambda R0, C0, c: search_rack_cem(be, f, R0, C0, c)) if a.search == "cem" else \
        (lambda R0, C0, c: search_rack(scene, f, R0, C0, c))
    est = {"photo_id": a.photo_id or Path(a.photo).stem, "method": "E3", "model_id": "e3-render-compare-v0", "prompt_id": None,
           "version_hash": version_hash(), "status": "ok", "search": a.search, "backend": a.backend if a.search == "cem" else "numpy", "camera_delta": None, "rack_delta": None,
           "intrinsics_ref": hashlib.sha256(Path(a.intrinsics).read_bytes()).hexdigest(), "raw_path": str(a.photo),
           "utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    if a.mode == "camera":
        Rn_, Cn = load_pose(a.nominal_pose)
        Rs, Cs = load_pose(a.start_pose) if a.start_pose else (Rn_, Cn)
        R, C, p, secs = s_cam(Rs, Cs, cls)
        Ra, Ca = Rn_, Cn
        if a.reference_photo:                     # differential: the nominal photo through the same model
            ref_i, ref_in = Sg.undistort(cv2.imread(a.reference_photo)[:, :, ::-1], K, dist)
            Rr, Cr, pr, s2 = s_cam(Rn_, Cn, Sg.classify(ref_i, ref_in))
            secs += s2
            est["reference_estimate"] = {"photo": a.reference_photo, "R_E_cv": Rr.tolist(), "C_E_m": Cr.tolist(),
                                         "vs_nominal_pose": b13_delta(Rn_, Cn, Rr, Cr)}
            Ra, Ca = Rr, Cr
        d = b13_delta(Ra, Ca, R, C)
        off = rig.offsets_for_lens(R, C) - rig.offsets_for_lens(Ra, Ca)
        est["camera_delta"] = {**{k: round(v, 5) for k, v in d.items()},
                               "mount_offsets": {"x_m": off[0], "y_m": off[1], "z_m": off[2], "roll_rad": off[3],
                                                 "pitch_rad": off[4], "yaw_rad": off[5]}}
        est["camera_estimate"] = {"R_E_cv": R.tolist(), "C_E_m": C.tolist(), "angles": angles(R), "lens_params": list(p)}
        rend = Rn.render_e3(scene, R, C, f * 320 / 640, 320, 240)
    else:
        R, C = load_pose(a.camera_pose)
        x, secs = s_rack(R, C, cls)
        est["rack_delta"] = {"x_m": round(x[0] / 1000, 5), "y_m": round(x[1] / 1000, 5), "yaw_deg": round(float(x[2]), 3)}
        rend = Rn.render_e3(scene, R, C, f * 320 / 640, 320, 240, (x[0] / 1000, x[1] / 1000, x[2]))
    J, per, ch = score(rend, Target(cls, 320, 240))
    est.update({"seconds": round(time.time() - t0, 1), "search_seconds": round(secs, 1),
                "fit": {"J": round(J, 4), "soft_iou": {k: round(v, 4) for k, v in per.items()}, "chamfer_px_320": round(ch, 2)}})
    Path(a.out).write_text(json.dumps(est, indent=1, default=float))
    if a.png:
        cv2.imwrite(a.png, overlay(rgb_i, rend, 320, 240)[:, :, ::-1])
    print(json.dumps({k: est[k] for k in ("photo_id", "camera_delta", "rack_delta", "fit", "seconds")}, default=float))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
