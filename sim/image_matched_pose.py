#!/usr/bin/env python3
"""H4 image-matched pose (D_software C8a; PREREGISTRATION_v1 §4 cell H4_c920_image_matched). CPU only, no GPU.

The pose of the sim's external camera, with the C920's focal, at which its view best matches the nominal D455
view (fx 514.67 px). Match = mean class-mask IoU over 7 classes: background, floor, walls, mat, rack, robot,
vials. The result is sent to the sim as the camera_mount offsets the S1/S7/S8 cells use (`sim/overrides.py`
"camera": x, y, z in m in the mount's parent frame (LightBox); roll, pitch, yaw in rad about the mount's local
axes, composed as base * delta like the course's randomize_camera_pose, resets.py:122-200).

    .venv/bin/python -I sim/image_matched_pose.py validate        # renderer vs the C1 masks; offsets vs T06 readback
    .venv/bin/python -I sim/image_matched_pose.py match --intrinsics config/c920_intrinsics.json \\
        [--out results/h4/image_matched_pose.json] [--png results/h4/image_matched_masks.png]

Scene: every pose is read from results/c1/frames_sim.json (the C1 dump: Eval task, every DR at its centre, seed 0
vials, read after the 10 warm-up steps, i.e. the first frame the policy sees). It includes:
  - the lightbox panels, built from their dumped world corners;
  - mat.usda;
  - Vial_rack_simple.usda;
  - Vial_opaque.usda × 3;
  - the robot's visual meshes (SO-ARM101-USD.usd) at the dumped link poses.
Rendering is a numpy z-buffer: pixel centres, perspective-correct depth, near-plane clipping at 1 cm.

Camera model: the sim's pinhole. Pixels are square and the principal point is the image centre, so only the focal
length changes (fx_sim = the measured fx; C8a: focal_mm = fx * hAp / 640, hAp 2.4 mm). The measured fy/fx,
cx, cy and distortion are not represented, here or in the sim cell.

Search (our choice, D_software C8a leaves it open):
  - All 6 DoF. They are parametrised at the lens: translation along the camera's own axes (x right, y down,
    z forward, mm) and rotation about the lens (deg, about the same axes).
  - So the dominant move, a dolly along the optical axis, is one parameter.
  - The result is converted exactly to mount offsets. That covers the pivot: the mount rotates about its origin,
    4.75 cm from the lens (C8a), not about the lens.
  - Start: the best dolly on a 5 mm grid (-150 to +150 mm). Then Nelder-Mead on all 6 at half resolution
    (320 x 240), with a deterministic simplex, from 6 fixed starts around that dolly (run in parallel). The
    IoU has several local optima, a tilt vs height trade-off; the best start is then polished.
  - IoU is reported at full resolution, together with the dolly-only optimum for comparison.
"""
import argparse
import datetime as dt
import hashlib
import json
import math
import multiprocessing as mp
import os
import sys
import time
from pathlib import Path

import numpy as np

GTC = Path(__file__).resolve().parents[1]
C1 = GTC / "results" / "c1"
FRAMES = C1 / "frames_sim.json"
USD_DIR = GTC.parent / "Sim-to-Real-SO-101-Workshop" / "source" / "sim_to_real_so101" / "assets" / "usd"
T06 = GTC / "results" / "sim" / "t06_probe.jsonl"
W, H = 640, 480
HAP_MM = 2.4
NEAR = 0.01
CLASSES = ["background", "floor", "wall", "mat", "rack", "robot", "vial"]
LINKS = ["base", "shoulder", "upper_arm", "lower_arm", "wrist", "gripper", "jaw"]


# ---------------------------------------------------------------- small geometry helpers (column vectors)
def quat_to_R(q):
    w, x, y, z = q
    n = math.sqrt(w * w + x * x + y * y + z * z)
    w, x, y, z = w / n, x / n, y / n, z / n
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
                     [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
                     [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)]])


def euler_xyz_to_R(roll, pitch, yaw):
    """Isaac Lab quat_from_euler_xyz: R = Rz(yaw) Ry(pitch) Rx(roll) (checked against the T06 readback)."""
    cr, sr, cp, sp, cy, sy = math.cos(roll), math.sin(roll), math.cos(pitch), math.sin(pitch), math.cos(yaw), math.sin(yaw)
    Rx = np.array([[1, 0, 0], [0, cr, -sr], [0, sr, cr]])
    Ry = np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]])
    Rz = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def R_to_euler_xyz(R):
    """Inverse of euler_xyz_to_R (pitch within ±90°)."""
    pitch = math.asin(max(-1.0, min(1.0, -R[2, 0])))
    roll = math.atan2(R[2, 1], R[2, 2])
    yaw = math.atan2(R[1, 0], R[0, 0])
    return roll, pitch, yaw


def axis_angle(v_deg):
    """Rotation matrix for a rotation vector given in degrees."""
    v = np.radians(np.asarray(v_deg, float))
    th = np.linalg.norm(v)
    if th < 1e-12:
        return np.eye(3)
    k = v / th
    Kx = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + math.sin(th) * Kx + (1 - math.cos(th)) * Kx @ Kx


def rot_angle_deg(A, B):
    """Angle of the rotation between A and B (robust near 0, unlike arccos of the trace)."""
    D = A.T @ B
    v = np.array([D[2, 1] - D[1, 2], D[0, 2] - D[2, 0], D[1, 0] - D[0, 1]])
    return math.degrees(math.atan2(np.linalg.norm(v) / 2, (np.trace(D) - 1) / 2))


def orthonormal(R):
    U, _, Vt = np.linalg.svd(R)
    return U @ Vt


def rowmat(M):
    """USD row-vector 4x4 (p_world = p_local · M) -> (R, t) with p_world = R p_local + t."""
    M = np.asarray(M, float)
    return M[:3, :3].T, M[3, :3].copy()


# ---------------------------------------------------------------- camera rig: mount offsets <-> lens pose
class Rig:
    """The external camera as the sim builds it: LightBox parent, camera_mount local ops, render prim in the mount."""

    def __init__(self, frames):
        cm = frames["camera_mount"]
        self.t_loc = np.array(cm["local_ops"]["xformOp:translate"], float)
        self.q_loc = np.array(cm["local_ops"]["xformOp:orient"], float)          # wxyz
        self.R_loc = quat_to_R(self.q_loc)
        R_mw, t_mw = rowmat(cm["world_usd"]["matrix_row_major_usd"])
        # parent (LightBox) world pose: mount_world = parent ∘ local
        self.R_par = R_mw @ self.R_loc.T
        self.t_par = t_mw - self.R_par @ self.t_loc
        cam = frames["camera_external_D455"]
        R_cm, t_cm = rowmat(cam["camera_in_mount"]["matrix_row_major_usd"])       # render prim in the mount frame
        self.R_cm, self.t_cm = orthonormal(R_cm), t_cm                             # stored with ~2e-6 non-orthogonality
        self.cv_from_usd = np.diag([1.0, -1.0, -1.0])                             # USD camera (-Z fwd, +Y up) -> OpenCV
        self.K_sim = np.array(cam["tiled_camera"]["intrinsic_matrices"], float)
        R0, C0 = self.lens(np.zeros(6))
        R_cam, t_cam = rowmat(cam["world_usd"]["matrix_row_major_usd"])
        self.rig_check = {"pos_err_m": float(np.linalg.norm(C0 - t_cam)),
                          "rot_err_deg": rot_angle_deg(orthonormal(R_cam) @ self.cv_from_usd, R0)}

    def mount_world(self, off):
        x, y, z, roll, pitch, yaw = off
        R_l = self.R_loc @ euler_xyz_to_R(roll, pitch, yaw)
        t_l = self.t_loc + np.array([x, y, z])
        return self.R_par @ R_l, self.R_par @ t_l + self.t_par

    def lens(self, off):
        """Offsets (x, y, z m; roll, pitch, yaw rad) -> OpenCV camera rotation (columns = cam axes in world), centre."""
        R_m, t_m = self.mount_world(off)
        R_c = R_m @ self.R_cm
        return R_c @ self.cv_from_usd, R_m @ self.t_cm + t_m

    def offsets_for_lens(self, R_cv, C):
        """Exact inverse of lens(): the mount offsets that put the render prim at (R_cv, C)."""
        R_c = R_cv @ self.cv_from_usd
        R_m = R_c @ self.R_cm.T
        t_m = C - R_m @ self.t_cm
        R_l = self.R_par.T @ R_m
        t_l = self.R_par.T @ (t_m - self.t_par)
        roll, pitch, yaw = R_to_euler_xyz(self.R_loc.T @ R_l)
        d = t_l - self.t_loc
        return np.array([d[0], d[1], d[2], roll, pitch, yaw])


def lens_move(R0, C0, p):
    """Lens-frame parameters p = (tx, ty, tz mm along the camera's x right, y down, z forward; rx, ry, rz deg)."""
    C = C0 + R0 @ (np.asarray(p[:3], float) / 1000.0)
    return R0 @ axis_angle(p[3:]), C


# ---------------------------------------------------------------- scene from the C1 dump + course USD
def _mesh_tris(prim, xc):
    from pxr import UsdGeom
    m = UsdGeom.Mesh(prim)
    pts = np.array(m.GetPointsAttr().Get(), float)
    M = np.array(xc.GetLocalToWorldTransform(prim), float)
    w = pts @ M[:3, :3] + M[3, :3]
    cnt = np.array(m.GetFaceVertexCountsAttr().Get())
    idx = np.array(m.GetFaceVertexIndicesAttr().Get())
    starts = np.r_[0, np.cumsum(cnt)[:-1]]
    tri = [np.c_[idx[s] * np.ones(c - 2, int), idx[s + 1:s + c - 1], idx[s + 2:s + c]] for s, c in zip(starts, cnt) if c >= 3]
    return w[np.concatenate(tri)]


def _file_meshes(path, root=None):
    """All visible meshes of a USD file, in the file's world frame (or relative to `root`'s frame)."""
    from pxr import Usd, UsdGeom
    st = Usd.Stage.Open(str(path))
    xc = UsdGeom.XformCache()
    start = st.GetPrimAtPath(root) if root else st.GetPseudoRoot()
    out = []
    for p in Usd.PrimRange(start, Usd.TraverseInstanceProxies()):
        if p.GetTypeName() == "Mesh" and UsdGeom.Imageable(p).ComputeVisibility() != UsdGeom.Tokens.invisible:
            out.append((str(p.GetPath()), _mesh_tris(p, xc)))
    return st, xc, out


def _place(tris, R, t):
    return tris @ R.T + t


def _box(lo, hi):
    """Axis-aligned cuboid, outward-wound triangles."""
    x0, y0, z0 = lo
    x1, y1, z1 = hi
    P = np.array([[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0], [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]])
    F = [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5), (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)]
    return P[np.array(F)]


class Scene:
    def __init__(self, frames):
        tris, cls, closed = [], [], []

        def add(t, c, is_closed=False):
            tris.append(t)
            cls.append(np.full(len(t), CLASSES.index(c), np.int8))
            closed.append(np.full(len(t), is_closed))

        self.sources = {}
        for name, pnl in frames["lightbox_panels"].items():
            lo, hi = np.array(pnl["world_bbox_min"]), np.array(pnl["world_bbox_max"])
            pts = np.array(pnl["world_points"])
            assert np.all(np.min(np.abs(pts[:, None, :] - np.stack([lo, hi])[None]), axis=1) < 1e-6), f"panel {name} not axis-aligned"
            add(_box(lo, hi), "floor" if name == "Base" else "wall", True)
        # mat
        _, _, ms = _file_meshes(USD_DIR / "mat.usda")
        R, t = rowmat(frames["mat"]["world_usd"]["matrix_row_major_usd"])
        for _, tr in ms:
            add(_place(tr, R, t), "mat")
        objs = frames["objects_after_warmup10"]
        # rack
        _, _, ms = _file_meshes(USD_DIR / "Vial_rack_simple.usda")
        R, t = quat_to_R(objs["rack_left"]["quat_wxyz"]), np.array(objs["rack_left"]["pos"])
        for _, tr in ms:
            add(_place(tr, R, t), "rack")
        # vials (visible meshes only; the collider is invisible)
        _, _, ms = _file_meshes(USD_DIR / "Vial_opaque.usda")
        for v in ("vial_1", "vial_2", "vial_3"):
            R, t = quat_to_R(objs[v]["quat_wxyz"]), np.array(objs[v]["pos"])
            for _, tr in ms:
                add(_place(tr, R, t), "vial")
        # robot: mesh in link frame (file) placed at the dumped link pose
        from pxr import Usd, UsdGeom
        st = Usd.Stage.Open(str(USD_DIR / "SO-ARM101-USD.usd"))
        xc = UsdGeom.XformCache()
        bodies = frames["robot"]["bodies"]
        n_robot = 0
        for link in LINKS:
            lp = st.GetPrimAtPath(f"/so101_new_calib/{link}")
            Ml = np.array(xc.GetLocalToWorldTransform(lp), float)
            R_l_file, t_l_file = rowmat(Ml)
            R_b, t_b = quat_to_R(bodies[link]["quat_wxyz"]), np.array(bodies[link]["pos"])
            for p in Usd.PrimRange(st.GetPrimAtPath(f"/so101_new_calib/{link}/visuals"), Usd.TraverseInstanceProxies()):
                if p.GetTypeName() == "Mesh" and UsdGeom.Imageable(p).ComputeVisibility() != UsdGeom.Tokens.invisible:
                    tr = _mesh_tris(p, xc)                                    # file world
                    loc = (tr - t_l_file) @ R_l_file                          # link frame
                    add(_place(loc, R_b, t_b), "robot")
                    n_robot += len(tr)
        self.tris = np.concatenate(tris).astype(np.float64)
        self.cls = np.concatenate(cls)
        self.closed = np.concatenate(closed)
        self.counts = {c: int((self.cls == i).sum()) for i, c in enumerate(CLASSES)}


# ---------------------------------------------------------------- z-buffer rasteriser (numpy)
def _clip_near(X, near):
    """Clip camera-space triangles against z = near (Sutherland-Hodgman); returns triangles fully at z >= near."""
    out = []
    for tri in X:
        poly = []
        for i in range(3):
            a, b = tri[i], tri[(i + 1) % 3]
            ina, inb = a[2] >= near, b[2] >= near
            if ina:
                poly.append(a)
            if ina != inb:
                s = (near - a[2]) / (b[2] - a[2])
                poly.append(a + s * (b - a))
        for k in range(1, len(poly) - 1):
            out.append([poly[0], poly[k], poly[k + 1]])
    return np.array(out, float).reshape(-1, 3, 3)


def render(scene, R_cv, C, f, w=W, h=H, max_cand=4_000_000):
    """Class image (h, w) int8: pixel centres, nearest surface wins. f = fx = fy in px at this resolution."""
    cx, cy = w / 2.0, h / 2.0
    T = scene.tris
    keep = np.ones(len(T), bool)
    if scene.closed.any():                                             # back-face culling for the closed panels only
        n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
        front = np.einsum("ij,ij->i", n, C - T[:, 0]) > 0
        keep &= ~scene.closed | front
    X = (T[keep] - C) @ R_cv                                           # camera coordinates
    cls = scene.cls[keep]
    z = X[..., 2]
    allin = (z >= NEAR).all(1)
    part = ~allin & (z >= NEAR).any(1)
    Xc, cc = [X[allin]], [cls[allin]]
    if part.any():
        for i in np.where(part)[0]:
            c = _clip_near(X[i:i + 1], NEAR)
            Xc.append(c)
            cc.append(np.full(len(c), cls[i], np.int8))
    X, cls = np.concatenate(Xc), np.concatenate(cc)
    z = X[..., 2]
    u = f * X[..., 0] / z + cx
    v = f * X[..., 1] / z + cy
    i0 = np.clip(np.ceil(u.min(1) - 0.5), 0, w).astype(np.int64)
    i1 = np.clip(np.floor(u.max(1) - 0.5), -1, w - 1).astype(np.int64)
    j0 = np.clip(np.ceil(v.min(1) - 0.5), 0, h).astype(np.int64)
    j1 = np.clip(np.floor(v.max(1) - 0.5), -1, h - 1).astype(np.int64)
    bw, bh = i1 - i0 + 1, j1 - j0 + 1
    ok = (bw > 0) & (bh > 0)
    idx = np.where(ok)[0]
    best = np.full(w * h, -np.inf)
    out = np.zeros(w * h, np.int8)
    if not len(idx):
        return out.reshape(h, w)
    cnt = (bw[idx] * bh[idx]).astype(np.int64)
    # chunks of triangles so the candidate arrays stay bounded (a single huge triangle is its own chunk)
    cum = np.cumsum(cnt)
    edges, lo = [], 0
    while lo < len(idx):
        hi = int(np.searchsorted(cum, (cum[lo - 1] if lo else 0) + max_cand, side="right"))
        hi = max(hi, lo + 1)
        edges.append((lo, hi))
        lo = hi
    win_pix, win_inv, win_cls = [], [], []
    for lo, hi in edges:
        t = idx[lo:hi]
        c = cnt[lo:hi]
        rep = np.repeat(np.arange(len(t)), c)
        k = np.arange(c.sum()) - np.repeat(np.cumsum(c) - c, c)
        tt = t[rep]
        px = i0[tt] + k % bw[tt] + 0.5
        py = j0[tt] + k // bw[tt] + 0.5
        u0, u1, u2 = u[tt, 0], u[tt, 1], u[tt, 2]
        v0, v1, v2 = v[tt, 0], v[tt, 1], v[tt, 2]
        area = (u1 - u0) * (v2 - v0) - (u2 - u0) * (v1 - v0)
        w0 = (u2 - u1) * (py - v1) - (v2 - v1) * (px - u1)
        w1 = (u0 - u2) * (py - v2) - (v0 - v2) * (px - u2)
        w2 = (u1 - u0) * (py - v0) - (v1 - v0) * (px - u0)
        s = np.sign(area)
        inside = (area != 0) & (w0 * s >= 0) & (w1 * s >= 0) & (w2 * s >= 0)
        if not inside.any():
            continue
        tt, px, py, area = tt[inside], px[inside], py[inside], area[inside]
        w0, w1, w2 = w0[inside], w1[inside], w2[inside]
        invz = (w0 / z[tt, 0] + w1 / z[tt, 1] + w2 / z[tt, 2]) / area
        pix = (py - 0.5).astype(np.int64) * w + (px - 0.5).astype(np.int64)
        np.maximum.at(best, pix, invz)
        win_pix.append(pix)
        win_inv.append(invz)
        win_cls.append(cls[tt])
    for pix, invz, cl in zip(win_pix, win_inv, win_cls):
        m = invz >= best[pix]
        out[pix[m]] = cl[m]
    return out.reshape(h, w)


def mean_iou(a, b):
    """Mean IoU over the classes present in either image, plus the per-class IoU."""
    per = {}
    for i, c in enumerate(CLASSES):
        A, B = a == i, b == i
        u = np.logical_or(A, B).sum()
        if u:
            per[c] = float(np.logical_and(A, B).sum() / u)
    return float(np.mean(list(per.values()))), per


def c1_class_mask():
    """The C1 dump's instance ids mapped to the 7 classes."""
    from PIL import Image
    ids = np.array(Image.open(C1 / "nominal_front_instance_ids.png")).astype(np.int64)
    labels = json.loads((C1 / "nominal_front_instance_labels.json").read_text())["instance_labels"]
    lut = np.zeros(ids.max() + 1, np.int8)
    for k, v in labels.items():
        lab = v["label"] or ""
        if "/LightBox/Base" in lab:
            c = "floor"
        elif any(f"/LightBox/{p}" in lab for p in ("Back", "Left", "Right", "Top")):
            c = "wall"
        elif "/Mat/" in lab:
            c = "mat"
        elif "/Rack_Left/" in lab:
            c = "rack"
        elif "/Robot/" in lab:
            c = "robot"
        elif "/Vial_" in lab:
            c = "vial"
        elif not lab:
            c = "background"
        else:
            raise SystemExit(f"STOP: unmapped C1 label {lab!r}")
        lut[int(k)] = CLASSES.index(c)
    return lut[ids]


# ---------------------------------------------------------------- optimiser (deterministic Nelder-Mead, numpy)
def nelder_mead(fun, x0, steps, max_evals=500, tol=1e-4):
    n = len(x0)
    pts = [np.asarray(x0, float)] + [np.asarray(x0, float) + np.eye(n)[i] * steps[i] for i in range(n)]
    vals = [fun(p) for p in pts]
    evals = n + 1
    while evals < max_evals:
        o = np.argsort(vals)
        pts, vals = [pts[i] for i in o], [vals[i] for i in o]
        if abs(vals[-1] - vals[0]) < tol and max(np.max(np.abs(p - pts[0]) / steps) for p in pts[1:]) < 0.05:
            break
        cen = np.mean(pts[:-1], axis=0)
        xr = cen + (cen - pts[-1])
        fr = fun(xr)
        evals += 1
        if fr < vals[0]:
            xe = cen + 2 * (cen - pts[-1])
            fe = fun(xe)
            evals += 1
            pts[-1], vals[-1] = (xe, fe) if fe < fr else (xr, fr)
        elif fr < vals[-2]:
            pts[-1], vals[-1] = xr, fr
        else:
            xc = cen + 0.5 * (pts[-1] - cen) if fr >= vals[-1] else cen + 0.5 * (xr - cen)
            fc = fun(xc)
            evals += 1
            if fc < min(fr, vals[-1]):
                pts[-1], vals[-1] = xc, fc
            else:
                for i in range(1, n + 1):
                    pts[i] = pts[0] + 0.5 * (pts[i] - pts[0])
                    vals[i] = fun(pts[i])
                    evals += 1
    i = int(np.argmin(vals))
    return pts[i], vals[i], evals


# fixed multi-start offsets around the best dolly (lens frame: tx, ty, tz mm; rx, ry, rz deg). Nelder-Mead on the
# class IoU has several local optima (a tilt vs height trade-off), so every start is run and the best one polished.
STARTS = [[0, 0, 0, 0, 0, 0], [0, -15, 0, -2, 0, 0], [0, 15, 0, 2, 0, 0], [-10, 0, 0, 0, 1.5, 0],
          [10, 0, 0, 0, -1.5, 0], [0, 0, 0, 0, 0, 1.0]]
_W = {}


def _score(p):
    s = _W
    R, C = lens_move(s["R0"], s["C0"], p)
    return mean_iou(render(s["scene"], R, C, s["fx"] * s["scale"], s["w"], s["h"]), s["ref"])[0]


def _nm(args):
    x0, steps, max_evals = args
    p, v, n = nelder_mead(lambda q: -_score(q), np.asarray(x0, float), steps=np.asarray(steps, float), max_evals=max_evals)
    return p.tolist(), -v, n


def match(scene, rig, fx, start=None, scale=0.5, dolly_range=(-150, 150, 5), max_evals=500, workers=None, log=print):
    """Lens-frame parameters maximising the mean class IoU of the fx view against the nominal D455 view.
    start=None: dolly grid, then Nelder-Mead from every STARTS offset (in parallel), then a polish of the best."""
    R0, C0 = rig.lens(np.zeros(6))
    f_sim = rig.K_sim[0, 0]
    w, h = int(W * scale), int(H * scale)
    _W.update(scene=scene, R0=R0, C0=C0, fx=fx, scale=scale, w=w, h=h, ref=render(scene, R0, C0, f_sim * scale, w, h))
    t0 = time.time()
    grid = np.arange(dolly_range[0], dolly_range[1] + 1e-9, dolly_range[2])
    dscore = [_score([0, 0, d, 0, 0, 0]) for d in grid]
    d_best = float(grid[int(np.argmax(dscore))])
    log(f"  dolly grid: best tz {d_best:+.0f} mm, IoU {max(dscore):.4f} ({time.time() - t0:.0f} s)")
    steps = [5, 5, 5, 0.5, 0.5, 0.5]
    starts = [list(start)] if start is not None else [list(np.add(o, [0, 0, d_best, 0, 0, 0])) for o in STARTS]
    jobs = [(x0, steps, max_evals) for x0 in starts]
    n_work = min(len(jobs), workers or max(1, (os.cpu_count() or 2) // 2))
    if n_work > 1:
        with mp.get_context("fork").Pool(n_work) as pool:
            runs = pool.map(_nm, jobs)
    else:
        runs = [_nm(j) for j in jobs]
    for x0, (p, v, n) in zip(starts, runs):
        log(f"  start {np.round(x0, 1).tolist()}: IoU {v:.4f} ({n} evals) at {np.round(p, 2).tolist()}")
    k = int(np.argmax([r[1] for r in runs]))
    p, v, n = _nm((runs[k][0], [2, 2, 2, 0.2, 0.2, 0.2], max_evals))
    if v < runs[k][1]:
        p, v = runs[k][0], runs[k][1]
    log(f"  polish: IoU {v:.4f} ({time.time() - t0:.0f} s)")
    return {"lens_params": np.asarray(p), "iou_half_res": v, "dolly_only_tz_mm": d_best, "dolly_grid": [grid.tolist(), dscore],
            "evals": int(sum(r[2] for r in runs) + n + len(grid)),
            "starts": [{"start": list(map(float, x0)), "end": list(map(float, r[0])), "iou_half_res": float(r[1]), "evals": int(r[2])}
                       for x0, r in zip(starts, runs)]}


# ---------------------------------------------------------------- commands
def inside_box(frames, C):
    """Lens centre inside the lightbox interior (inner faces of the panels; the front is open to the floor's edge)."""
    P = frames["lightbox_panels"]
    lo = np.array([P["Base"]["world_bbox_min"][0], P["Right"]["world_bbox_max"][1], P["Base"]["world_bbox_max"][2]])
    hi = np.array([P["Back"]["world_bbox_min"][0], P["Left"]["world_bbox_min"][1], P["Top"]["world_bbox_min"][2]])
    margin = float(np.min(np.r_[C - lo, hi - C]))
    return margin > 0, margin


def full_res_report(scene, rig, fx, p):
    R0, C0 = rig.lens(np.zeros(6))
    ref = render(scene, R0, C0, rig.K_sim[0, 0])
    at_nom = render(scene, R0, C0, fx)
    R, C = lens_move(R0, C0, p)
    at_best = render(scene, R, C, fx)
    m0, per0 = mean_iou(at_nom, ref)
    m1, per1 = mean_iou(at_best, ref)
    return {"ref": ref, "at_nominal": at_nom, "at_best": at_best,
            "iou_pose_matched": m0, "iou_pose_matched_per_class": per0,
            "iou_image_matched": m1, "iou_image_matched_per_class": per1}


def offsets_dict(o):
    return {"x": float(o[0]), "y": float(o[1]), "z": float(o[2]), "roll": float(o[3]), "pitch": float(o[4]), "yaw": float(o[5])}


def lens_summary(rig, p):
    R0, C0 = rig.lens(np.zeros(6))
    R, C = lens_move(R0, C0, p)
    ax0, ax = R0[:, 2], R[:, 2]
    dep = lambda a: math.degrees(math.asin(-a[2]))
    head = lambda a: math.degrees(math.atan2(a[1], a[0]))
    return {"lens_centre_env_m": C.tolist(), "lens_shift_env_mm": ((C - C0) * 1000).tolist(),
            "optical_axis_deg_below_horizontal": dep(ax), "delta_tilt_down_deg": dep(ax) - dep(ax0),
            "optical_axis_heading_deg": head(ax), "delta_heading_deg": head(ax) - head(ax0)}


def save_png(path, rep):
    import cv2
    pal = np.array([[0, 0, 0], [200, 200, 200], [120, 120, 160], [40, 160, 60], [30, 200, 230], [30, 110, 240], [230, 60, 60]], np.uint8)
    row = [pal[rep["ref"]], pal[rep["at_nominal"]], pal[rep["at_best"]]]
    img = np.concatenate(row, axis=1)
    for k, t in enumerate(["D455 nominal (reference)", "C920 focal, pose-matched", "C920 focal, image-matched"]):
        cv2.putText(img, t, (10 + 640 * k, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), img)


def t06_check(rig):
    """Offsets -> lens pose against every T06 probe readback (the real sim)."""
    errs = []
    if not T06.exists():
        return None
    for line in open(T06):
        r = json.loads(line)
        ov = r.get("resolved", {}).get("camera")
        rb = r.get("readback", {}).get("camera_external")
        if not ov or not rb:
            continue
        off = np.array([ov[k] for k in ("x", "y", "z", "roll", "pitch", "yaw")])
        R, C = rig.lens(off)
        R_rb = quat_to_R(rb["quat_wxyz"]) @ rig.cv_from_usd
        e_pos = float(np.linalg.norm(C - np.array(rb["pos"])))
        e_rot = rot_angle_deg(R_rb, R)
        back = rig.offsets_for_lens(R, C)
        errs.append({"set": r.get("set"), "pos_err_mm": e_pos * 1000, "rot_err_deg": e_rot,
                     "inverse_err": float(np.max(np.abs(back - off)))})
    return errs


def cmd_validate(a):
    frames = json.loads(FRAMES.read_text())
    rig = Rig(frames)
    print(f"rig: render prim from the mount chain vs the dumped world pose: {rig.rig_check['pos_err_m'] * 1000:.4f} mm, "
          f"{rig.rig_check['rot_err_deg']:.5f} deg")
    t06 = t06_check(rig)
    if t06:
        print(f"T06 readback ({len(t06)} probe records): max lens error {max(e['pos_err_mm'] for e in t06):.4f} mm, "
              f"{max(e['rot_err_deg'] for e in t06):.5f} deg; offsets round trip max {max(e['inverse_err'] for e in t06):.2e}")
    t0 = time.time()
    scene = Scene(frames)
    print(f"scene: {len(scene.tris)} triangles {scene.counts} ({time.time() - t0:.1f} s)")
    R0, C0 = rig.lens(np.zeros(6))
    t0 = time.time()
    img = render(scene, R0, C0, rig.K_sim[0, 0])
    print(f"render 640x480: {time.time() - t0:.2f} s")
    ref = c1_class_mask()
    m, per = mean_iou(img, ref)
    print(f"vs C1 instance masks: mean IoU {m:.4f}; " + ", ".join(f"{k} {v:.3f}" for k, v in per.items()))
    agree = float((img == ref).mean())
    print(f"pixel agreement {agree:.4f}")
    return {"rig_check": rig.rig_check, "t06": t06, "c1_mean_iou": m, "c1_per_class": per, "pixel_agreement": agree}


def cmd_match(a):
    frames = json.loads(FRAMES.read_text())
    rig = Rig(frames)
    intr = json.loads(Path(a.intrinsics).read_text())
    K = np.array(intr["K"], float)
    fx, fy = float(K[0, 0]), float(K[1, 1])
    f_sim = float(rig.K_sim[0, 0])
    gap = 100 * (fx / f_sim - 1)
    print(f"fx {fx:.2f} px (fy {fy:.2f}; sim {f_sim:.2f}), gap {gap:+.2f} %; sim focal {fx * HAP_MM / 640:.6f} mm")
    scene = Scene(frames)
    res = match(scene, rig, fx, max_evals=a.max_evals)
    p = res["lens_params"]
    off = rig.offsets_for_lens(*lens_move(*rig.lens(np.zeros(6)), p))
    R_chk, C_chk = rig.lens(off)
    R_exp, C_exp = lens_move(*rig.lens(np.zeros(6)), p)
    assert np.linalg.norm(C_chk - C_exp) < 1e-9 and np.abs(R_chk - R_exp).max() < 1e-9
    rep = full_res_report(scene, rig, fx, p)
    dolly = full_res_report(scene, rig, fx, [0, 0, res["dolly_only_tz_mm"], 0, 0, 0])
    out = {
        "utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "intrinsics": {"path": str(a.intrinsics), "sha256": hashlib.sha256(Path(a.intrinsics).read_bytes()).hexdigest(),
                       "status": intr.get("status"), "fx": fx, "fy": fy, "cx": float(K[0, 2]), "cy": float(K[1, 2]),
                       "dist": intr.get("dist")},
        "fx_sim": f_sim, "fx_gap_pct": gap, "camera_focal_mm": fx * HAP_MM / 640,
        "not_represented": "fy/fx, cx, cy and distortion: the sim camera is a square-pixel pinhole centred on the image",
        "lens_params": {"t_mm_cam_xyz": p[:3].tolist(), "r_deg_cam_xyz": p[3:].tolist()},
        "camera_offsets": offsets_dict(off),
        "lens": lens_summary(rig, p),
        "lens_inside_box": bool(inside_box(frames, C_chk)[0]), "lens_margin_to_box_m": inside_box(frames, C_chk)[1],
        "iou_full_res": {"pose_matched": rep["iou_pose_matched"], "image_matched": rep["iou_image_matched"],
                         "dolly_only": dolly["iou_image_matched"], "dolly_only_tz_mm": res["dolly_only_tz_mm"],
                         "per_class_pose_matched": rep["iou_pose_matched_per_class"],
                         "per_class_image_matched": rep["iou_image_matched_per_class"]},
        "search": {"dof": "6, lens frame (tx, ty, tz mm; rx, ry, rz deg), converted exactly to mount offsets",
                   "start": "best dolly tz on a 5 mm grid (-150..+150 mm), then the fixed STARTS offsets around it",
                   "optimiser": "Nelder-Mead from each start (steps 5 mm / 0.5 deg), best one polished (2 mm / 0.2 deg)",
                   "resolution": "320x240 search, 640x480 report", "evals": res["evals"], "starts": res["starts"]},
        "scene": {"frames_sim_sha256": hashlib.sha256(FRAMES.read_bytes()).hexdigest(), "triangles": int(len(scene.tris)),
                  "counts": scene.counts},
        "code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    print(f"image-matched: lens move {np.round(p[:3], 1).tolist()} mm (cam x right, y down, z forward), "
          f"{np.round(p[3:], 2).tolist()} deg")
    print(f"  camera offsets: " + ", ".join(f"{k} {v:+.5f}" for k, v in out["camera_offsets"].items()))
    print(f"  lens inside the box: {out['lens_inside_box']} (nearest panel or the open front {out['lens_margin_to_box_m'] * 100:.1f} cm)")
    print(f"  mean IoU vs the D455 view: pose-matched {rep['iou_pose_matched']:.4f} -> image-matched "
          f"{rep['iou_image_matched']:.4f} (dolly only {dolly['iou_image_matched']:.4f} at tz {res['dolly_only_tz_mm']:+.0f} mm)")
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(json.dumps(out, indent=1))
        print(f"wrote {a.out}")
    if a.png:
        save_png(a.png, rep)
        print(f"wrote {a.png}")
    return out


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("validate")
    m = sub.add_parser("match")
    m.add_argument("--intrinsics", required=True)
    m.add_argument("--out", default=str(GTC / "results" / "h4" / "image_matched_pose.json"))
    m.add_argument("--png", default=str(GTC / "results" / "h4" / "image_matched_masks.png"))
    m.add_argument("--max-evals", type=int, default=500)
    a = ap.parse_args(argv)
    if a.cmd == "validate":
        cmd_validate(a)
    else:
        if not Path(a.intrinsics).exists():
            raise SystemExit(f"STOP: {a.intrinsics} not found (C3 intrinsics first)")
        cmd_match(a)


if __name__ == "__main__":
    main(sys.argv[1:])
