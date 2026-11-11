#!/usr/bin/env python3
"""V05: 1:1 vial stencils for layouts L00-L09 (config/layouts.json), US Letter landscape, 2 sets.

    .venv/bin/python -I tools/make_stencils.py            -> stencils/stencils_letter_setA.pdf, _setB.pdf, _both.pdf
                                                             (+ optional Tabloid variant flush with the front-right corner)

Geometry (mat frame, mm): u from the mat's front edge toward the back wall, v from the mat's right edge.
Each window = the simulated vial's top-view outline (Vial_opaque.usda body + cap meshes at the layout's
settled pose, after the 10 warm-up steps) grown by 3 mm. Caps point to the back wall (top of the sheet).

Why the sheet is registered this way: the windows span about u 104-301 mm and v 19-280 mm, so no Letter
sheet can also contain the mat's front-right corner (u 0, v 0). The sheet's right edge is cut on a printed
TRIM line (v = 0) and laid flush on the mat's right edge; a printed line at u = 100 mm is set 100.0 mm from
the mat's front edge with the metal ruler (the front-right corner is the zero). Printed lines, not paper
edges, are the datums, so a printer offset does not move the windows.
"""
import hashlib
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from pxr import Usd, UsdGeom
from reportlab.lib.pagesizes import letter, landscape, TABLOID
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]
VIAL_USD = ROOT.parent / "Sim-to-Real-SO-101-Workshop/source/sim_to_real_so101/assets/usd/Vial_opaque.usda"
GROW_MM = 3.0
VIALS = ("vial_1", "vial_2", "vial_3")


def vial_local_points():
    """Body + cap mesh points in the vial root frame (m)."""
    st = Usd.Stage.Open(str(VIAL_USD))
    root = st.GetPrimAtPath("/Vial")
    cache = UsdGeom.XformCache()
    pts = []
    for name in ("Mesh_002", "Mesh_001", "Mesh"):
        p = st.GetPrimAtPath(f"/Vial/{name}")
        m, _ = cache.ComputeRelativeTransform(p, root)
        for q in UsdGeom.Mesh(p).GetPointsAttr().Get():
            pts.append(list(m.Transform(q)))
    return np.array(pts)


def qrot(q):
    w, x, y, z = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
                     [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
                     [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)]])


def hull(pts2):
    h = cv2.convexHull(np.asarray(pts2, np.float32))
    return h.reshape(-1, 2).astype(float)


def grow(poly, r, n=72):
    ang = np.linspace(0, 2 * np.pi, n, endpoint=False)
    circ = np.c_[np.cos(ang), np.sin(ang)] * r
    return hull((poly[:, None, :] + circ[None, :, :]).reshape(-1, 2))


def vial_outline_uv(rec, mat, local):
    R = qrot(rec["quat_wxyz"])
    w = local @ R.T + np.array(rec["pos_env"])
    uv = np.c_[(w[:, 0] - mat["front_x"]) * 1000, (w[:, 1] - mat["right_y"]) * 1000]
    return hull(uv)


class Sheet:
    """Maps mat (u, v) mm to page points; page origin bottom-left."""

    def __init__(self, page, u0, v_right_inset):
        self.W, self.H = page[0] / mm, page[1] / mm   # page size in mm
        self.u0, self.inset = u0, v_right_inset

    def xy(self, u, v):
        return ((self.W - self.inset - v) * mm, (u - self.u0) * mm)


def free_spot(sheet, polys_uv, w_mm, h_mm, margin=4.0, prefer=None, u_range=None):
    """First page rectangle (mm) of size w x h that avoids all windows (+margin) and the page edges,
    optionally kept inside a u range (the part of the sheet that stays after trimming)."""
    occ = np.zeros((int(sheet.H) + 1, int(sheet.W) + 1), np.uint8)
    for poly in polys_uv:
        pts = np.array([[(sheet.W - sheet.inset - v), (u - sheet.u0)] for u, v in poly], np.int32)
        cv2.fillPoly(occ, [pts], 1)
    occ = cv2.dilate(occ, np.ones((int(2 * margin) + 1,) * 2, np.uint8))
    ylo, yhi = 10, int(sheet.H - h_mm - 8)
    if u_range is not None:
        ylo = max(ylo, int(u_range[0] - sheet.u0 + 6))
        yhi = min(yhi, int(u_range[1] - sheet.u0 - h_mm - 6))
    cands = [(x, y) for y in range(yhi, ylo, -2) for x in range(10, int(sheet.W - sheet.inset - w_mm - 22), 2)]
    if prefer == "bottom":
        cands = sorted(cands, key=lambda c: c[1])
    for x, y in cands:
        if not occ[y:y + int(h_mm), x:x + int(w_mm)].any():
            return x, y
    return None


def _poly_gap(A, B, n=40):
    """Smallest distance between two polygon outlines (mm) and the closest points."""
    def dense(P):
        Q = np.vstack([P, P[:1]])
        t = np.linspace(0, 1, n)[:, None]
        return np.vstack([a + t * (b - a) for a, b in zip(Q[:-1], Q[1:])])
    a, b = dense(A), dense(B)
    d = np.linalg.norm(a[:, None, :] - b[None, :, :], axis=2)
    i, j = np.unravel_index(np.argmin(d), d.shape)
    return float(d[i, j]), a[i], b[j]


def cut_notes(L, polys, sheet, variant, bridge_mm=1.0):
    """Cutting notes printed on the sheet, found from the geometry (window numbers = vial numbers)."""
    notes = []
    for i, w in enumerate(polys, 1):
        if max(v for _, v in w) - (sheet.W - sheet.inset) > -4.5:   # within the printer's edge or beyond the paper
            notes.append(f"NOTE: window {i} reaches the LEFT paper edge: cut it open to the edge.")
        if variant == "tabloid" and max(u for u, _ in w) > 304.8:   # the back trim line (mat back edge)
            notes.append(f"NOTE: window {i} reaches the back trim line: cut it open to the edge.")
    for a in range(len(polys)):
        for b in range(a + 1, len(polys)):
            gap, pa, pb = _poly_gap(polys[a], polys[b])
            if gap < bridge_mm:   # no paper bridge this thin survives cutting
                ends = []
                for p, v in ((pa, VIALS[a]), (pb, VIALS[b])):
                    rec = L["vials"][v]
                    dc = np.linalg.norm(p - np.array(rec["cap_uv_mm"]))
                    dt = np.linalg.norm(p - np.array(rec["tip_uv_mm"]))
                    ends.append("cap" if dc < dt else "tip")
                where = f"{ends[0]}s" if ends[0] == ends[1] else "ends"
                notes.append(f"NOTE: windows {a + 1} and {b + 1} touch at the {where}: cut them as one opening.")
    return notes


def draw_layout(c, L, mat, local, sheet, set_name, variant, meta):
    polys, sims, labels = [], [], []
    for i, v in enumerate(VIALS, 1):
        sim = vial_outline_uv(L["vials"][v], mat, local)
        win = grow(sim, GROW_MM)
        polys.append(win)
        sims.append(sim)
        labels.append((i, L["vials"][v]))
    W, H = sheet.W, sheet.H

    # windows (cut lines) and the simulated outline (thin grey dashes)
    for win, sim, (i, rec) in zip(polys, sims, labels):
        p = c.beginPath()
        x0, y0 = sheet.xy(*win[0])
        p.moveTo(x0, y0)
        for u, v in win[1:]:
            p.lineTo(*sheet.xy(u, v))
        p.close()
        c.setLineWidth(0.8)
        c.setStrokeColorRGB(0, 0, 0)
        c.setDash()
        c.drawPath(p, stroke=1, fill=0)
        p = c.beginPath()
        p.moveTo(*sheet.xy(*sim[0]))
        for u, v in sim[1:]:
            p.lineTo(*sheet.xy(u, v))
        p.close()
        c.setLineWidth(0.3)
        c.setStrokeColorRGB(0.55, 0.55, 0.55)
        c.setDash(2, 2)
        c.drawPath(p, stroke=1, fill=0)
        c.setDash()
        c.setStrokeColorRGB(0, 0, 0)
        cu, cv = rec["cap_uv_mm"]
        tu, tv = rec["tip_uv_mm"]
        mu, mv = rec["mid_uv_mm"]
        c.setFont("Helvetica-Bold", 9)
        x, y = sheet.xy(cu - 6, cv)
        c.drawCentredString(x, y - 3, "CAP")
        x, y = sheet.xy(tu + 6, tv)
        c.drawCentredString(x, y - 3, "tip")
        x, y = sheet.xy(mu, mv)
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(x, y - 5, str(i))

    # TRIM line at v = 0 (mat right edge)
    c.setLineWidth(0.6)
    c.setDash(6, 3)
    xr = (W - sheet.inset) * mm
    c.line(xr, 0, xr, H * mm)
    c.setDash()
    c.setFont("Helvetica-Bold", 7)
    c.drawRightString(xr - 1 * mm, H * mm - 4 * mm, "TRIM >")

    # front reference: a u-scale along the right edge (the strip v < 19 mm is free of windows on every layout)
    if variant == "letter":
        c.setLineWidth(0.5)
        for u in range(110, 301, 10):
            x0, y = sheet.xy(u, 0)
            x1, _ = sheet.xy(u, 9 if u % 50 == 0 else 5)
            c.setLineWidth(1.2 if u == 150 else 0.5)
            c.line(x1, y, x0, y)
            if u % 50 == 0:
                c.setFont("Helvetica-Bold" if u == 150 else "Helvetica", 7)
                c.drawRightString(x1 - 1 * mm, y - 1 * mm, f"u {u}")
    else:  # tabloid: trim line at u = 0 makes the sheet's corner the mat's front-right corner
        _, yf = sheet.xy(0, 0)
        c.setDash(6, 3)
        c.line(0, yf, W * mm, yf)
        _, yb = sheet.xy(304.8, 0)
        c.line(0, yb, W * mm, yb)
        c.setDash()
        c.setFont("Helvetica-Bold", 8)
        c.drawString(10 * mm, yf + 1.5 * mm, "TRIM ON THIS LINE (mat FRONT edge). After both trims, this corner = the mat's FRONT-RIGHT corner.")
        c.drawString(10 * mm, yb + 1.5 * mm, "TRIM ON THIS LINE (mat BACK edge, u = 304.8 mm) so the sheet clears the back wall.")
        x, y = sheet.xy(0, 0)
        c.setLineWidth(1.5)
        c.line(x, y, x - 15 * mm, y)
        c.line(x, y, x, y + 15 * mm)
        c.setFont("Helvetica-Bold", 9)
        c.drawRightString(x - 2 * mm, y + 4 * mm, "MAT FRONT-RIGHT CORNER")

    # labels in free space: big Lxx, then the info block and the 100 mm check line
    ur = (0.0, 304.8) if variant == "tabloid" else None
    spot = free_spot(sheet, polys, 62, 30, u_range=ur)
    if spot:
        c.setFont("Helvetica-Bold", 72)
        c.drawString(spot[0] * mm, (spot[1] + 4) * mm, L["layout_id"])
    if variant == "letter":
        lines = ["1. Trim the dashed line at the right edge.",
                 "2. Cut edge flush on the mat's RIGHT edge; BACK WALL",
                 "    label toward the back wall.",
                 "3. Ruler zero on the mat's FRONT-RIGHT corner, along",
                 "    the right edge: slide until bold 'u 150' reads 150.0 mm.",
                 "4. Vials in windows, cap at CAP. Lift the sheet straight up.",
                 "    Remove it before every trial."]
    else:
        lines = ["1. Trim the 3 dashed lines (right, front, back).",
                 "2. Cut corner on the mat's FRONT-RIGHT corner,",
                 "    cut edges flush on both mat edges.",
                 "3. Vials in windows, cap at CAP. Lift the sheet straight up.",
                 "    Remove it before every trial."]
    lines += cut_notes(L, polys, sheet, variant)
    lines += ["Windows = sim vial outline (grey dashes) + 3 mm.",
              f"{L['layout_id']} = sim seed {L['seed']} | set {set_name} | {variant} | {meta['sha'][:10]}"]
    bh = 3.4 * len(lines) + 11
    keep = list(polys)
    if spot:  # the big label's rectangle, in (u, v)
        u_lo, u_hi = spot[1] + sheet.u0 - 2, spot[1] + sheet.u0 + 32
        v_hi, v_lo = W - sheet.inset - spot[0] + 2, W - sheet.inset - spot[0] - 64
        keep.append(np.array([[u_lo, v_lo], [u_lo, v_hi], [u_hi, v_hi], [u_hi, v_lo]]))
    def draw_check(x, y):
        c.setLineWidth(0.8)
        c.line(x, y + 3 * mm, x + 100 * mm, y + 3 * mm)
        for xx in (x, x + 100 * mm):
            c.line(xx, y + 1 * mm, xx, y + 5 * mm)
        c.setFont("Helvetica-Bold", 7)
        c.drawString(x, y + 6.0 * mm, "CHECK FIRST: this line = 100.0 mm (print at 100%)")

    def draw_lines(x, y, ls):
        c.setFont("Helvetica", 6.5)
        for k, t in enumerate(reversed(ls)):
            c.drawString(x, y + 3.4 * k * mm, t)

    spot2 = free_spot(sheet, keep, 104, bh, margin=3.0, prefer="bottom", u_range=ur)
    if spot2 is not None:                       # one block: lines above the check line
        x, y = spot2[0] * mm, spot2[1] * mm
        draw_check(x, y)
        draw_lines(x, y + 10.0 * mm, lines)
    else:                                       # two blocks
        s_chk = free_spot(sheet, keep, 104, 11, margin=3.0, prefer="bottom", u_range=ur)
        if s_chk is None:
            raise RuntimeError(f"{L['layout_id']} {variant}: no free space for the 100 mm check line")
        keep.append(np.array([[s_chk[1] + sheet.u0 - 1, W - sheet.inset - s_chk[0] - 106],
                              [s_chk[1] + sheet.u0 - 1, W - sheet.inset - s_chk[0] + 1],
                              [s_chk[1] + sheet.u0 + 12, W - sheet.inset - s_chk[0] + 1],
                              [s_chk[1] + sheet.u0 + 12, W - sheet.inset - s_chk[0] - 106]]))
        s_txt = free_spot(sheet, keep, 76, 3.4 * len(lines) + 2, margin=3.0, prefer="bottom", u_range=ur)
        if s_txt is None:
            raise RuntimeError(f"{L['layout_id']} {variant}: no free space for the instructions")
        draw_check(s_chk[0] * mm, s_chk[1] * mm)
        draw_lines(s_txt[0] * mm, (s_txt[1] + 1) * mm, lines)
        spot2 = {"check": s_chk, "text": s_txt}
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(W * mm / 2, H * mm - 7 * mm, "BACK WALL  ^  (caps this way)")

    return {"label_spot_mm": spot, "info_spot_mm": spot2}


def main():
    meta_path = ROOT / "config" / "layouts.json"
    data = json.loads(meta_path.read_text())
    meta = {"sha": hashlib.sha256(meta_path.read_bytes()).hexdigest()}
    mat = data["mat_env"]
    local = vial_local_points()
    out = ROOT / "stencils"
    out.mkdir(exist_ok=True)
    report = {"layouts_sha256": meta["sha"], "grow_mm": GROW_MM, "pages": []}
    variants = {"letter": (landscape(letter), Sheet(landscape(letter), u0=96.0, v_right_inset=4.5)),
                "tabloid": (TABLOID, Sheet(TABLOID, u0=-8.0, v_right_inset=4.5))}
    for variant, (page, sheet) in variants.items():
        both = canvas.Canvas(str(out / f"stencils_{variant}_both_sets.pdf"), pagesize=page)
        for set_name in ("A", "B"):
            cset = canvas.Canvas(str(out / f"stencils_{variant}_set{set_name}.pdf"), pagesize=page)
            for L in data["layouts"]:
                for cv_ in (cset, both):
                    info = draw_layout(cv_, L, mat, local, sheet, set_name, variant, meta)
                    cv_.showPage()
                # fit check: window extent vs the printable sheet (between trim line and page edges)
                ext = []
                for v in VIALS:
                    win = grow(vial_outline_uv(L["vials"][v], mat, local), GROW_MM)
                    ext.append((win[:, 0].min(), win[:, 0].max(), win[:, 1].min(), win[:, 1].max()))
                umin, umax = min(e[0] for e in ext), max(e[1] for e in ext)
                vmin, vmax = min(e[2] for e in ext), max(e[3] for e in ext)
                if set_name == "A":
                    report["pages"].append({"variant": variant, "layout": L["layout_id"], "u_mm": [round(float(umin), 1), round(float(umax), 1)],
                                            "v_mm": [round(float(vmin), 1), round(float(vmax), 1)],
                                            "v_room_mm": round(sheet.W - sheet.inset, 1),
                                            "clipped_left_mm": round(float(max(0.0, vmax - (sheet.W - sheet.inset))), 1),
                                            "top_margin_mm": round(float(sheet.u0 + sheet.H - umax), 1), **info})
            cset.save()
        both.save()
    (out / "stencils_report.json").write_text(json.dumps(report, indent=1, default=str))
    for p in report["pages"]:
        print(f"{p['variant']:8s} {p['layout']}: u {p['u_mm']} v {p['v_mm']} (room {p['v_room_mm']}), "
              f"clipped {p['clipped_left_mm']} mm, top margin {p['top_margin_mm']} mm, label {p['label_spot_mm']}")


if __name__ == "__main__":
    sys.exit(main())
