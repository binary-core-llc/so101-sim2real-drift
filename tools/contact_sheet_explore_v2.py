#!/usr/bin/env python3
"""explore-v2 contact sheet: first front-camera frame after the 10 warm-up steps (seed 0, probe frames), labelled,
with the framing check over seeds 0-39 (tools/framing_check.py).

    .venv/bin/python -I tools/contact_sheet_explore_v2.py [out.png]
Top: sim nominal and R0 (course text, config/r0_pose.json), with R0's absolute lens pose read back from the stage.
Bottom: the tilt series 12 (explore-v1), 13, 14 (explore-v2), 15 deg (explore-v1).
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

GTC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from contact_sheet_explore_v1 import BOLD, COLS, FONT, GAP, H, HEAD, LAB, W, framing, measured  # noqa: E402
from r0_pose import axis_info, q2r  # noqa: E402

V1, V2 = GTC / "results" / "explore_v1", GTC / "results" / "explore_v2"
M1, M2 = GTC / "media" / "explore_v1", GTC / "media" / "explore_v2"


def probe_rows(path):
    return {r["set"]: r for r in (json.loads(l) for l in open(path)) if r["seed"] == 0}


def main(dst):
    p1, p2 = probe_rows(V1 / "probe_explore_v1.jsonl"), probe_rows(V2 / "probe_explore_v2.jsonl")
    seeds_in = {**json.loads((V1 / "framing_explore_v1.json").read_text())["summary"],
                **json.loads((V2 / "framing_explore_v2.json").read_text())["summary"]}
    r0 = json.loads((GTC / "config" / "r0_pose.json").read_text())
    ce = p2["Y_R0_course_text"]["readback"]["camera_external"]
    down, head = axis_info(q2r(ce["quat_wxyz"]))
    r0_line = (f"lens ({ce['pos'][0]:.4f}, {ce['pos'][1]:.4f}, {ce['pos'][2]:.4f}) m, axis {down:.2f}° down, heading {head:.2f}° "
               f"(target {r0['target_axis_deg_below_horizontal']:.0f}°, {r0['target_heading_deg']:.2f}°)")
    nom2 = p2["nominal"]["readback"]
    tiles_a = [("nominal", "sim nominal (every randomization at its center)", measured(nom2, nom2), M2 / "probe_explore_v2" / "nominal_seed000", None),
               ("Y_R0_course_text", "R0, course text: 40.0 cm high, 27.0 cm from plate rear, 45.0° down, aimed at mat centre",
                measured(p2["Y_R0_course_text"]["readback"], nom2), M2 / "probe_explore_v2" / "Y_R0_course_text_seed000", r0_line)]
    tiles_b = [("X_tilt_down_12", "camera tilt down 12° (explore-v1)", measured(p1["X_tilt_down_12"]["readback"], p1["nominal"]["readback"]),
                M1 / "probe_explore_v1" / "X_tilt_down_12_seed000", None),
               ("Y_tilt_down_13", "camera tilt down 13°", measured(p2["Y_tilt_down_13"]["readback"], nom2), M2 / "probe_explore_v2" / "Y_tilt_down_13_seed000", None),
               ("Y_tilt_down_14", "camera tilt down 14°", measured(p2["Y_tilt_down_14"]["readback"], nom2), M2 / "probe_explore_v2" / "Y_tilt_down_14_seed000", None),
               ("X_tilt_down_15", "camera tilt down 15° (explore-v1)", measured(p1["X_tilt_down_15"]["readback"], p1["nominal"]["readback"]),
                M1 / "probe_explore_v1" / "X_tilt_down_15_seed000", None)]
    lab = LAB + 20
    sw = COLS * W + (COLS + 1) * GAP
    sh = 2 * HEAD + 2 * (H + lab + GAP) + GAP + 40
    sheet = Image.new("RGB", (sw, sh), (250, 250, 250))
    dr = ImageDraw.Draw(sheet)
    f_head, f_bold, f_txt = ImageFont.truetype(BOLD, 26), ImageFont.truetype(BOLD, 20), ImageFont.truetype(FONT, 16)
    y = 0
    for title, tiles in (("explore-v2 (added after sweep v1 and explore-v1, not part of prereg-v1): R0 in simulation - seed 0", tiles_a),
                         ("Tilt series 12-15° (12 and 15 from explore-v1) - seed 0", tiles_b)):
        dr.text((GAP, y + 14), title, font=f_head, fill=(20, 20, 20))
        y += HEAD
        for i, (cid, what, meas, stem, extra) in enumerate(tiles):
            cx, cy = GAP + (i % COLS) * (W + GAP), y
            sheet.paste(Image.open(f"{stem}_front.png").convert("RGB"), (cx, cy))
            bad = framing(stem)
            dr.text((cx + 4, cy + H + 4), cid, font=f_bold, fill=(20, 20, 20))
            dr.text((cx + 4, cy + H + 30), what[:80], font=f_txt, fill=(40, 40, 40))
            dr.text((cx + 4, cy + H + 50), meas[0], font=f_txt, fill=(40, 40, 40))
            dr.text((cx + 4, cy + H + 70), meas[1] + "  |  seed 0: " + (("NOT fully in frame: " + ", ".join(bad)) if bad else "rack + 3 vials in frame"),
                    font=f_txt, fill=(190, 0, 0) if bad else (0, 120, 0))
            s = seeds_in.get(cid)
            if s:
                parts = [f"{o.replace('_left', '')} {s[o]['cut']} cut/{s[o]['out']} out" for o in ("rack_left", "vial_1", "vial_2", "vial_3")
                         if s[o]["cut"] or s[o]["out"]]
                dr.text((cx + 4, cy + H + 90), f"seeds 0-{s['seeds'] - 1}: fully in frame {s['all_in']}/{s['seeds']}"
                        + (" (" + ", ".join(parts) + ")" if parts else ""), font=f_txt, fill=(190, 0, 0) if s["all_in"] < s["seeds"] else (0, 120, 0))
            if extra:
                dr.text((cx + 4, cy + H + 110), extra, font=f_txt, fill=(40, 40, 40))
        y += H + lab + GAP
    dr.text((GAP, y + 8), "Frames: first front-camera (D455 slot) frame after reset + 10 warm-up steps, probe (no policy). Measured values: "
            "stage readback vs nominal (axis below horizontal, heading, image roll, camera height; rack origin, m).", font=f_txt, fill=(60, 60, 60))
    sheet.save(dst)
    print(f"wrote {dst} ({sw}x{sh})")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else str(V2 / "contact_sheet_explore_v2.png"))
