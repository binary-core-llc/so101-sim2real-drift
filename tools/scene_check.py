#!/usr/bin/env python3
"""Where the mat and the rack are in E (the sim frame), from one front-camera view and a measured camera pose.

    .venv/bin/python -I tools/scene_check.py [--pose r0] [--mat-width-mm 457.2] [--no-rack] [--source camera:front]
Mat: the mat's three visible edges (robot side = front, back-wall side = back, far side toward the right wall) are
found along profiles across the sim edges projected with the pose (bright floor -> dark mat, sub-pixel), lifted to
the mat-top plane through the lens and fitted with lines. Reported per edge: offset from the sim edge at both ends
(mm; front/back in E x, far in E y) and the turn (deg). The camera-side edge is out of view: it is the far edge plus
--mat-width-mm (measure the real mat).
Rack: the yellow blob (the trial runner's HSV band, filled) against the rack's sim block (corner O (0.18, 0.08),
12 x 12 cm, --rack-h-cm high on the mat) projected with the pose; the shift (E x, E y) and turn about its centre that
give the best overlap. --target x_mm,y_mm[,yaw_deg] (Nov 8): the search is centred there and the push and OK are against
it (R2 y+3: 0,30; R3 x+3: 30,0). Push words follow B's E axes: +x away from the robot (toward the back wall), +y toward the
camera wall.
The camera pose comes from results/poses/<tag>.json (calib/pose.py, frame E), so the numbers are only as good as the
sled chain (config/board_in_E.json). Writes results/rig/scene_check_last.json and .png.
"""
import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import cv2
import numpy as np

GTC = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(GTC / "calib"), str(GTC / "real")]

import camera_lock  # noqa: E402
import capture  # noqa: E402
import live  # noqa: E402
import vial_check as V  # noqa: E402

MAT = json.loads((GTC / "config" / "layouts.json").read_text())["mat_env"]
RACK_O = (0.18, 0.08)
TOL_MM, TOL_DEG = 3.0, 0.3


def lift(uv, R, C, z):
    """Undistorted pixel(s) -> points on the plane z in E."""
    uv = np.atleast_2d(uv)
    K = lift.K
    d = np.column_stack([(uv[:, 0] - K[0, 2]) / K[0, 0], (uv[:, 1] - K[1, 2]) / K[1, 1], np.ones(len(uv))]) @ R.T
    t = (z - C[2]) / d[:, 2]
    return C + t[:, None] * d


def edge_points(gray, p0, p1, inside, n=60, half=45):
    """Bright -> dark transitions along the normals of the projected segment p0-p1; inside = a point on the mat side."""
    h, w = gray.shape
    g = cv2.GaussianBlur(gray.astype(np.float32), (0, 0), 1.5)
    t = (p1 - p0) / np.linalg.norm(p1 - p0)
    nrm = np.array([-t[1], t[0]])
    if np.dot(inside - p0, nrm) < 0:
        nrm = -nrm                                          # normal points into the mat
    out = []
    for s in np.linspace(0.05, 0.95, n):
        c = p0 + s * (p1 - p0)
        k = np.arange(-half, half + 1, dtype=np.float32)
        xy = c[None, :] + k[:, None] * nrm[None, :]
        if (xy[:, 0] < 1).any() or (xy[:, 0] > w - 2).any() or (xy[:, 1] < 1).any() or (xy[:, 1] > h - 2).any():
            continue
        xy = xy.astype(np.float32)
        prof = cv2.remap(g, xy[:, 0].reshape(1, -1), xy[:, 1].reshape(1, -1), cv2.INTER_LINEAR).ravel()
        d = np.diff(prof)                                     # into the mat: bright -> dark, so the step is negative
        i = int(np.argmin(d))
        if -d[i] < 25 or prof[:max(i - 3, 1)].mean() - prof[i + 4:].mean() < 40:
            continue
        a, b, cc = (d[i - 1], d[i], d[i + 1]) if 0 < i < len(d) - 1 else (0, d[i], 0)
        off = 0.5 * (a - cc) / (a - 2 * b + cc) if (a - 2 * b + cc) != 0 else 0.0
        out.append(c + (k[i] + 0.5 + off) * nrm)
    return np.array(out)


def fit_edge(P, axis):
    """Line through E points; axis 0: x = a + b*y (front/back edges), axis 1: y = a + b*x (far edge)."""
    u, v = (P[:, 1], P[:, 0]) if axis == 0 else (P[:, 0], P[:, 1])
    keep = np.ones(len(u), bool)
    for _ in range(3):
        b, a = np.polyfit(u[keep], v[keep], 1)
        r = v - (a + b * u)
        s = max(1.4826 * np.median(np.abs(r[keep])), 0.0003)
        keep = np.abs(r) < 3 * s
    return a, b, keep


def rack_mask(R, C, K, shape, dx, dy, yaw_deg, z0, h):
    cx, cy = RACK_O[0] + 0.06 + dx, RACK_O[1] + 0.06 + dy
    c, s = np.cos(np.radians(yaw_deg)), np.sin(np.radians(yaw_deg))
    sq = np.array([[-0.06, -0.06], [0.06, -0.06], [0.06, 0.06], [-0.06, 0.06]]) @ np.array([[c, s], [-s, c]])
    pts = np.vstack([np.column_stack([sq[:, 0] + cx, sq[:, 1] + cy, np.full(4, z)]) for z in (z0, z0 + h)])
    uv = V.project(pts, R, C, K)
    m = np.zeros(shape, np.uint8)
    cv2.fillConvexPoly(m, cv2.convexHull(np.round(uv * 4).astype(np.int32)), 1, cv2.LINE_8, 2)
    return m.astype(bool), uv


def fit_rack(yel, R, C, K, z0, h, target=(0.0, 0.0, 0.0)):
    """Best-overlap rack shift (m) and turn (deg); the coarse grid is centred on target (m, m, deg), +-30 mm."""
    tx, ty, tyaw = target
    best = (-1, tx, ty, tyaw)
    def iou(dx, dy, yaw):
        m, _ = rack_mask(R, C, K, yel.shape, dx, dy, yaw, z0, h)
        u = (m | yel).sum()
        return (m & yel).sum() / u if u else 0.0
    for dx in np.arange(tx - 0.03, tx + 0.0301, 0.003):
        for dy in np.arange(ty - 0.03, ty + 0.0301, 0.003):
            for yaw in (tyaw - 4, tyaw, tyaw + 4) if tyaw else (0.0,):
                v = iou(dx, dy, yaw)
                if v > best[0]:
                    best = (v, dx, dy, yaw)
    for step, span in ((0.001, 0.003), (0.00025, 0.001)):
        _, bx, by, byaw = best
        for dx in np.arange(bx - span, bx + span + 1e-9, step):
            for dy in np.arange(by - span, by + span + 1e-9, step):
                for yaw in np.arange(byaw - 2 * span * 1000 / 3, byaw + 2 * span * 1000 / 3 + 1e-9, max(step * 1000, 0.25)):
                    v = iou(dx, dy, yaw)
                    if v > best[0]:
                        best = (v, dx, dy, yaw)
    return best


def push(dx_mm, dy_mm):
    w = []
    if abs(dx_mm) > 0.5:
        w.append(f"push {abs(dx_mm):.1f} mm " + ("toward the robot" if dx_mm > 0 else "toward the back wall"))
    if abs(dy_mm) > 0.5:
        w.append(f"push {abs(dy_mm):.1f} mm " + ("toward the right wall" if dy_mm > 0 else "toward the camera wall"))
    return "; ".join(w) or "in place"


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--pose", default="r0")
    ap.add_argument("--source", default="camera:front")
    ap.add_argument("--frames", type=int, default=5)
    ap.add_argument("--mat-width-mm", type=float, default=457.2)
    ap.add_argument("--mat-top-z", type=float, default=0.035)
    ap.add_argument("--rack-h-cm", type=float, default=7.85)
    ap.add_argument("--no-rack", action="store_true")
    ap.add_argument("--target", default="0,0,0", help="rack target x_mm,y_mm[,yaw_deg] from the sim nominal in E "
                    "(e.g. 0,30 for R2 y+3; 30,0 for R3 x+3); the push and OK are against it")
    ap.add_argument("--out", default=str(GTC / "results" / "rig" / "scene_check_last"))
    a = ap.parse_args(argv)
    R, C, K, dist = V.load_camera(GTC / "results" / "poses" / f"{a.pose}.json", GTC / "config" / "c920_intrinsics.json")
    lift.K = K
    if a.source.startswith("camera:"):
        if camera_lock.cmd_apply(a.source.split(":", 1)[1], write=False) != 0:
            raise SystemExit("STOP: camera lock does not read back; run camera_lock.py apply front")
    src = capture.open_source(a.source)
    try:
        frames = [src.read() for _ in range(a.frames)]
    finally:
        src.close()
    rgb = V.undistort(np.median(np.stack(frames), axis=0).astype(np.uint8), K, dist)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    z = a.mat_top_z
    fx, bx, ry, ly = MAT["front_x"], MAT["back_x"], MAT["right_y"], MAT["left_y"]
    centre = V.project(np.array([[(fx + bx) / 2, 0.0, z]]), R, C, K)[0]
    edges = {"front": ((fx, ly - 0.17), (fx, ry), 0, fx), "back": ((bx, 0.05), (bx, ry), 0, bx),
             "far": ((fx + 0.01, ry), (bx - 0.01, ry), 1, ry)}
    vis = rgb.copy()
    res = {"utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "pose": a.pose,
           "mat_width_mm": a.mat_width_mm, "mat_top_z": z, "mat": {}, "source": a.source}
    lines = []
    for name, (e0, e1, axis, sim) in edges.items():
        p = V.project(np.array([[*e0, z], [*e1, z]]), R, C, K)
        pts = edge_points(gray, p[0], p[1], centre)
        cv2.line(vis, tuple(np.round(p[0]).astype(int)), tuple(np.round(p[1]).astype(int)), (0, 255, 0), 1, cv2.LINE_AA)
        if len(pts) < 10:
            res["mat"][name] = {"error": f"only {len(pts)} edge points"}
            lines.append(f"mat {name}: not found ({len(pts)} points)")
            continue
        E = lift(pts, R, C, z)
        a0, b0, keep = fit_edge(E, axis)
        for q in pts[keep]:
            cv2.circle(vis, tuple(np.round(q).astype(int)), 1, (255, 0, 0), -1)
        ends = (e0[1], e1[1]) if axis == 0 else (e0[0], e1[0])
        offs = [1000 * (a0 + b0 * u - sim) for u in ends]
        turn = np.degrees(np.arctan(b0))
        rec = {"offset_mm_ends": [round(o, 1) for o in offs], "turn_deg": round(float(turn), 2), "n_points": int(keep.sum()),
               "axis": "E x" if axis == 0 else "E y"}
        if name == "far":
            rec["camera_side_edge_y_mm_ends"] = [round(1000 * (a0 + b0 * u) + a.mat_width_mm, 1) for u in ends]
            rec["camera_side_edge_offset_mm_ends"] = [round(o + a.mat_width_mm - 1000 * (ly - ry), 1) for o in offs]
        rec["ok"] = bool(max(abs(o) for o in offs) <= TOL_MM and abs(turn) <= TOL_DEG)
        res["mat"][name] = rec
        where = "x (+ away from the robot)" if axis == 0 else "y (+ toward the camera wall)"
        lines.append(f"mat {name} edge: {offs[0]:+.1f} / {offs[1]:+.1f} mm in E {where}, turn {turn:+.2f} deg "
                     f"({'OK' if rec['ok'] else 'OFF'}, {keep.sum()} points)")
        if name == "far":
            lines.append(f"  -> camera-side edge {rec['camera_side_edge_offset_mm_ends'][0]:+.1f} / "
                         f"{rec['camera_side_edge_offset_mm_ends'][1]:+.1f} mm from the sim with a {a.mat_width_mm:.1f} mm wide mat")
    if not a.no_rack:
        import trial_runner as T
        yel = T.yellow_mask(rgb, T.CHECKS["yellow_hsv_lo"], T.CHECKS["yellow_hsv_hi"])
        n, lab, st, _ = cv2.connectedComponentsWithStats(yel.astype(np.uint8))
        if n > 1:
            k = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
            cnt, _ = cv2.findContours((lab == k).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            yel = np.zeros_like(yel, np.uint8)
            cv2.fillPoly(yel, [cv2.convexHull(max(cnt, key=cv2.contourArea))], 1)
            yel = yel.astype(bool)
        if yel.sum() < 2000:
            res["rack"] = {"error": "no rack seen"}
            lines.append("rack: not seen")
        else:
            tgt = [float(v) for v in a.target.split(",")] + [0.0] * (3 - len(a.target.split(",")))
            iou, dx, dy, yaw = fit_rack(yel, R, C, K, z, a.rack_h_cm / 100, (tgt[0] / 1000, tgt[1] / 1000, tgt[2]))
            _, uv0 = rack_mask(R, C, K, yel.shape, 0, 0, 0, z, a.rack_h_cm / 100)
            _, uv1 = rack_mask(R, C, K, yel.shape, dx, dy, yaw, z, a.rack_h_cm / 100)
            for uv, col in ((uv0, (0, 255, 255)), (uv1, (255, 0, 255))):
                for i, j in ((4, 5), (5, 6), (6, 7), (7, 4)):
                    cv2.line(vis, tuple(np.round(uv[i]).astype(int)), tuple(np.round(uv[j]).astype(int)), col, 1, cv2.LINE_AA)
            ex, ey, eyaw = 1000 * dx - tgt[0], 1000 * dy - tgt[1], float(yaw) - tgt[2]
            ok = bool(abs(ex) <= 2.0 and abs(ey) <= 2.0 and abs(eyaw) <= 1.0)
            res["rack"] = {"dx_mm": round(1000 * dx, 1), "dy_mm": round(1000 * dy, 1), "yaw_deg": round(float(yaw), 2),
                           "iou": round(float(iou), 3), "target": tgt, "vs_target": [round(ex, 1), round(ey, 1), round(eyaw, 2)],
                           "ok": ok, "push": push(ex, ey)}
            lines.append(f"rack: {1000 * dx:+.1f} mm in x, {1000 * dy:+.1f} mm in y, turn {yaw:+.2f} deg (IoU {iou:.3f})"
                         + (f"; target ({tgt[0]:+.0f}, {tgt[1]:+.0f} mm, {tgt[2]:+.0f} deg): {ex:+.1f} / {ey:+.1f} mm, "
                            f"{eyaw:+.2f} deg" if any(tgt) else "")
                         + f" -> {res['rack']['push']} ({'OK' if ok else 'OFF'}; 2 mm / 1 deg)")
    print("\n".join(lines))
    capture.save_rgb(a.out + ".png", np.vstack([vis, live.text_panel(lines + ["green: sim mat edges, blue: found edge points; "
                     "cyan: rack at the sim position, magenta: best fit"], vis.shape[1])]))
    Path(a.out + ".json").write_text(json.dumps(res, indent=1))
    print(f"-> {a.out}.png / .json")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
