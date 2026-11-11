#!/usr/bin/env python3
"""E3 renderer: class images of the course scene at any camera pose, with the rack movable.

Copied from gtc sim/image_matched_pose.py (gtc commit 58ffd9f, sha256 db83a6c3...2e606): the geometry helpers, the
camera rig (mount offsets <-> lens pose), the USD mesh loading and the numpy z-buffer rasteriser are verbatim; render()
gained depth=True. The scene is split for E3: the static part (lightbox panels, mat) and the rack (in its own frame,
origin = footprint corner O), so the rack can be re-posed and composited without re-rendering the rest. The robot and
the vials are not rendered: in a real photo their pixels are "don't care" (segment.py), because the arm's rest pose
and the layout change from photo to photo.

Pinhole model: square pixels, principal point at the image centre (as the sim's renderer). Real photos are mapped to
this ideal camera by segment.py (undistortion with the measured K and distortion onto K_ideal).
"""
import json
import math
from pathlib import Path

import numpy as np

W, H = 640, 480
NEAR = 0.01
CLASSES = ["background", "floor", "wall", "mat", "rack", "robot", "vial"]
E3_CLASSES = ["dont_care", "white", "mat", "rack"]            # floor and walls are one class in a photo (both white)
TO_E3 = np.array([0, 1, 1, 2, 3, 0, 0], np.int8)              # renderer class -> E3 class


# ---------------------------------------------------------------- geometry helpers (verbatim)
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



# ---------------------------------------------------------------- camera rig (verbatim)
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


# ---------------------------------------------------------------- USD meshes (verbatim)
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



# ---------------------------------------------------------------- z-buffer rasteriser (verbatim + depth)
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


def render(scene, R_cv, C, f, w=W, h=H, max_cand=4_000_000, depth=False):
    """Class image (h, w) int8: pixel centres, nearest surface wins. f = fx = fy in px at this resolution.
    depth=True also returns the winning 1/z per pixel (-inf where nothing), for compositing parts rendered apart."""
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
        return (out.reshape(h, w), best.reshape(h, w)) if depth else out.reshape(h, w)
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
    return (out.reshape(h, w), best.reshape(h, w)) if depth else out.reshape(h, w)



# ---------------------------------------------------------------- optimiser (verbatim)
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



# ---------------------------------------------------------------- scene for E3
class Scene:
    """Static triangles (panels, mat) and the rack's triangles in the rack frame (origin O, axes of the dumped pose)."""

    def __init__(self, frames, usd_dir):
        usd_dir = Path(usd_dir)
        tris, cls, closed = [], [], []
        for name, pnl in frames["lightbox_panels"].items():
            lo, hi = np.array(pnl["world_bbox_min"]), np.array(pnl["world_bbox_max"])
            t = _box(lo, hi)
            tris.append(t)
            cls.append(np.full(len(t), CLASSES.index("floor" if name == "Base" else "wall"), np.int8))
            closed.append(np.full(len(t), True))
        _, _, ms = _file_meshes(usd_dir / "mat.usda")
        R, t = rowmat(frames["mat"]["world_usd"]["matrix_row_major_usd"])
        for _, tr in ms:
            p = _place(tr, R, t)
            tris.append(p)
            cls.append(np.full(len(p), CLASSES.index("mat"), np.int8))
            closed.append(np.full(len(p), False))
        self.static = _Part(np.concatenate(tris), np.concatenate(cls), np.concatenate(closed))
        rk = frames["objects_after_warmup10"]["rack_left"]
        self.R_rack, self.O_rack = quat_to_R(rk["quat_wxyz"]), np.array(rk["pos"], float)
        _, _, ms = _file_meshes(usd_dir / "Vial_rack_simple.usda")
        self.rack_local = np.concatenate([tr for _, tr in ms])          # file frame = rack frame (origin O)
        self.rack_cls = np.full(len(self.rack_local), CLASSES.index("rack"), np.int8)

    def rack_part(self, dx=0.0, dy=0.0, dyaw_deg=0.0):
        """The rack moved by (dx, dy) m in E and turned by dyaw about its corner O (Appendix C rack_delta)."""
        c, s = math.cos(math.radians(dyaw_deg)), math.sin(math.radians(dyaw_deg))
        Rz = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.0]])
        R = Rz @ self.R_rack
        return _Part(self.rack_local @ R.T + self.O_rack + np.array([dx, dy, 0.0]), self.rack_cls,
                     np.zeros(len(self.rack_cls), bool))


class _Part:
    def __init__(self, tris, cls, closed):
        self.tris, self.cls, self.closed = np.asarray(tris, np.float64), np.asarray(cls, np.int8), np.asarray(closed, bool)


def render_e3(scene, R_cv, C, f, w, h, rack=(0.0, 0.0, 0.0), static=None):
    """E3 class image: the static part, the rack composited by depth. static = a cached (cls, invz) of the static part."""
    s_cls, s_inv = static if static is not None else render(scene.static, R_cv, C, f, w, h, depth=True)
    r_cls, r_inv = render(scene.rack_part(*rack), R_cv, C, f, w, h, depth=True)
    out = TO_E3[s_cls].copy()
    out[(s_cls == 0) & ~np.isfinite(s_inv)] = 0
    m = r_inv > s_inv
    out[m] = TO_E3[r_cls[m]]
    return out


def save_cache(scene, path):
    """The scene's triangles as an .npz (built where pxr exists; read anywhere, e.g. our Isaac container's python)."""
    np.savez_compressed(path, static_tris=scene.static.tris, static_cls=scene.static.cls, static_closed=scene.static.closed,
                        rack_local=scene.rack_local, rack_cls=scene.rack_cls, R_rack=scene.R_rack, O_rack=scene.O_rack)


def load_scene(frames_path, usd_dir=None, cache=None):
    """(Scene, Rig). With cache (an .npz from save_cache) no USD is read; the Rig always comes from the frames JSON."""
    fr = json.loads(Path(frames_path).read_text())
    if cache and Path(cache).exists():
        z = np.load(cache)
        sc = Scene.__new__(Scene)
        sc.static = _Part(z["static_tris"], z["static_cls"], z["static_closed"])
        sc.rack_local, sc.rack_cls, sc.R_rack, sc.O_rack = z["rack_local"], z["rack_cls"], z["R_rack"], z["O_rack"]
        return sc, Rig(fr)
    return Scene(fr, usd_dir), Rig(fr)


if __name__ == "__main__":                       # python -I render.py cache --frames F --usd-dir D --out cache/scene.npz
    import argparse
    import sys
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["cache"])
    ap.add_argument("--frames", required=True)
    ap.add_argument("--usd-dir", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(sys.argv[1:])
    sc, _ = load_scene(a.frames, a.usd_dir)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    save_cache(sc, a.out)
    print(f"cache {a.out}: {len(sc.static.tris)} static + {len(sc.rack_local)} rack triangles")
