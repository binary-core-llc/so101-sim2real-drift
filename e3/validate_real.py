#!/usr/bin/env python3
"""E3 on real photos with ground truth (development only; never on scored photos before the freeze).

    python validate_real.py dev --gtc <gtc root> [--ids D01 D02 ...] [--backend numpy|torch] [--scene-cache cache/scene.npz]
        DEV photos (gtc calib/dev_photos.py: results/photoset_dev/<id>.json): rack mode with the camera at the photo's
        board-measured pose; estimate vs the intended rack offset.
    python validate_real.py cam --gtc <gtc root> --ref-photo R.png --ref-pose s1.json --photo P.png --pose camK.json [...]
        A camera change (e.g. a CAM block's reference against the S1 block reference): differential camera mode
        (E3 on both photos); estimated change vs the board-measured change (pose camK - pose s1), in B 1.3 terms.
Writes <gtc>/results/e3/validate_real_<mode>_<utc>.json.
"""
import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import estimate as E  # noqa: E402
import render as Rn  # noqa: E402
import segment as Sg  # noqa: E402


def setup(a):
    G = Path(a.gtc)
    j = json.loads((G / "config" / "c920_intrinsics.json").read_text())
    K, dist = np.array(j["K"], float), np.array(j["dist"], float).ravel()
    scene, rig = Rn.load_scene(G / "results" / "c1" / "frames_sim.json", a.usd_dir, cache=a.scene_cache)
    if a.backend == "torch":
        import render_gpu
        be = render_gpu.TorchBackend(scene)
    else:
        be = E.NumpyBackend(scene)
    return G, K, dist, scene, rig, be


def classes(path, K, dist):
    rgb = cv2.imread(str(path))[:, :, ::-1]
    ri, inside = Sg.undistort(rgb, K, dist)
    return Sg.classify(ri, inside)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["dev", "cam"])
    ap.add_argument("--gtc", required=True)
    ap.add_argument("--ids", nargs="*")
    ap.add_argument("--ref-photo")
    ap.add_argument("--ref-pose")
    ap.add_argument("--photo")
    ap.add_argument("--pose")
    ap.add_argument("--backend", choices=["numpy", "torch"], default="numpy")
    ap.add_argument("--scene-cache", default=str(HERE / "cache" / "scene.npz"))
    ap.add_argument("--usd-dir")
    a = ap.parse_args(argv)
    G, K, dist, scene, rig, be = setup(a)
    f = float(K[0, 0])
    out = {"mode": a.mode, "utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "backend": a.backend,
           "version_hash": E.version_hash(), "rows": []}
    if a.mode == "dev":
        recs = sorted((G / "results" / "photoset_dev").glob("*.json"))
        for p in recs:
            r = json.loads(p.read_text())
            if a.ids and r["photo_id"] not in a.ids:
                continue
            cp = (r.get("gt") or {}).get("camera_pose") or {}
            if "R_E_cv" not in cp:
                out["rows"].append({"photo_id": r["photo_id"], "error": "no ground-truth camera pose in E"})
                continue
            R, C = np.array(cp["R_E_cv"]), np.array(cp["C_E_m"])
            x, secs = E.search_rack_cem(be, f, R, C, classes(G / r["files"]["clean"], K, dist), log=lambda *z: None)
            it = r["intended"]["rack_delta"]
            est = {"x_mm": float(x[0]), "y_mm": float(x[1]), "yaw_deg": float(x[2])}
            err = {"x_mm": est["x_mm"] - 1000 * it["x_m"], "y_mm": est["y_mm"] - 1000 * it["y_m"], "yaw_deg": est["yaw_deg"] - it["yaw_deg"]}
            out["rows"].append({"photo_id": r["photo_id"], "description": r["description"], "intended": it, "estimate": est,
                                "error_vs_intended": err, "seconds": round(secs, 1)})
            print(f"{r['photo_id']}: intended ({1000 * it['x_m']:+.0f}, {1000 * it['y_m']:+.0f} mm, {it['yaw_deg']:+.1f} deg) "
                  f"estimate ({est['x_mm']:+.1f}, {est['y_mm']:+.1f} mm, {est['yaw_deg']:+.2f} deg) -> error "
                  f"({err['x_mm']:+.1f}, {err['y_mm']:+.1f} mm, {err['yaw_deg']:+.2f} deg) [{secs:.0f} s]")
        # relative to the photos at the zero offset (the jig's plate N): the plates' differences are exact (30.0 mm)
        rows = [r for r in out["rows"] if "estimate" in r]
        zero = [r["estimate"] for r in rows if not any(r["intended"].values())]
        if zero:
            base = {k: float(np.mean([z[k] for z in zero])) for k in ("x_mm", "y_mm", "yaw_deg")}
            out["zero_offset_mean"] = base
            print(f"relative to the mean of the {len(zero)} zero-offset photos ({base['x_mm']:+.1f}, {base['y_mm']:+.1f} mm, "
                  f"{base['yaw_deg']:+.2f} deg):")
            for r in rows:
                it = r["intended"]
                rel = {k: r["estimate"][k] - base[k] for k in base}
                r["error_vs_intended_relative"] = {"x_mm": rel["x_mm"] - 1000 * it["x_m"], "y_mm": rel["y_mm"] - 1000 * it["y_m"],
                                                   "yaw_deg": rel["yaw_deg"] - it["yaw_deg"]}
                e = r["error_vs_intended_relative"]
                print(f"  {r['photo_id']}: ({e['x_mm']:+.1f}, {e['y_mm']:+.1f} mm, {e['yaw_deg']:+.2f} deg)")
    else:
        Rn0, Cn0 = E.load_pose(a.ref_pose)
        Rg, Cg = E.load_pose(a.pose)
        Rr, Cr, _, s1 = E.search_camera_cem(be, f, Rn0, Cn0, classes(a.ref_photo, K, dist), log=lambda *z: None)
        Rp, Cp, _, s2 = E.search_camera_cem(be, f, Rn0, Cn0, classes(a.photo, K, dist), log=lambda *z: None)
        est = E.b13_delta(Rr, Cr, Rp, Cp)
        gt = E.b13_delta(Rn0, Cn0, Rg, Cg)
        err = {k: est[k] - gt[k] for k in gt}
        out["rows"].append({"ref_photo": a.ref_photo, "photo": a.photo, "estimate": est, "ground_truth": gt, "error": err,
                            "seconds": round(s1 + s2, 1)})
        print("estimate " + ", ".join(f"{k} {v:+.4f}" for k, v in est.items()))
        print("truth    " + ", ".join(f"{k} {v:+.4f}" for k, v in gt.items()))
        print(f"error: tilt {err['tilt_down_deg']:+.2f} pan {err['pan_deg']:+.2f} roll {err['roll_deg']:+.2f} deg; lateral "
              f"{1000 * err['lateral_m']:+.1f} depth {1000 * err['depth_m']:+.1f} height {1000 * err['height_m']:+.1f} mm "
              f"[{s1 + s2:.0f} s]")
    od = G / "results" / "e3"
    od.mkdir(parents=True, exist_ok=True)
    (od / f"validate_real_{a.mode}_{out['utc'].replace(':', '')}.json").write_text(json.dumps(out, indent=1, default=float))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
