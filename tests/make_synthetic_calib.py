#!/usr/bin/env python3
"""Synthetic ChArUco calibration sets of the real print (docs/ChArUco_GTC_SO101_letter.pdf) seen by a camera with a
known test lens, posed as B section 3.2 asks. For dry runs of the capture tool and the solver.

    .venv/bin/python -I tests/make_synthetic_calib.py OUT_DIR [--views 45]
Writes OUT_DIR/A/view_*.png, OUT_DIR/B/view_*.png and OUT_DIR/truth.json (K, dist). The test lens is made up
(C920-like numbers, not a measurement).
"""
import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "calib"))
import capture  # noqa: E402
import charuco as C  # noqa: E402

K = np.array([[495.0, 0, 318.4], [0, 496.2, 243.7], [0, 0, 1]])
DIST = np.array([0.09, -0.21, 0.001, -0.0007, 0.12])
CENTRE = np.array([0.12, 0.09, 0.0])


def poses(rng, n, inplane):
    """B 3.2 per 15: 3 fronto-parallel (0.30/0.50/0.75 m), 8 tilted 30-45 deg about x/y, 4 in the corners at ~20 deg."""
    out = []
    while len(out) < n:
        k = len(out) % 15
        if k < 3:
            d, tx, ty, off = (0.30, 0.50, 0.75)[k], 0.0, 0.0, (0, 0)
        elif k < 11:
            ang = math.radians(rng.uniform(30, 45)) * (1 if k % 2 else -1)
            d = rng.uniform(0.35, 0.6)
            tx, ty = (ang, 0.0) if k < 7 else (0.0, ang)
            off = (rng.uniform(-0.03, 0.03), rng.uniform(-0.03, 0.03))
        else:
            d, ang = rng.uniform(0.40, 0.55), math.radians(20)
            sx, sy = ((1, 1), (1, -1), (-1, 1), (-1, -1))[k - 11]
            tx, ty = sy * ang * 0.7, -sx * ang * 0.7
            off = (sx * d * 0.62, sy * d * 0.50)    # board pushed into the image corner (partly cut off)
        dirn = np.array([math.sin(ty), -math.sin(tx), -math.cos(tx) * math.cos(ty)])
        cam = CENTRE + d * dirn / np.linalg.norm(dirn)
        target = CENTRE + np.array([off[0], off[1], 0.0])
        up = (1, 0, 0) if inplane else (0, -1, 0)
        T = C.look_at_pose(cam, target, up_hint=up)
        if k >= 11:   # corner view: Newton on the aim point until the board's outer corner sits 3 px inside the image corner
            corner = np.array([[3, 3], [636, 3], [3, 476], [636, 476]], float)[(k - 11) % 4]
            outer = np.array([[0, 0, 0], [0.24, 0, 0], [0, 0.18, 0], [0.24, 0.18, 0]])

            def proj(tg):
                Tt = C.look_at_pose(cam, tg, up_hint=up)
                p, _ = cv2.projectPoints(outer, cv2.Rodrigues(Tt[:3, :3])[0], Tt[:3, 3], K, DIST)
                return p.reshape(-1, 2)
            j = int(np.argmin(np.hypot(*(proj(CENTRE) - corner).T)))
            target = CENTRE.copy()
            for _ in range(40):
                e = proj(target)[j] - corner
                if np.hypot(*e) < 1:
                    break
                J = np.column_stack([(proj(target + dv)[j] - proj(target)[j]) / 1e-3
                                     for dv in (np.array([1e-3, 0, 0]), np.array([0, 1e-3, 0]))])
                step = np.linalg.lstsq(J, -e, rcond=None)[0]
                target = target + 0.7 * np.array([step[0], step[1], 0.0])
            T = C.look_at_pose(cam, target, up_hint=up)
        out.append(T)
    return out


def main(argv):
    out = Path(argv[0])
    n = int(argv[argv.index("--views") + 1]) if "--views" in argv else 45
    tex, H, _ = C.pdf_texture(300)
    rng = np.random.default_rng(7)
    for s, inplane in (("A", False), ("B", True)):
        (out / s).mkdir(parents=True, exist_ok=True)
        for i, T in enumerate(poses(rng, n, inplane)):
            g = C.render_view(tex, H, K, DIST, T, noise=1.5, blur=0.7, rng=np.random.default_rng(1000 * (s == "B") + i))
            capture.save_rgb(out / s / f"view_{i:03d}.png", np.repeat(g[:, :, None], 3, axis=2))
    (out / "truth.json").write_text(json.dumps({"K": K.tolist(), "dist": DIST.tolist(), "note": "made-up test lens"}))
    print(f"wrote {2 * n} views to {out}")


if __name__ == "__main__":
    main(sys.argv[1:])
