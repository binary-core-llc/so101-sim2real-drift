#!/usr/bin/env python3
"""T05 + T06 (V07): readback pass/fail and the axis/sign table, from a probe run.

    .venv/bin/python -I sim/sign_table.py results/sim/t06_probe.jsonl media/sim/t06_probe

For every probe set (one code-level perturbation, seed 0) it reports what physically moved,
measured on the live stage (camera prim world pose, rack pose) and in the rendered front image
(rack mask centroid and area, floor brightness), relative to the nominal set. Walls in env frame:
back wall +x (Back panel x 0.402), camera wall +y ("Left" panel y 0.381), right wall -y, open front -x.
Writes config/sign_table.json and notes/sign_table_V07.md.
"""
import ast
import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def rows(path):
    return {r["set"]: r for r in map(json.loads, open(path)) if r.get("mode") == "probe"}


def qmat(q):
    w, x, y, z = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
                     [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
                     [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)]])


def cam_frame(r):
    c = r["readback"]["camera_external"]
    R = qmat(c["quat_wxyz"])          # USD camera: columns = local x (image right), y (image up), z (backwards)
    return np.array(c["pos"]), R


def image_roll_deg(R0, R1):
    """Rotation of the image about the optical axis between two camera frames (+ = image turns CCW)."""
    fwd = -R1[:, 2]
    up0 = R0[:, 1] - fwd * (R0[:, 1] @ fwd)
    up0 /= np.linalg.norm(up0)
    ang = math.atan2(np.cross(up0, R1[:, 1]) @ fwd, up0 @ R1[:, 1])
    return math.degrees(ang)


def mask_of(media, name, needle):
    lab = json.loads((media / f"{name}_seed000_front_instance_labels.json").read_text())
    seg = cv2.cvtColor(cv2.imread(str(media / f"{name}_seed000_front_instance_rgba.png"), cv2.IMREAD_UNCHANGED),
                       cv2.COLOR_BGRA2RGBA)
    m = np.zeros(seg.shape[:2], bool)
    for k, v in lab.items():
        if needle in v:
            c = ast.literal_eval(k)
            m |= np.all(seg == np.array(c, np.uint8), axis=2)
    return m


def centroid(m):
    ys, xs = np.nonzero(m)
    return (float(xs.mean()), float(ys.mean()), int(m.sum())) if len(xs) else (None, None, 0)


def name_translation(d):
    ax = int(np.argmax(np.abs(d)))
    names = [("toward the back wall", "toward the open front"), ("toward the camera wall", "toward the right wall"),
             ("up", "down")]
    return names[ax][0 if d[ax] > 0 else 1], ax


def main(jsonl, media):
    R = rows(jsonl)
    media = Path(media)
    nom = R["nominal"]
    p0, R0 = cam_frame(nom)
    c0 = nom["readback"]["camera_external"]
    rack0 = centroid(mask_of(media, "nominal", "/Rack_Left/"))
    floor0 = cv2.imread(str(media / "nominal_seed000_front.png")).astype(float)
    table, t05 = [], []
    for name, r in R.items():
        rb = r["readback"]
        t05.append({"set": name, "pass": rb["pass"], "camera_mount_err_m": rb["camera_mount"]["err_m"],
                    "camera_mount_err_rad": rb["camera_mount"]["err_rad"], "rack_err_m": rb["rack"]["err_m"],
                    "rack_err_yaw_rad": rb["rack"]["err_yaw_rad"], "exposure": rb["exposure_ev"],
                    "ext_focal_mm": rb["camera_external"]["focal_mm"], "wrist_focal_mm": rb["wrist_focal_mm"],
                    "mat_yaw_rad": rb["mat_yaw_rad"], "vials_on_mat_z_ok": rb.get("vials_on_mat_z_ok")})
        if name.startswith("nominal"):
            continue
        p1, R1 = cam_frame(r)
        c1 = rb["camera_external"]
        rk = centroid(mask_of(media, name, "/Rack_Left/"))
        e = {"set": name, "code_overrides": r["overrides"],
             "camera_dpos_cm": [round(float(v) * 100, 2) for v in (p1 - p0)],
             "camera_pos_env": [round(float(v), 4) for v in p1],
             "camera_dtilt_down_deg": round(c1["axis_deg_below_horizontal"] - c0["axis_deg_below_horizontal"], 3),
             "camera_dpan_deg": round((c1["axis_heading_deg"] - c0["axis_heading_deg"] + 180) % 360 - 180, 3),
             "camera_image_roll_deg": round(image_roll_deg(R0, R1), 3),
             "hfov_deg": round(c1["hfov_deg"], 2),
             "rack_dpos_cm": [round((a - b) * 100, 2) for a, b in zip(rb["rack"]["pos"][:2], nom["readback"]["rack"]["pos"][:2])],
             "rack_dyaw_deg": round(math.degrees(rb["rack"]["yaw_rad"] - nom["readback"]["rack"]["yaw_rad"]), 3),
             "rack_mask_shift_px": None if rk[0] is None else [round(rk[0] - rack0[0], 1), round(rk[1] - rack0[1], 1)],
             "rack_mask_area_ratio": round(rk[2] / max(rack0[2], 1), 3)}
        # lightbox inner faces (env, from the C1 dump): x -0.102..0.402, |y| < 0.381, z 0.028..0.530
        x, y, z = p1
        e["camera_inside_box"] = bool(-0.102 < x < 0.402 and abs(y) < 0.379 and 0.028 < z < 0.530)
        img = cv2.imread(str(media / f"{name}_seed000_front.png")).astype(float)
        e["front_mean_brightness_ratio"] = round(float(img.mean() / floor0.mean()), 3)
        ov = r["overrides"]
        if "camera" in ov:
            (ax, val), = ov["camera"].items()
            if ax in ("x", "y", "z"):
                phys, wax = name_translation(np.array(e["camera_dpos_cm"]))
                e["physical"] = f"camera moves {phys} ({e['camera_dpos_cm'][wax]:+.1f} cm env {'xyz'[wax]})"
            else:
                parts = []
                if abs(e["camera_dtilt_down_deg"]) > 1:
                    parts.append(f"tilts {'down' if e['camera_dtilt_down_deg'] > 0 else 'up'} {abs(e['camera_dtilt_down_deg']):.2f} deg")
                if abs(e["camera_dpan_deg"]) > 1:
                    parts.append(f"pans {'left (CCW from above)' if e['camera_dpan_deg'] > 0 else 'right (CW from above)'} {abs(e['camera_dpan_deg']):.2f} deg")
                if abs(e["camera_image_roll_deg"]) > 1:
                    parts.append(f"image rolls {'CCW' if e['camera_image_roll_deg'] > 0 else 'CW'} {abs(e['camera_image_roll_deg']):.2f} deg")
                e["physical"] = "camera " + ", ".join(parts)
        elif "rack" in ov:
            (ax, val), = ov["rack"].items()
            if ax == "yaw":
                e["physical"] = f"rack turns {'CCW' if e['rack_dyaw_deg'] > 0 else 'CW'} (from above) {abs(e['rack_dyaw_deg']):.1f} deg about its corner origin"
            else:
                phys, wax = name_translation(np.array(e["rack_dpos_cm"] + [0.0]))
                e["physical"] = f"rack moves {phys} ({e['rack_dpos_cm'][wax]:+.1f} cm env {'xy'[wax]})"
        elif "exposure_ev" in ov:
            e["physical"] = f"box light {ov['exposure_ev']:+.0f} EV (centre -1): image brightness x{e['front_mean_brightness_ratio']}"
        elif "camera_focal_mm" in ov:
            e["physical"] = f"external camera HFOV {e['hfov_deg']} deg (nominal 63.74): rack area x{e['rack_mask_area_ratio']}"
        elif "wrist_focal_mm" in ov:
            e["physical"] = f"wrist focal {ov['wrist_focal_mm']} mm (centre 13.5)"
        elif "mat_yaw_rad" in ov:
            e["physical"] = f"mat yaw {math.degrees(ov['mat_yaw_rad']):+.1f} deg"
        if not e["camera_inside_box"]:
            e["physical"] = e.get("physical", "") + " -- LENS OUTSIDE THE BOX (behind a wall/ceiling): not a valid level"
        table.append(e)

    t05_pass = all(x["pass"] for x in t05)
    renom = R.get("nominal_again")
    repeat = None
    if renom:
        repeat = {"camera_pos_diff_m": float(np.abs(np.array(renom["readback"]["camera_external"]["pos"]) - p0).max()),
                  "vial_after_reset_diff_m": max(abs(a - b) for v in ("vial_1", "vial_2", "vial_3")
                                                 for a, b in zip(renom["objects_after_reset"][v]["pos"], nom["objects_after_reset"][v]["pos"]))}
    out = {"source": str(jsonl), "T05_readback_all_pass": t05_pass, "T05": t05, "nominal_repeat": repeat, "T06": table}
    (ROOT / "config" / "sign_table.json").write_text(json.dumps(out, indent=1))

    md = ["# V07 sign table (T06), from `" + str(jsonl) + "`", "",
          "Measured on the live stage (camera prim world pose, rack pose) and in the rendered front image, relative to nominal.",
          "Env frame: +x = toward the back wall, +y = toward the camera wall (the 'Left' panel), +z = up; open front at -x.",
          "Answers to V07: **tilt down = code pitch +**; **toward the camera wall = camera code x +**; **toward the back wall = camera code y -**; "
          "up = camera code z +. Rack: code x + = toward the back wall, code y + = toward the camera wall. "
          "Code yaw is not a pure pan (the mount z axis is tilted ~36 deg): +10 deg code yaw = 16.7 deg pan + ~1.5 deg tilt.",
          "Wall limits from the nominal lens position (0.138, 0.330, 0.489): camera wall +5.1 cm (inner face y 0.381), "
          "ceiling +4.1 cm (z 0.530); the 6 cm probes beyond them are invalid levels.", "",
          "| code override | physical result | camera Δpos (cm, env xyz) | Δtilt down (°) | Δpan (°) | image roll (°) | rack mask shift (px) |",
          "|---|---|---|---|---|---|---|"]
    for e in table:
        md.append(f"| `{json.dumps(e['code_overrides'])}` | {e.get('physical', '')} | {e['camera_dpos_cm']} | "
                  f"{e['camera_dtilt_down_deg']} | {e['camera_dpan_deg']} | {e['camera_image_roll_deg']} | {e['rack_mask_shift_px']} |")
    md += ["", f"T05 readback: {'ALL PASS' if t05_pass else 'FAILURES'} ({len(t05)} sets, tolerance 1e-4)."]
    if repeat:
        md.append(f"Nominal repeated at the end: camera pos diff {repeat['camera_pos_diff_m']:.2e} m, "
                  f"vial after-reset diff {repeat['vial_after_reset_diff_m']:.2e} m.")
    (ROOT / "notes" / "sign_table_V07.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
