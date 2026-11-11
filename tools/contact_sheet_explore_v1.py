#!/usr/bin/env python3
"""explore-v1 contact sheet: the first front-camera frame after the 10 warm-up steps (seed 0), labelled.

    .venv/bin/python -I tools/contact_sheet_explore_v1.py [out.png]
Top: sweep v1 nominal and the largest level of S1, S2, S3, S7, S8 (episode 0 of each cell, media/sim/).
Bottom: the 8 explore-v1 cells (probe frames, same reset + warm-up as a run, no policy; media/explore_v1/).
Each label: cell, what the code changes, the measured change against nominal (camera axis tilt, heading pan,
image roll, height; rack position) read back from the stage, and which objects are not fully in frame at seed 0.
"""
import csv
import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

GTC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from framing_check import masks  # noqa: E402

SWEEP = ["S0_nominal", "S1_tilt_down_8p6", "S2_rack_y_4p0", "S3_rack_x_8p0", "S7_cam_yaw_8p6", "S8_cam_up_3p0"]
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
W, H, LAB, GAP, COLS, HEAD = 640, 480, 116, 12, 4, 56


def image_roll_deg(q0, q):
    """Twist of q relative to q0 about the camera's optical axis (local Z), as image-content roll, CCW +.
    The camera turning +phi about its +Z (pointing back out of the lens) turns the scene -phi in the image."""
    w0, x0, y0, z0 = q0
    w1, x1, y1, z1 = q
    w = w0 * w1 + x0 * x1 + y0 * y1 + z0 * z1          # conj(q0) * q, in the camera frame
    z = w0 * z1 - x0 * y1 + y0 * x1 - z0 * w1
    return -math.degrees(2 * math.atan2(z, w))


def measured(rb, nom):
    c, c0 = rb["camera_external"], nom["camera_external"]
    d = {"tilt": c["axis_deg_below_horizontal"] - c0["axis_deg_below_horizontal"],
         "pan": c["axis_heading_deg"] - c0["axis_heading_deg"],
         "roll": image_roll_deg(c0["quat_wxyz"], c["quat_wxyz"]),
         "dz": 100 * (c["pos"][2] - c0["pos"][2])}
    r = rb["rack"]["pos"]
    return (f"camera: tilt {d['tilt']:+.2f}°  pan {d['pan']:+.2f}°  image roll {d['roll']:+.2f}°  dz {d['dz']:+.2f} cm",
            f"rack origin ({r[0]:.3f}, {r[1]:.3f}) m")


def framing(stem):
    m = masks(stem)
    bad = []
    for o, mk in m.items():
        if not mk.any():
            bad.append(f"{o} out/hidden")
        elif mk[0].any() or mk[-1].any() or mk[:, 0].any() or mk[:, -1].any():
            bad.append(f"{o} cut")
    return bad


def main(dst):
    seeds_in = {}  # per-seed framing from tools/framing_check.py over seeds 0-39, when present
    for fr in ("framing_sweep_v1_top.json", "framing_explore_v1.json"):
        if (GTC / "results" / "explore_v1" / fr).exists():
            seeds_in.update(json.loads((GTC / "results" / "explore_v1" / fr).read_text())["summary"])
    cells = {r["cell_id"]: r for r in csv.DictReader(open(GTC / "config" / "cells_sweep_v1.csv"))}
    xcells = list(csv.DictReader(open(GTC / "config" / "explore_v1_cells.csv")))
    first = {c: next(json.loads(l) for l in open(GTC / "results" / "sim" / f"{c}.jsonl") if json.loads(l)["episode"] == 0)
             for c in SWEEP}
    probe = {json.loads(l)["set"]: json.loads(l) for l in open(GTC / "results" / "explore_v1" / "probe_explore_v1.jsonl")}
    tiles_a = [(c, cells[c]["notes"].split(":", 1)[-1].strip(), measured(first[c]["readback"], first["S0_nominal"]["readback"]),
                GTC / "media" / "sim" / c / "ep0000_step0") for c in SWEEP]
    tiles_b = [(x["cell_id"], x["notes"].split("prereg-v1.", 1)[-1].strip(),
                measured(probe[x["cell_id"]]["readback"], probe["nominal"]["readback"]),
                GTC / "media" / "explore_v1" / "probe_explore_v1" / f"{x['cell_id']}_seed000") for x in xcells]
    rows_a, rows_b = math.ceil(len(tiles_a) / COLS), math.ceil(len(tiles_b) / COLS)
    sw = COLS * W + (COLS + 1) * GAP
    sh = 2 * HEAD + (rows_a + rows_b) * (H + LAB + GAP) + GAP + 40
    sheet = Image.new("RGB", (sw, sh), (250, 250, 250))
    dr = ImageDraw.Draw(sheet)
    f_head, f_bold, f_txt = ImageFont.truetype(BOLD, 26), ImageFont.truetype(BOLD, 20), ImageFont.truetype(FONT, 16)
    y = 0
    for title, tiles in (("Sweep v1 (prereg-v1): nominal and the largest level of S1, S2, S3, S7, S8 - episode 0, seed 0", tiles_a),
                         ("explore-v1 (added after seeing sweep v1, not part of prereg-v1) - seed 0, probe frame", tiles_b)):
        dr.text((GAP, y + 14), title, font=f_head, fill=(20, 20, 20))
        y += HEAD
        for i, (cid, what, meas, stem) in enumerate(tiles):
            cx, cy = GAP + (i % COLS) * (W + GAP), y + (i // COLS) * (H + LAB + GAP)
            sheet.paste(Image.open(f"{stem}_front.png").convert("RGB"), (cx, cy))
            bad = framing(stem)
            dr.text((cx + 4, cy + H + 4), cid, font=f_bold, fill=(20, 20, 20))
            dr.text((cx + 4, cy + H + 30), what[:78], font=f_txt, fill=(40, 40, 40))
            dr.text((cx + 4, cy + H + 50), meas[0], font=f_txt, fill=(40, 40, 40))
            dr.text((cx + 4, cy + H + 70), meas[1] + "  |  seed 0: " + (("NOT fully in frame: " + ", ".join(bad)) if bad else "rack + 3 vials in frame"),
                    font=f_txt, fill=(190, 0, 0) if bad else (0, 120, 0))
            if cid in seeds_in:
                k, n = seeds_in[cid]["all_in"], seeds_in[cid]["seeds"]
                dr.text((cx + 4, cy + H + 90), f"seeds 0-{n - 1}: rack + 3 vials fully in frame in {k}/{n}",
                        font=f_txt, fill=(190, 0, 0) if k < n else (0, 120, 0))
        y += math.ceil(len(tiles) / COLS) * (H + LAB + GAP)
    dr.text((GAP, y + 8), "Frames: first front-camera (D455 slot) frame after reset + 10 warm-up steps. Measured values: stage readback "
            "vs nominal (axis below horizontal, heading, image roll, camera height; rack origin, m).", font=f_txt, fill=(60, 60, 60))
    sheet.save(dst)
    print(f"wrote {dst} ({sw}x{sh})")
    for cid, what, meas, stem in tiles_a + tiles_b:
        print(f"  {cid:24s} {meas[0]} | {meas[1]} | {', '.join(framing(stem)) or 'all in frame'}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else str(GTC / "results" / "explore_v1" / "contact_sheet_explore_v1.png"))
