#!/usr/bin/env python3
"""Rebuild the README figures from files committed in this repository.

    python3 -I docs/figures/make_figures.py          # any Python 3 with Pillow; run from anywhere

Writes docs/figures/pose_offset.png (the README's hero image), docs/figures/results_chain.svg and docs/figures/sled.svg,
and prints the README captions.
No number is typed here. Success counts and intervals come from poster/numbers.json (sim.S0_nominal, real.R1, real.R2,
real.R4, real.R0, s1.offset_total_mm, s1.offset_total_deg) and results/h4/h4_result.json and s1_result.json; the
condition wording of R2 and R4 and the sled dimensions come from README.md (the result sentence and the camera check
kit's step 2); the board grid and the page size come from docs/charuco_board.json and the board PDF. The pose-offset
panel combines two simulation frames copied into docs/figures/ (see PROVENANCE.md); its offset comes from
poster/numbers.json (s1.offset_total_mm, s1.offset_total_deg) and its rates from results/h4/s1_result.json. Charts and
drawings are SVG written with the standard library; Pillow only combines the two simulation frames of the pose-offset
image.
"""
import json
import re
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "docs" / "figures"
SIM_C, REAL_C, INK, GREY, LIGHT = "#2f6db5", "#d0611c", "#1f2328", "#6e7781", "#d0d7de"
FONT = "DejaVu Sans, Helvetica, Arial, sans-serif"


def load(rel):
    return json.loads((REPO / rel).read_text())


def one(pattern, text, what):
    m = re.findall(pattern, text)
    assert len(m) == 1, f"{what}: {len(m)} matches for {pattern!r}"
    return m[0]


def pct(r):
    return f"{100 * r:.1f}".rstrip("0").rstrip(".") + " %"


NUM = load("poster/numbers.json")
H4 = load("results/h4/h4_result.json")
S1 = load("results/h4/s1_result.json")
README = (REPO / "README.md").read_text()


# ---------------------------------------------------------------- 1. hero, the pose offset alone: H4 and S1, same seed and step
def pose_offset():
    left = Image.open(OUT / "h4_c920_measured_ep0000_step0_front.png").convert("RGB")
    right = Image.open(OUT / "s1_measured_c920_ep0000_step0_front.png").convert("RGB")
    assert left.size == right.size
    w, h = left.size
    gap, bar = 12, 40
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 19)
    except OSError:
        font = ImageFont.load_default()
    img = Image.new("RGB", (2 * w + gap, h + bar), "white")
    d = ImageDraw.Draw(img)
    for x, im, label in ((0, left, "H4_c920_measured: simulated camera pose"),
                         (w + gap, right, "S1_measured_c920: real camera's measured pose")):
        img.paste(im, (x, bar))
        d.text((x + 6, 10), label, fill=INK, font=font)
    img.save(OUT / "pose_offset.png", optimize=True)
    s1, h4 = S1["S1_measured_c920"], S1["vs_H4_c920_measured"]
    ep = {int(one(r"_ep(\d+)_step", f, "episode")) for f in ("h4_c920_measured_ep0000_step0_front.png",
                                                                "s1_measured_c920_ep0000_step0_front.png")}
    assert len(ep) == 1
    ep = ep.pop()
    seeds = {next(json.loads(l)["seed"] for l in open(REPO / f"results/sim/{c}.jsonl") if json.loads(l)["episode"] == ep)
             for c in ("H4_c920_measured", "S1_measured_c920")}
    assert len(seeds) == 1                                             # same seed in both cells
    mm, deg = NUM["s1.offset_total_mm"]["value"], NUM["s1.offset_total_deg"]["value"]
    assert h4["n"] == s1["n"]
    return (f"Same simulated scene and lens, two camera positions {mm} mm and {deg}° apart: the simulated camera pose "
            f"(left) and the real camera's measured pose (right). Over {s1['n']} episodes each, the policy succeeded "
            f"{h4['k']}/{h4['n']} ({pct(h4['k'] / h4['n'])}) from the left pose and {s1['k']}/{s1['n']} "
            f"({pct(s1['k'] / s1['n'])}) from the right (cells H4_c920_measured and S1_measured_c920; simulation, "
            f"seed {seeds.pop()}, first frame).")


# ---------------------------------------------------------------- 2. results chain: rates with Wilson 95 % intervals
def results_chain():
    r2_shift = one(r"with the rack moved (\d+(?:\.\d+)? cm)", README, "R2 wording")
    r4_tilt = one(r"with the camera tilted (\d+(?:\.\d+)?°) further down", README, "R4 wording")
    s0, h4, s1 = NUM["sim.S0_nominal"], H4["c920_measured"], S1["S1_measured_c920"]
    assert (H4["sim_intrinsics"]["k"], H4["sim_intrinsics"]["n"]) == (s0["k"], s0["n"])
    off_mm, off_deg = NUM["s1.offset_total_mm"]["value"], NUM["s1.offset_total_deg"]["value"]
    rows = [
        ("sim", "S0_nominal", f"simulated camera (fx {H4['sim_intrinsics']['fx_px']} px)", s0["k"], s0["n"], s0["ci"]),
        ("sim", "H4_c920_measured", f"C920 focal length (fx {h4['fx_px']} px), simulated pose", h4["k"], h4["n"], h4["wilson95"]),
        ("sim", "S1_measured_c920", f"C920 at the real camera's measured pose ({off_mm} mm, {off_deg}° away)",
         s1["k"], s1["n"], s1["wilson95"]),
        ("real", "R1", "camera at the measured nominal pose", NUM["real.R1"]["k"], NUM["real.R1"]["n"], NUM["real.R1"]["ci"]),
        ("real", "R2", f"rack moved {r2_shift}", NUM["real.R2"]["k"], NUM["real.R2"]["n"], NUM["real.R2"]["ci"]),
        ("real", "R4", f"camera tilted {r4_tilt} further down", NUM["real.R4"]["k"], NUM["real.R4"]["n"], NUM["real.R4"]["ci"]),
        ("real", "R0", "camera placed by the course's written measurements", NUM["real.R0"]["k"], NUM["real.R0"]["n"],
         NUM["real.R0"]["ci"]),
    ]
    sim_n = {r[4] for r in rows if r[0] == "sim"}
    assert len(sim_n) == 1
    sim_n = sim_n.pop()
    W, LX, PX0, PW, RH = 1000, 20, 470, 400, 46
    head = {"sim": f"Simulation (Isaac Lab), {sim_n} episodes per cell", "real": "Real robot, blind-scored trials"}
    o, y = [], 70
    X = lambda v: PX0 + v * PW
    o.append(f'<text x="{LX}" y="30" font-size="20" font-weight="bold" fill="{INK}">Success rate, with Wilson 95 % intervals</text>')
    for grp in ("sim", "real"):
        col = SIM_C if grp == "sim" else REAL_C
        o.append(f'<rect x="{LX}" y="{y - 16}" width="12" height="12" fill="{col}"/>')
        o.append(f'<text x="{LX + 20}" y="{y - 5}" font-size="15" font-weight="bold" fill="{col}">{escape(head[grp])}</text>')
        y += 14
        for g, cell, label, k, n, ci in (r for r in rows if r[0] == grp):
            cy = y + RH / 2
            o.append(f'<text x="{LX}" y="{cy - 3}" font-size="14" font-weight="bold" fill="{INK}">{escape(cell)}</text>')
            o.append(f'<text x="{LX}" y="{cy + 14}" font-size="12.5" fill="{GREY}">{escape(label)}</text>')
            o.append(f'<line x1="{X(ci[0]):.1f}" y1="{cy}" x2="{X(ci[1]):.1f}" y2="{cy}" stroke="{col}" stroke-width="3"/>')
            for v in ci:
                o.append(f'<line x1="{X(v):.1f}" y1="{cy - 7}" x2="{X(v):.1f}" y2="{cy + 7}" stroke="{col}" stroke-width="2"/>')
            o.append(f'<circle cx="{X(k / n):.1f}" cy="{cy}" r="6.5" fill="{col}" stroke="white" stroke-width="1.5"/>')
            o.append(f'<text x="{PX0 + PW + 16}" y="{cy + 5}" font-size="14" fill="{INK}">{k}/{n} ({pct(k / n)})</text>')
            y += RH
        y += 34
    top, bot = 64, y - 30
    grid = []
    for t in range(0, 101, 20):
        grid.append(f'<line x1="{X(t / 100):.1f}" y1="{top}" x2="{X(t / 100):.1f}" y2="{bot}" stroke="{LIGHT}" stroke-width="1"/>')
        grid.append(f'<text x="{X(t / 100):.1f}" y="{bot + 18}" font-size="12" fill="{GREY}" text-anchor="middle">{t} %</text>')
    H = bot + 34
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{FONT}">'
           f'<rect width="{W}" height="{H}" fill="white"/>' + "".join(grid + o) + "</svg>\n")
    (OUT / "results_chain.svg").write_text(svg)
    real = [r for r in rows if r[0] == "real"]
    real_n = sorted(r[4] for r in real)
    assert max(r[5][0] for r in real) < min(r[5][1] for r in real)    # every real-robot interval overlaps every other
    return (f"Success rate with Wilson 95 % intervals: the simulation cells (blue, {sim_n} episodes each) and the "
            f"blind-scored real-robot conditions (orange). With {real_n[0]} to {real_n[-1]} trials per real condition, "
            "the real-robot intervals are wide and overlap.")


# ---------------------------------------------------------------- 3. the ChArUco sled, top view, from README step 2
def sled():
    step2 = one(r"\*\*2\. The sled\.\*\*(.*?)\*\*3\. Calibrate", README.replace("\n", " "), "step 2")
    f = lambda pat, what: float(one(pat, step2, what))
    material = one(r"from one piece of (\d+/\d+ in foam board)", step2, "material")
    tongue_w = f(r"a tongue (\d+(?:\.\d+)?) mm wide", "tongue width")
    tongue_l = f(r"(\d+(?:\.\d+)?) mm from its end face to the carrier", "tongue length")
    car_l, car_w = map(float, one(r"a carrier (\d+(?:\.\d+)?) x (\d+(?:\.\d+)?) mm", step2, "carrier"))
    key_l = f(r"a key (\d+(?:\.\d+)?) mm long", "key length")
    key_w = f(r"design width is (\d+(?:\.\d+)?) mm", "key design width")
    key_cut = f(r"cut it (\d+(?:\.\d+)?) mm wide", "key cut width")
    left_edge = f(r"left edge (\d+(?:\.\d+)?) mm from the end face", "print left edge")
    title_edge = f(r"title edge (\d+(?:\.\d+)?) mm from the centre line", "print title edge")
    dx_d = f(r"grid column line 0 at (\d+(?:\.\d+)?) mm", "grid column line 0")
    dy_d = f(r"row line 0 at (\d+(?:\.\d+)?) mm", "grid row line 0")
    for field, v in (("d_x_mm", dx_d), ("d_y_mm", dy_d)):              # the README table's design column agrees
        assert float(one(rf"\| `{field}` \|[^|]*\|([^|]*)\|", step2, field)) == v
    board = load("docs/charuco_board.json")
    sq = board["square_m"] * 1000
    gx, gy = board["cols"] * sq, board["rows"] * sq                     # long side along the box depth (x)
    mb = re.search(rb"/MediaBox \[ *0 +0 +([\d.]+) +([\d.]+) *\]", (REPO / "docs/ChArUco_GTC_SO101_letter.pdf").read_bytes())
    page_l, page_w = (float(v) * 25.4 / 72 for v in mb.groups())       # landscape letter page, mm

    S, OX, OY = 2.0, 250, 330                                          # px per mm; origin = end face on the centre line
    X = lambda x: OX + x * S
    Y = lambda y: OY - y * S                                           # +y (toward the camera wall) is up
    o = []

    def rect(x0, y0, x1, y1, **kw):
        a = " ".join(f'{k.replace("_", "-")}="{v}"' for k, v in kw.items())
        o.append(f'<rect x="{X(x0):.1f}" y="{Y(y1):.1f}" width="{(x1 - x0) * S:.1f}" height="{(y1 - y0) * S:.1f}" {a}/>')

    def text(x, y, s, size=12.5, anchor="start", col=INK, bold=False):
        o.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{col}" text-anchor="{anchor}"'
                 f'{" font-weight=\"bold\"" if bold else ""}>{escape(s)}</text>')

    def line(x1, y1, x2, y2, col=INK, w=1.0, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        o.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{col}" stroke-width="{w}"{d}/>')

    def head(x, y, dx, dy, col):                                       # filled arrowhead at (x, y) pointing along (dx, dy)
        n = (dx * dx + dy * dy) ** 0.5
        ux, uy = dx / n, dy / n
        pts = [(x, y), (x - 7 * ux + 3 * uy, y - 7 * uy - 3 * ux), (x - 7 * ux - 3 * uy, y - 7 * uy + 3 * ux)]
        o.append(f'<polygon points="{" ".join(f"{a:.1f},{b:.1f}" for a, b in pts)}" fill="{col}"/>')

    def hdim(x0, x1, y, label, col=INK, outside=False):                # horizontal dimension at pixel row y
        line(X(x0), y, X(x1), y, col)
        for x in (x0, x1):
            line(X(x), y - 6, X(x), y + 6, col, 0.8)
        if outside:                                                    # too short for inward arrows
            head(X(x0), y, 1, 0, col); head(X(x1), y, -1, 0, col)
            text(X(x0) - 8, y + 4, label, 12, "end", col)
        else:
            head(X(x0), y, -1, 0, col); head(X(x1), y, 1, 0, col)
            text((X(x0) + X(x1)) / 2, y - 6, label, 12, "middle", col)

    def vdim(y0, y1, x, label, col=INK):                               # vertical dimension at pixel column x, label on top
        line(x, Y(y0), x, Y(y1), col)
        for v in (y0, y1):
            line(x - 6, Y(v), x + 6, Y(v), col, 0.8)
        head(x, Y(y0), 0, 1, col); head(x, Y(y1), 0, -1, col)
        text(x, Y(max(y0, y1)) - 10, label, 12, "middle", col)

    hw, cw = tongue_w / 2, car_w / 2
    rect(0, -hw, tongue_l, hw, fill="#f3ead7", stroke=INK, stroke_width=1.2)                     # tongue
    rect(tongue_l, -cw, tongue_l + car_l, cw, fill="#f3ead7", stroke=INK, stroke_width=1.2)      # carrier
    rect(-key_l, -key_w / 2, 0, key_w / 2, fill="#c9b48a", stroke=INK, stroke_width=1.2)         # key
    rect(left_edge, title_edge - page_w, left_edge + page_l, title_edge, fill="white", stroke=GREY,
         stroke_width=1, stroke_dasharray="5 3")                                                   # print
    for i in range(board["cols"]):                                                                 # grid squares
        for j in range(board["rows"]):
            if (i + j) % 2 == 0:
                rect(dx_d + i * sq, dy_d - (j + 1) * sq, dx_d + (i + 1) * sq, dy_d - j * sq, fill="#bfc5cc")
    rect(dx_d, dy_d - gy, dx_d + gx, dy_d, fill="none", stroke=GREY, stroke_width=1)
    line(X(-key_l - 12), Y(0), X(tongue_l + car_l + 12), Y(0), GREY, 0.8, "8 3 2 3")             # centre line
    line(X(dx_d), Y(cw + 6), X(dx_d), Y(-cw) + 24, SIM_C, 1.2)                                     # grid column line 0
    line(X(dx_d) - 12, Y(dy_d), X(tongue_l + car_l) + 24, Y(dy_d), SIM_C, 1.2)                     # grid row line 0
    o.append(f'<circle cx="{X(dx_d):.1f}" cy="{Y(dy_d):.1f}" r="4" fill="{SIM_C}"/>')

    # dimensions along the box depth (below), across (right and left)
    base = Y(-cw) + 34
    hdim(-key_l, 0, base, f"key {key_l:g}", outside=True)
    hdim(0, tongue_l, base + 28, f"tongue {tongue_l:g}")
    hdim(0, left_edge, base + 56, f"print edge {left_edge:g}")
    hdim(0, dx_d, base + 84, f"grid column line 0: {dx_d:g} (d_x)", SIM_C)
    hdim(tongue_l, tongue_l + car_l, base + 112, f"carrier {car_l:g}")
    rx = X(tongue_l + car_l) + 50
    vdim(-cw, cw, rx, f"carrier {car_w:g}")
    vdim(0, title_edge, rx + 105, f"print edge {title_edge:g}")
    vdim(0, dy_d, rx + 210, f"row line 0: {dy_d:g} (d_y)", SIM_C)
    vdim(-hw, hw, X(-key_l) - 40, f"tongue {tongue_w:g}")
    vdim(-key_w / 2, key_w / 2, X(-key_l) - 120, f"key {key_w:g}")

    # labels
    text(X(tongue_l / 2), Y(0) - 10, "tongue", 13, "middle", bold=True)
    text(X(tongue_l / 2), Y(0) + 18, "centre line", 11, "middle", GREY)
    text(X(tongue_l + car_l) - 8, Y(-cw) - 8, f"carrier ({material})", 13, "end", bold=True)
    text(X(dx_d) + 8, Y(dy_d) - 8, "grid origin", 12.5, "start", SIM_C, bold=True)
    text(X(-key_l) - 120, 54, "End face: touches both front lobes of the robot base. Key: sits in the gap between them "
         f"(cut {key_cut:g} wide, then trimmed to fit).", 12.5, col=GREY)
    text(X(-key_l) - 120, 72, f"Grey squares: the ChArUco grid, {board['cols']} x {board['rows']} squares of {sq:g}. "
         "Dashed: the print (whole letter page). Blue: the grid origin lines, d_x and d_y.", 12.5, col=GREY)
    ax = rx + 300
    line(ax, Y(cw) + 50, ax, Y(cw) + 4, GREY, 1.4); head(ax, Y(cw), 0, -1, GREY)
    text(ax, Y(cw) - 8, "camera wall", 12, "middle", GREY)
    text(X(-key_l) - 120, 30, "ChArUco sled, top view (mm; design values from the camera check kit, step 2)", 18, bold=True)

    W, H = int(ax + 60), int(base + 112 + 30)                          # below the lowest dimension line
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{FONT}">'
           f'<rect width="{W}" height="{H}" fill="white"/>' + "".join(o) + "</svg>\n")
    (OUT / "sled.svg").write_text(svg)
    return "Top view of the ChArUco sled with the design dimensions of step 2 (mm); the table gives this study's measured offsets."


if __name__ == "__main__":
    caps = {"pose_offset.png": pose_offset(), "results_chain.svg": results_chain(), "sled.svg": sled()}
    for name, cap in caps.items():
        print(f"{name}: {cap}")
