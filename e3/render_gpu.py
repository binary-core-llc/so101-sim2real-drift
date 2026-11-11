#!/usr/bin/env python3
"""E3 renderer on the GPU (CUDA PyTorch): the same z-buffer as render.py, one pose at a time, fully vectorised.

Pixel centres, perspective-correct 1/z, the nearest surface wins (scatter max), the same back-face culling of the
closed lightbox panels and the same near-plane clipping (the few static triangles that cross z = NEAR are clipped on
the CPU by render._clip_near, then uploaded). float32 on the GPU: class images match render.py except where two
surfaces tie at an edge pixel (tested in bench.py). Backend for estimate.py (camera_images / rack_images).
"""
import math

import numpy as np
import torch

import render as Rn

MAX_CAND = 24_000_000


class TorchBackend:
    name = "torch-cuda"

    def __init__(self, scene, device="cuda"):
        self.dev = torch.device(device)
        self.scene = scene
        self.rack_local = torch.tensor(scene.rack_local, dtype=torch.float32, device=self.dev)
        self.R_rack = torch.tensor(scene.R_rack, dtype=torch.float32, device=self.dev)
        self.O_rack = torch.tensor(scene.O_rack, dtype=torch.float32, device=self.dev)
        self.rack_cls = torch.tensor(scene.rack_cls.astype(np.int64), device=self.dev)
        self.to_e3 = torch.tensor(Rn.TO_E3.astype(np.int64), device=self.dev)

    # ------------------------------------------------------------ raster
    def _static_cam(self, R, C):
        """Static triangles in camera coordinates, culled and clipped exactly as render.render (CPU, 72 triangles)."""
        sc = self.scene.static
        T = sc.tris
        keep = np.ones(len(T), bool)
        n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
        front = np.einsum("ij,ij->i", n, C - T[:, 0]) > 0
        keep &= ~sc.closed | front
        X = (T[keep] - C) @ R
        cls = sc.cls[keep]
        z = X[..., 2]
        allin = (z >= Rn.NEAR).all(1)
        part = ~allin & (z >= Rn.NEAR).any(1)
        Xs, cs = [X[allin]], [cls[allin]]
        for i in np.where(part)[0]:
            c = Rn._clip_near(X[i:i + 1], Rn.NEAR)
            Xs.append(c)
            cs.append(np.full(len(c), cls[i], np.int8))
        return (torch.tensor(np.concatenate(Xs), dtype=torch.float32, device=self.dev),
                torch.tensor(np.concatenate(cs).astype(np.int64), device=self.dev))

    def _raster(self, X, cls, f, w, h):
        """(class (h*w,) int64, best 1/z (h*w,) float32) for camera-space triangles X (M, 3, 3), all at z >= NEAR."""
        dev = self.dev
        best = torch.full((w * h,), -math.inf, device=dev)
        out = torch.zeros(w * h, dtype=torch.int64, device=dev)
        if len(X) == 0:
            return out, best
        z = X[..., 2]
        u = f * X[..., 0] / z + w / 2.0
        v = f * X[..., 1] / z + h / 2.0
        i0 = torch.clamp(torch.ceil(u.min(1).values - 0.5), 0, w).long()
        i1 = torch.clamp(torch.floor(u.max(1).values - 0.5), -1, w - 1).long()
        j0 = torch.clamp(torch.ceil(v.min(1).values - 0.5), 0, h).long()
        j1 = torch.clamp(torch.floor(v.max(1).values - 0.5), -1, h - 1).long()
        bw, bh = i1 - i0 + 1, j1 - j0 + 1
        idx = torch.nonzero((bw > 0) & (bh > 0)).squeeze(1)
        if len(idx) == 0:
            return out, best
        cnt = (bw[idx] * bh[idx])
        cum = torch.cumsum(cnt, 0)
        wins = []
        lo, total = 0, int(cum[-1])
        starts = torch.cat([torch.zeros(1, dtype=cum.dtype, device=dev), cum[:-1]])
        while lo < len(idx):                                   # chunks of triangles bound the candidate arrays
            base = int(starts[lo])
            hi = int(torch.searchsorted(cum, torch.tensor(base + MAX_CAND, device=dev), right=True))
            hi = max(hi, lo + 1)
            t = idx[lo:hi]
            c = cnt[lo:hi]
            rep = torch.repeat_interleave(torch.arange(len(t), device=dev), c)
            k = torch.arange(int(c.sum()), device=dev) - torch.repeat_interleave(torch.cumsum(c, 0) - c, c)
            tt = t[rep]
            bwt = bw[tt]
            px = (i0[tt] + k % bwt).float() + 0.5
            py = (j0[tt] + torch.div(k, bwt, rounding_mode="floor")).float() + 0.5
            u0, u1, u2 = u[tt, 0], u[tt, 1], u[tt, 2]
            v0, v1, v2 = v[tt, 0], v[tt, 1], v[tt, 2]
            area = (u1 - u0) * (v2 - v0) - (u2 - u0) * (v1 - v0)
            w0 = (u2 - u1) * (py - v1) - (v2 - v1) * (px - u1)
            w1 = (u0 - u2) * (py - v2) - (v0 - v2) * (px - u2)
            w2 = (u1 - u0) * (py - v0) - (v1 - v0) * (px - u0)
            sg = torch.sign(area)
            inside = (area != 0) & (w0 * sg >= 0) & (w1 * sg >= 0) & (w2 * sg >= 0)
            tt, px, py, area, w0, w1, w2 = tt[inside], px[inside], py[inside], area[inside], w0[inside], w1[inside], w2[inside]
            invz = (w0 / z[tt, 0] + w1 / z[tt, 1] + w2 / z[tt, 2]) / area
            pix = (py - 0.5).long() * w + (px - 0.5).long()
            best.scatter_reduce_(0, pix, invz, reduce="amax")
            wins.append((pix, invz, cls[tt]))
            lo = hi
        for pix, invz, cl in wins:
            m = invz >= best[pix]
            out[pix[m]] = cl[m]
        return out, best

    def _e3(self, R, C, f, w, h, rack_xyz=(0.0, 0.0, 0.0), static=None):
        s_cls, s_inv = static if static is not None else self._raster(*self._static_cam(R, C), f, w, h)
        dx, dy, dyaw = rack_xyz
        c, s_ = math.cos(math.radians(dyaw)), math.sin(math.radians(dyaw))
        Rz = torch.tensor([[c, -s_, 0], [s_, c, 0], [0, 0, 1.0]], dtype=torch.float32, device=self.dev)
        Rr = Rz @ self.R_rack
        W = self.rack_local @ Rr.T + self.O_rack + torch.tensor([dx, dy, 0.0], dtype=torch.float32, device=self.dev)
        Rt = torch.tensor(R, dtype=torch.float32, device=self.dev)
        Ct = torch.tensor(C, dtype=torch.float32, device=self.dev)
        X = (W - Ct) @ Rt                                   # the rack never crosses the near plane in a front view
        keep = (X[..., 2] >= Rn.NEAR).all(1)
        r_cls, r_inv = self._raster(X[keep], self.rack_cls[keep], f, w, h)
        out = self.to_e3[s_cls]
        out[(s_cls == 0) & torch.isinf(s_inv)] = 0
        m = r_inv > s_inv
        out[m] = self.to_e3[r_cls[m]]
        return out.view(h, w)

    # ------------------------------------------------------------ estimate.py backend
    def camera_images(self, R0, C0, P, f, w, h):
        ims = []
        for p in P:
            R, C = Rn.lens_move(R0, C0, p)
            ims.append(self._e3(R, C, f, w, h))
        return [im.to(torch.uint8).cpu().numpy() for im in ims]

    def rack_images(self, R, C, Q, f, w, h):
        st = self._raster(*self._static_cam(R, C), f, w, h)
        ims = [self._e3(R, C, f, w, h, (q[0] / 1000, q[1] / 1000, q[2]), static=st) for q in Q]
        return [im.to(torch.uint8).cpu().numpy() for im in ims]
