#!/usr/bin/env python3
"""calib/still_check.py on rendered R0 views of the real print (CLI, file sources; no camera).

    .venv/bin/python -I tests/test_still_check.py
R0 camera from config/r0_pose.json at 45.0 deg, the sled board at the B 4.2 CAD placement, the made-up test lens of
tests/make_synthetic_calib.py (test values, not readings). 'before' at R0; 'after' with other noise and the light
changed (gain 0.6, offset +12, as when the roof goes on): PASS; tilted 0.05 deg: PASS; tilted 0.3 deg and the lens
moved 2 mm sideways: FAIL; no 'before': STOP.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

GTC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GTC / "calib"))
sys.path.insert(0, str(GTC / "tests"))
import capture  # noqa: E402
import charuco as C  # noqa: E402
from make_synthetic_calib import DIST, K  # noqa: E402

BOARD = {"d_x_mm": 101.1, "d_y_mm": 89.2, "h_K_mm": 9.9, "yaw_deg": 0.0, "method": "test: B 4.2 CAD intent"}


def main():
    tmp = Path(tempfile.mkdtemp())
    (tmp / "board.json").write_text(json.dumps(BOARD))
    T_E_K, _ = C.board_in_E(tmp / "board.json")
    tex, H, _ = C.pdf_texture(300)
    r0 = json.loads((GTC / "config" / "r0_pose.json").read_text())
    C0, head = np.array(r0["target_lens_env"]), r0["target_heading_deg"]
    side = C.rot_from_angles(45.0, head, 0.0)[:, 0]                 # the camera's image-right axis in E

    def frames(name, dep=45.0, dC=(0, 0, 0), gain=1.0, offset=0.0, seed=0):
        T_cv_K = np.linalg.inv(C.T(C.rot_from_angles(dep, head, 0.0), C0 + np.array(dC))) @ T_E_K
        d = tmp / name
        for i in range(20):
            g = C.render_view(tex, H, K, DIST, T_cv_K, noise=1.5, blur=0.7, rng=np.random.default_rng(seed + i))
            g = np.clip(g.astype(float) * gain + offset, 0, 255).astype(np.uint8)
            capture.save_rgb(d / f"f{i:02d}.png", np.repeat(g[:, :, None], 3, 2))
        return d

    env = {**os.environ, "GTC_STILL_DIR": str(tmp / "out")}
    run = lambda *args: subprocess.run([sys.executable, "-I", str(GTC / "calib" / "still_check.py"), *args],  # noqa: E731
                                       capture_output=True, text=True, env=env)
    ok = True
    p = run("after", "--tag", "none", "--source", str(frames("unused")))
    good = p.returncode != 0 and "before" in p.stderr
    ok &= good
    print(f"  after without before: exit {p.returncode}  {'ok' if good else 'FAIL'}")
    p = run("before", "--tag", "r0", "--source", str(frames("before")))
    ok &= p.returncode == 0
    print(f"  before: {p.stdout.strip() or p.stderr.strip()[-200:]}")
    cases = (("still, light changed", dict(gain=0.6, offset=12, seed=100), 0),
             ("tilt 0.05 deg", dict(dep=45.05, seed=200), 0),
             ("tilt 0.3 deg", dict(dep=45.3, seed=300), 2),
             ("lens 2 mm sideways", dict(dC=tuple(0.002 * side), seed=400), 2))
    for name, kw, want in cases:
        p = run("after", "--tag", "r0", "--source", str(frames(name.replace(" ", "_"), **kw)))
        out = p.stdout.strip().splitlines()
        good = p.returncode == want
        ok &= good
        print(f"  {name:22s} exit {p.returncode} (want {want}): {out[0] if out else p.stderr.strip()[-200:]}  {'ok' if good else 'FAIL'}")
    print("STILL CHECK TEST", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
