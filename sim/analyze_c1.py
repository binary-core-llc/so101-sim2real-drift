#!/usr/bin/env python3
"""C1 analysis on the host (no GPU): T04 checks, V04 patch colours, straight-edge
(fisheye) check, V03 background. Reads what dump_scene.py wrote.

    .venv/bin/python -I sim/analyze_c1.py [results/c1]

Writes <dir>/c1_checks.json and <dir>/nominal_front_checks.png (overlay).
Thresholds marked [P] are proposals, not course facts.
"""
import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np

# T04 expected values (D_software T04)
EXP_MOUNT = (0.1846, 0.3359, 0.4893)
EXP_ROBOT = (-0.05, 0.0, 0.0)
EXP_ROBOT_YAW = 90.0
EXP_RACK = (0.18, 0.08, 0.06)
TOL_M, TOL_DEG = 0.001, 0.05            # [P] D_software T04
EDGE_RMS_PX, EDGE_SAG_PX = 0.7, 1.5     # [P] straight-edge pass limits
WALLS = ("Back", "Left", "Right")


def load(d):
    f = json.loads((d / "frames_sim.json").read_text())
    rgb = cv2.cvtColor(cv2.imread(str(d / "nominal_front_rgb.png")), cv2.COLOR_BGR2RGB)
    ids = cv2.imread(str(d / "nominal_front_instance_ids.png"), cv2.IMREAD_UNCHANGED)
    info = json.loads((d / "nominal_front_instance_labels.json").read_text())
    labs = info["instance_labels"]
    # dump_scene.py v0 looked colours up with string keys while the live idToLabels used tuple
    # keys, so labels came out None; rebuild them from the saved raw mapping.
    raw = {str(tuple(int(x) for x in k.strip("()").split(","))): v for k, v in info["idToLabels_raw"].items()}
    for e in labs.values():
        if e.get("label") is None and "rgba" in e:
            e["label"] = raw.get(str(tuple(e["rgba"])))
    return f, rgb, ids, labs


def masks_by(ids, labs, pred):
    m = np.zeros(ids.shape, bool)
    for i, e in labs.items():
        if pred(e.get("label") or ""):
            m |= ids == int(i)
    return m


def class_masks(f, ids, labs):
    printed = {p for p, mat in f["robot"]["mesh_materials"].items() if mat and "3d_printed" in mat}
    lb = "/LightStudio/LightBox/"
    c = {
        "floor_base": masks_by(ids, labs, lambda s: s.endswith(lb + "Base")),
        "mat": masks_by(ids, labs, lambda s: "/Mat/" in s),
        "rack": masks_by(ids, labs, lambda s: "/Rack_Left/" in s),
        "blue_cap": masks_by(ids, labs, lambda s: "/Vial_" in s and s.endswith("/Mesh_001")),
        "vial_body": masks_by(ids, labs, lambda s: "/Vial_" in s and s.endswith("/Mesh_002")),
        "robot_orange": masks_by(ids, labs, lambda s: s in printed or any(s.startswith(p + "/") for p in printed)),
        "robot_all": masks_by(ids, labs, lambda s: "/Robot/" in s),
        "background_unlabelled": masks_by(ids, labs, lambda s: s in ("", "BACKGROUND", "UNLABELLED")),
    }
    for w in WALLS + ("Top",):
        c["wall_" + w] = masks_by(ids, labs, lambda s, w=w: s.endswith(lb + w))
    return c


def stats(rgb, m, erode=3):
    k = np.ones((2 * erode + 1, 2 * erode + 1), np.uint8)
    me = cv2.erode(m.astype(np.uint8), k) > 0 if erode else m
    if me.sum() == 0:
        return {"pixels": int(m.sum()), "pixels_eroded": 0}
    px = rgb[me].astype(float)
    dist = cv2.distanceTransform(me.astype(np.uint8), cv2.DIST_L2, 5)
    y, x = np.unravel_index(np.argmax(dist), dist.shape)
    h = int(max(1, min(7, dist[y, x] - 1)))
    patch = rgb[y - h:y + h + 1, x - h:x + h + 1].reshape(-1, 3).astype(float)
    return {"pixels": int(m.sum()), "pixels_eroded": int(me.sum()),
            "mean_rgb": px.mean(0).round(2).tolist(), "median_rgb": np.median(px, 0).tolist(),
            "std_rgb": px.std(0).round(2).tolist(),
            "interior_patch": {"center_xy": [int(x), int(y)], "size_px": 2 * h + 1,
                               "mean_rgb": patch.mean(0).round(2).tolist()}}


def boundary(a, b):
    """pixel centres on the a|b boundary (midpoints between 4-neighbours)."""
    pts = []
    for dy, dx in ((0, 1), (1, 0)):
        aa = a[: a.shape[0] - dy, : a.shape[1] - dx]
        bb = b[dy:, dx:]
        ab = a[dy:, dx:] & b[: b.shape[0] - dy, : b.shape[1] - dx]
        for m in (aa & bb, ab):
            yy, xx = np.nonzero(m)
            pts.append(np.c_[xx + dx / 2.0, yy + dy / 2.0])
    return np.vstack(pts) if pts else np.zeros((0, 2))


def line_fit(p):
    if len(p) < 20:
        return None
    c = p.mean(0)
    u, s, vt = np.linalg.svd(p - c, full_matrices=False)
    d, n = vt[0], vt[1]
    t = (p - c) @ d
    r = (p - c) @ n
    span = float(t.max() - t.min())
    a, b, cc = np.polyfit(t, r, 2)
    sag = abs(a) * (span / 2) ** 2
    rq = r - np.polyval([a, b, cc], t)
    return {"n": int(len(p)), "span_px": round(span, 1), "rms_px": round(float(np.sqrt((r ** 2).mean())), 3),
            "max_abs_px": round(float(np.abs(r).max()), 3), "sagitta_px": round(float(sag), 3),
            "rms_after_quadratic_px": round(float(np.sqrt((rq ** 2).mean())), 3),
            "pass": bool(np.sqrt((r ** 2).mean()) <= EDGE_RMS_PX and sag <= EDGE_SAG_PX),
            "_c": c, "_d": d, "_tminmax": (float(t.min()), float(t.max()))}


def cv_pose(cam):
    """world->OpenCV camera R,t from the USD camera world matrix (row-vector convention)."""
    M = np.array(cam["world_usd"]["matrix_row_major_usd"])
    R_usd = M[:3, :3] / np.linalg.norm(M[:3, :3], axis=1, keepdims=True)  # rows: cam axes in world
    pos = M[3, :3]
    R_cw = np.c_[R_usd[0], -R_usd[1], -R_usd[2]]   # columns: cv x,y,z axes in world
    R_wc = R_cw.T
    return R_wc, -R_wc @ pos


def project(P, K, R, t):
    X = (R @ P.T).T + t
    ok = X[:, 2] > 1e-6
    uv = (K @ X.T).T
    return uv[:, :2] / uv[:, 2:3], ok


def floor_edges_3d(panels):
    base = panels["Base"]
    zf = base["world_bbox_max"][2]
    cx = 0.5 * (base["world_bbox_min"][0] + base["world_bbox_max"][0])
    cy = 0.5 * (base["world_bbox_min"][1] + base["world_bbox_max"][1])
    edges = {}
    for w in WALLS:
        if w not in panels:
            continue
        lo, hi = np.array(panels[w]["world_bbox_min"]), np.array(panels[w]["world_bbox_max"])
        ext = hi - lo
        ax = int(np.argmin(ext[:2]))            # thickness axis (0=x, 1=y)
        centre = (cx, cy)[ax]
        inner = lo[ax] if abs(lo[ax] - centre) < abs(hi[ax] - centre) else hi[ax]
        o = 1 - ax
        a = np.zeros(3); b = np.zeros(3)
        a[ax] = b[ax] = inner
        a[o], b[o] = lo[o], hi[o]
        a[2] = b[2] = zf
        edges[w] = np.linspace(a, b, 200)
    return edges


def dist_to_polyline(p, poly):
    best = np.full(len(p), np.inf)
    for q0, q1 in zip(poly[:-1], poly[1:]):
        v = q1 - q0
        L2 = max(v @ v, 1e-12)
        s = np.clip(((p - q0) @ v) / L2, 0, 1)
        best = np.minimum(best, np.linalg.norm(p - (q0 + s[:, None] * v), axis=1))
    return best


def near(a, b, tol):
    return all(abs(x - y) <= tol for x, y in zip(a, b))


def main(d):
    d = Path(d)
    f, rgb, ids, labs = load(d)
    out = {"dir": str(d)}

    # ---- T04
    mount = f["camera_mount"]["world_usd"]["pos"]
    root = f["robot"]["root"]
    rack0 = f["objects_after_reset"]["rack_left"]["pos"]
    rackw = f["objects_after_warmup10"]["rack_left"]["pos"]
    cam = f["camera_external_D455"]
    K = np.array(cam["tiled_camera"]["intrinsic_matrices"])
    W = cam["tiled_camera"]["image_shape"][1]
    fl, hap = cam["usd"]["focalLength"], cam["usd"]["horizontalAperture"]
    out["T04"] = {
        "camera_mount_env": {"got": mount, "expected": EXP_MOUNT, "pass": near(mount, EXP_MOUNT, TOL_M)},
        "robot_root": {"got_pos": root["pos"], "got_rpy_deg": root["rpy_deg_xyz"], "expected_pos": EXP_ROBOT,
                       "expected_yaw_deg": EXP_ROBOT_YAW,
                       "pass": near(root["pos"], EXP_ROBOT, TOL_M) and abs(root["rpy_deg_xyz"][2] - EXP_ROBOT_YAW) <= TOL_DEG},
        "rack_corner_after_reset": {"got": rack0, "expected": EXP_RACK, "pass": near(rack0, EXP_RACK, TOL_M)},
        "rack_after_warmup10": {"got": rackw, "z_drop_m": round(rack0[2] - rackw[2], 4)},
        "env_origin": {"got": f["env_origin"], "pass": near(f["env_origin"], (0, 0, 0), 1e-9)},
    }
    out["camera_external"] = {
        "focalLength_mm": fl, "horizontalAperture_mm": hap, "verticalAperture_mm": cam["usd"]["verticalAperture"],
        "projection": cam["usd"]["projection"],
        "fx_fy_cx_cy": [K[0, 0], K[1, 1], K[0, 2], K[1, 2]],
        "fx_expected_if_1.93mm": round(640 * 1.93 / 2.4, 2),
        "hfov_deg_from_K": round(math.degrees(2 * math.atan(W / 2 / K[0, 0])), 2),
        "vfov_deg_from_K": round(math.degrees(2 * math.atan(cam["tiled_camera"]["image_shape"][0] / 2 / K[1, 1])), 2),
        "optical_axis_deg_below_horizontal": round(cam["optical_axis_deg_below_horizontal"], 2),
        "camera_world_pos": cam["world_usd"]["pos"],
        "tiled_pos_w_minus_usd_m": (np.array(cam["tiled_camera"]["pos_w"]) - np.array(cam["world_usd"]["pos"])).round(6).tolist(),
        "lens_related_attributes": {k: v for k, v in cam["all_attributes"].items()
                                    if any(s in k.lower() for s in ("fisheye", "ftheta", "lensdistortion", "projection", "distortion"))},
    }

    # ---- V04 patches + V03
    cm = class_masks(f, ids, labs)
    pat = {k: stats(rgb, m) for k, m in cm.items()}
    band = cv2.dilate(cm["mat"].astype(np.uint8), np.ones((81, 81), np.uint8)) > 0
    band &= ~(cv2.dilate(cm["mat"].astype(np.uint8), np.ones((11, 11), np.uint8)) > 0)
    pat["floor_beside_mat"] = stats(rgb, cm["floor_base"] & band, erode=1)
    out["V04_patches"] = {k: pat[k] for k in ("floor_beside_mat", "floor_base", "mat", "rack", "blue_cap", "robot_orange")}
    out["other_classes"] = {k: v for k, v in pat.items() if k not in out["V04_patches"]}
    out["V04_note"] = ("means over each class mask eroded 3 px (floor_beside_mat: floor pixels 5-40 px from the mat, eroded 1 px); "
                       "interior_patch = up to 15x15 px at the mask's most interior point; Eval nominal, exposure -1 EV")
    out["V03_background"] = pat["background_unlabelled"]

    # ---- straight-edge check (floor|wall) + projection of the 3D edge with K
    R, t = cv_pose(cam)
    e3d = floor_edges_3d(f["lightbox_panels"])
    vis = rgb.copy()
    edges = {}
    for w in WALLS:
        p = boundary(cm["floor_base"], cm["wall_" + w])
        fit = line_fit(p)
        e = {"boundary_pixels": int(len(p))}
        if fit:
            c, dvec, (t0, t1) = fit.pop("_c"), fit.pop("_d"), fit.pop("_tminmax")
            e["fit"] = fit
            a, b = c + t0 * dvec, c + t1 * dvec
            cv2.line(vis, tuple(np.round(a).astype(int)), tuple(np.round(b).astype(int)), (0, 255, 0), 1)
        if w in e3d and len(p):
            uv, ok = project(e3d[w], K, R, t)
            uv = uv[ok]
            inimg = (uv[:, 0] >= -50) & (uv[:, 0] <= W + 50)
            if inimg.sum() > 2:
                dist = dist_to_polyline(p, uv[inimg])
                e["vs_pinhole_projection_px"] = {"mean": round(float(dist.mean()), 3),
                                                 "p95": round(float(np.percentile(dist, 95)), 3),
                                                 "max": round(float(dist.max()), 3)}
                cv2.polylines(vis, [np.round(uv[inimg]).astype(np.int32)], False, (255, 0, 255), 1)
        edges[w] = e
    fitted = [e["fit"] for e in edges.values() if "fit" in e and e["fit"]["span_px"] >= 100]
    out["straight_edge_check"] = {
        "edges": edges,
        "verdict": ("PASS: pinhole (edges straight)" if fitted and all(x["pass"] for x in fitted)
                    else "CHECK: no long edge measured" if not fitted else "FAIL: edges curved -> possible fisheye"),
        "limits": {"rms_px": EDGE_RMS_PX, "sagitta_px": EDGE_SAG_PX, "min_span_px": 100, "tag": "[P]"},
        "overlay": "green = fitted straight line, magenta = 3D floor-wall edge projected with the dumped K and pose",
    }
    for k in ("floor_beside_mat", "mat", "rack", "blue_cap", "robot_orange"):
        ip = pat[k].get("interior_patch")
        if ip:
            x, y = ip["center_xy"]; h = ip["size_px"] // 2
            cv2.rectangle(vis, (x - h, y - h), (x + h, y + h), (0, 255, 255), 1)
            cv2.putText(vis, k, (x + h + 2, y), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 255), 1)
    cv2.imwrite(str(d / "nominal_front_checks.png"), cv2.cvtColor(vis, cv2.COLOR_RGB2BGR))

    (d / "c1_checks.json").write_text(json.dumps(out, indent=1, default=float) + "\n")
    s = out["straight_edge_check"]
    print(json.dumps({"T04": {k: v.get("pass") for k, v in out["T04"].items()},
                      "camera": {k: out["camera_external"][k] for k in ("focalLength_mm", "horizontalAperture_mm", "fx_fy_cx_cy",
                                                                        "hfov_deg_from_K", "vfov_deg_from_K", "projection",
                                                                        "optical_axis_deg_below_horizontal")},
                      "edges": {w: {**e.get("fit", {}), **({"vs_proj": e["vs_pinhole_projection_px"]} if "vs_pinhole_projection_px" in e else {})}
                                for w, e in s["edges"].items()},
                      "edge_verdict": s["verdict"],
                      "V04_mean_rgb": {k: v.get("mean_rgb") for k, v in out["V04_patches"].items()},
                      "V03_background": {k: out["V03_background"].get(k) for k in ("pixels", "mean_rgb")}}, indent=1, default=float))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "results/c1")
