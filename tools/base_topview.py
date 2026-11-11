#!/usr/bin/env python3
"""Top view of the SO-101 base from the course USD, with the sled datums (B 4.2) to measure on the real base.

    .venv/bin/python -I tools/base_topview.py            # writes results/rig/base_topview_cad.png
Mesh /visuals/base/base_so101_v2 of SO-ARM101-USD.usd (course repo @ ce807d9), placed at the robot root
(-0.05, 0, 0) with yaw +90 like tools/r0_pose.py (env x = -0.05 - local y, env y = local x). Seen from above,
front (+x, the side the arm reaches toward) at the top, +y (camera wall) to the left.
"""
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pxr import Usd, UsdGeom

GTC = Path(__file__).resolve().parents[1]
USD = GTC.parent / "Sim-to-Real-SO-101-Workshop/source/sim_to_real_so101/assets/usd/SO-ARM101-USD.usd"
OUT = GTC / "results" / "rig" / "base_topview_cad.png"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
S, W, H, V0 = 10, 1800, 1760, 330          # px per mm, canvas, image row of the front line
Y_AXIS = 20.8                              # pan-axis y (mm), the base's centre line


def mesh_tris(st, path):
    """Triangles (n, 3, 3) of one mesh in env coordinates, mm."""
    p = st.GetPrimAtPath(path)
    m = UsdGeom.Mesh(p)
    pts = np.array(m.GetPointsAttr().Get())
    M = np.array(UsdGeom.XformCache().GetLocalToWorldTransform(p))
    w = pts @ M[:3, :3] + M[3, :3]
    env = np.c_[-0.05 - w[:, 1], w[:, 0], w[:, 2]] * 1000
    cnt, idx, tris, o = m.GetFaceVertexCountsAttr().Get(), np.array(m.GetFaceVertexIndicesAttr().Get()), [], 0
    for c in cnt:
        f = idx[o:o + c]
        o += c
        tris += [(f[0], f[k], f[k + 1]) for k in range(1, c - 1)]
    return env[np.array(tris)]


def gap_at(tris, depth, x_front, z):
    """Gap between the lobes' inner faces and their outer span, `depth` mm behind the front line, at height z."""
    x, ys = x_front - depth, []
    for t in tris:
        d = t[:, 2] - z
        if (d > 0).all() or (d < 0).all():
            continue
        P = [t[a] + (t[b] - t[a]) * (d[a] / (d[a] - d[b])) for a, b in ((0, 1), (1, 2), (2, 0)) if (d[a] > 0) != (d[b] > 0)]
        if len(P) == 2 and (P[0][0] - x) * (P[1][0] - x) < 0:
            a, b = P
            ys.append(a[1] + (b[1] - a[1]) * (x - a[0]) / (b[0] - a[0]))
    ys = np.sort(ys)
    lo, hi = ys[ys < Y_AXIS].max(), ys[ys > Y_AXIS].min()
    return hi - lo, ys.max() - ys.min(), lo, hi


def main():
    st = Usd.Stage.Open(str(USD))
    base = mesh_tris(st, "/visuals/base/base_so101_v2/mesh")
    motor = np.concatenate([mesh_tris(st, f"/visuals/base/{n}/mesh") for n in ("base_motor_holder_so101_v1", "sts3215_03a_v1")])
    board = mesh_tris(st, "/visuals/base/waveshare_mounting_plate_so101_v2/mesh")
    x_front, x_rear = base[..., 0].max(), base[..., 0].min()
    y_min, y_max = base[..., 1].min(), base[..., 1].max()
    z_tongue = base[..., 2].min() + 7.5                     # mid-height of the sled tongue (B 4.2: z 0.035-0.040)
    g2, o2, lo2, hi2 = gap_at(base, 2.0, x_front, z_tongue)
    g5, _, lo5, hi5 = gap_at(base, 5.0, x_front, z_tongue)
    print(f"front x {x_front:.2f}  rear x {x_rear:.2f}  depth {x_front - x_rear:.1f}  side span {y_max - y_min:.1f} mm")
    print(f"2 mm behind: gap {g2:.1f}, outer span {o2:.1f};  5 mm behind: gap {g5:.1f} mm")

    U = lambda y: W / 2 + (Y_AXIS - y) * S
    V = lambda x: V0 + (x_front - x) * S

    def mask(tris):
        m = np.zeros((H, W), np.uint8)
        for t in tris:
            cv2.fillConvexPoly(m, np.round(np.c_[U(t[:, 1]), V(t[:, 0])] * 4).astype(np.int32), 255, cv2.LINE_8, 2)
        return m

    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    f, fb, fs, fbig = (ImageFont.truetype(FONT, 26), ImageFont.truetype(BOLD, 28),
                       ImageFont.truetype(FONT, 22), ImageFont.truetype(BOLD, 34))
    RED, BLUE, GREEN, GREY, INK = (200, 30, 30), (30, 80, 200), (20, 130, 60), (150, 150, 150), (30, 30, 30)

    def arrow(p, q, col, w=3):
        d.line([p, q], fill=col, width=w)
        for a, b in ((p, q), (q, p)):
            v = np.subtract(b, a) / max(np.hypot(*np.subtract(b, a)), 1)
            n = np.array([-v[1], v[0]])
            tip = np.array(b, float)
            d.polygon([tuple(tip), tuple(tip - 16 * v + 7 * n), tuple(tip - 16 * v - 7 * n)], fill=col)

    def badge(c, k, col):
        d.ellipse([c[0] - 19, c[1] - 19, c[0] + 19, c[1] + 19], fill=col)
        d.text(c, str(k), font=fb, fill="white", anchor="mm")

    # 6: side span (done), drawn first so the base hides its middle
    v6 = V(-46.5)
    arrow((U(y_max) - 120, v6), (U(y_max), v6), GREY)
    arrow((U(y_min) + 120, v6), (U(y_min), v6), GREY)
    badge((U(y_max) - 200, v6 - 40), 6, GREY)
    d.text((U(y_max) - 170, v6 - 40), "111.0 (done)", font=f, fill=GREY, anchor="lm")

    for m, fill in ((mask(board), (225, 225, 225)), (mask(base), (246, 205, 160)), (mask(motor), (185, 185, 185))):
        layer = Image.new("RGB", (W, H), fill)
        img.paste(layer, (0, 0), Image.fromarray(m))
        cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        for c in cs:
            d.line([tuple(p[0]) for p in c] + [tuple(c[0][0])], fill=INK, width=2)

    # front line (5) and rear edge
    d.line([(U(y_max) - 60, V(x_front)), (U(y_min) + 60, V(x_front))], fill=RED, width=3)
    d.text((U(y_min) + 70, V(x_front)), "FRONT LINE", font=fb, fill=RED, anchor="lm")
    badge((U(y_min) + 300, V(x_front)), 5, RED)
    d.line([(U(y_max) - 60, V(x_rear)), (U(y_min) + 60, V(x_rear))], fill=BLUE, width=3)
    d.text((U(y_min) + 70, V(x_rear)), "REAR EDGE", font=fb, fill=BLUE, anchor="lm")
    d.text((U(y_min) + 70, V(x_rear) + 30), "(bottom plate)", font=fs, fill=BLUE, anchor="lm")

    # 1: outer span, above the tips with extension lines
    v1 = V(x_front) - 110
    for y in (lo2 - g2 / 2 + g2 / 2 - (o2 - g2) / 2, hi2 + (o2 - g2) / 2):
        d.line([(U(y), v1 - 15), (U(y), V(x_front - 2.0))], fill=GREEN, width=2)
    arrow((U(hi2 + (o2 - g2) / 2), v1), (U(lo2 - (o2 - g2) / 2), v1), GREEN)
    badge((W / 2 - 110, v1 - 34), 1, GREEN)
    d.text((W / 2 - 80, v1 - 34), "66.5 mm", font=fb, fill=GREEN, anchor="lm")
    # 2 and 3: gaps, inside the gap at 2 and 5 mm behind the front line
    arrow((U(hi2), V(x_front - 2.0)), (U(lo2), V(x_front - 2.0)), RED)
    badge((W / 2 - 130, V(x_front - 2.0) - 34), 2, RED)
    d.text((W / 2 - 100, V(x_front - 2.0) - 34), "44.6 mm", font=fb, fill=RED, anchor="lm")
    arrow((U(hi5), V(x_front - 5.0)), (U(lo5), V(x_front - 5.0)), (190, 90, 0))
    badge((W / 2 - 130, V(x_front - 5.0) + 36), 3, (190, 90, 0))
    d.text((W / 2 - 100, V(x_front - 5.0) + 36), f"{g5:.1f} mm", font=fb, fill=(190, 90, 0), anchor="lm")
    # 4: depth, right of the base
    u4 = U(y_min) + 90
    arrow((u4, V(x_front)), (u4, V(x_rear)), BLUE)
    badge((u4, (V(x_front) + V(x_rear)) / 2 - 30), 4, BLUE)
    d.text((u4 + 28, (V(x_front) + V(x_rear)) / 2 + 10), "86.9 mm", font=fb, fill=BLUE, anchor="lm")

    # names
    for y_tip, side in ((hi2 + (o2 - g2) / 4, -1), (lo2 - (o2 - g2) / 4, 1)):
        p = (U(y_tip), V(x_front - 1))
        q = (W / 2 + side * 640, V0 - 110)
        d.line([(q[0], q[1] + 38), p], fill=INK, width=2)
        d.text(q, "LOBE", font=fbig, fill=INK, anchor="mb")
        d.text((q[0], q[1] + 4), "(front tip of a lattice wing)", font=fs, fill=INK, anchor="mt")
    px, py = U(Y_AXIS), V(-26.9)
    d.line([(px - 18, py), (px + 18, py)], fill=INK, width=3)
    d.line([(px, py - 18), (px, py + 18)], fill=INK, width=3)
    d.text((U(y_max) - 70, V(-20)), "turntable motor (grey)", font=fs, fill=INK, anchor="rm")
    d.text((U(y_max) - 70, V(-27)), "+ = turntable centre", font=fs, fill=INK, anchor="rm")
    d.text((U(y_min) - 280, V(-93)), "driver-board plate: ignore", font=fs, fill=GREY, anchor="lm")
    d.text((W / 2, 36), "SO-101 follower base, seen from above (course USD)", font=fbig, fill=INK, anchor="mt")
    d.text((W / 2, 80), "FRONT (the side the arm reaches toward) at the top", font=f, fill=INK, anchor="mt")

    # legend: one line per measurement
    rows = [(1, GREEN, "Outer span of the two lobes, at their outer corners (2 mm behind the front line): CAD 66.5 mm"),
            (2, RED, "Gap between the lobes, at their inner corners (2 mm behind the front line): CAD 44.6 mm"),
            (3, (190, 90, 0), f"Gap between the lobes, 5 mm behind the front line (sizes the sled key): CAD {g5:.1f} mm"),
            (4, BLUE, "Depth, front line to the rear edge of the bottom plate: CAD 86.9 mm"),
            (5, RED, "Both lobe tips touch one straight edge laid across them: yes / no"),
            (6, GREY, "Side span (done): 111 mm, CAD 111.0")]
    y0 = V(x_rear) + 130
    for i, (k, col, t) in enumerate(rows):
        badge((70, y0 + i * 50), k, col)
        d.text((105, y0 + i * 50), t, font=f, fill=INK, anchor="lm")
    d.text((70, y0 + 6 * 50 + 10), "Don't cut the sled key yet: the gap narrows behind the tips (2 → 3).",
           font=fb, fill=RED, anchor="lm")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT)
    print(f"wrote {OUT.relative_to(GTC)}")


if __name__ == "__main__":
    main()
