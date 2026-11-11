#!/usr/bin/env python3
"""Static frames of the sled board seen from the R0 camera target (for CLI and GUI dry runs of pose.py).

    .venv/bin/python -I tests/make_r0_board_frames.py OUT_DIR
Writes OUT_DIR/frame_*.png (4 noisy frames), OUT_DIR/intr.json (the made-up test lens) and OUT_DIR/board.json
(B 4.2 CAD intent).
"""
import json
import sys
from pathlib import Path

import numpy as np

GTC = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(GTC / "calib"), str(GTC / "tests")]
import capture  # noqa: E402
import charuco as C  # noqa: E402
from make_synthetic_calib import DIST, K  # noqa: E402
from test_pose_synthetic import R_E_cv  # noqa: E402

out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
r0 = json.loads((GTC / "config/r0_pose.json").read_text())
(out / "board.json").write_text(json.dumps({"d_x_mm": 101.1, "d_y_mm": 89.2, "h_K_mm": 9.9, "yaw_deg": 0.0}))
(out / "intr.json").write_text(json.dumps({"K": K.tolist(), "dist": DIST.tolist()}))
T_E_K, _ = C.board_in_E(out / "board.json")
T_cv_K = np.linalg.inv(C.T(R_E_cv(45.0, r0["target_heading_deg"], 0.0), r0["target_lens_env"])) @ T_E_K
tex, H, _ = C.pdf_texture(300)
for i in range(4):
    capture.save_rgb(out / f"frame_{i}.png", np.repeat(C.render_view(tex, H, K, DIST, T_cv_K, rng=np.random.default_rng(i))[:, :, None], 3, 2))
print(f"wrote 4 R0 board frames to {out}")
