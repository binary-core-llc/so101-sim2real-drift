#!/usr/bin/env python3
"""Light drift log dry run: 7 samples from rendered frames with a 1.8 % brightness drift, the last with moving
rolling bands. Expects the drift to be measured within 0.5 % (the frames are saved as 8-bit PNG: one grey level is
0.75 % of a floor patch near 133, so rounding alone moves the measured drift by up to about 0.4 %) and the bands
to be flagged.

    .venv/bin/python -I tests/test_light_log.py
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

GTC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GTC / "calib"))
import capture  # noqa: E402


def main():
    tmp = Path(tempfile.mkdtemp())
    ref = capture.load_rgb(GTC / "results/c1/nominal_front_rgb.png").astype(float)
    for i in range(7):
        for k in range(10):
            img = ref * (1 - 0.003 * i)
            if i == 6:
                img = img * (1 + 0.03 * np.sin(2 * np.pi * (np.arange(480)[:, None, None] / 60 + k / 3)))
            capture.save_rgb(tmp / f"s{i}" / f"f{k}.png", np.clip(img, 0, 255).astype(np.uint8))
        subprocess.run([sys.executable, "-I", str(GTC / "calib/light_log.py"), "run", "--source", str(tmp / f"s{i}"),
                        "--every-s", "0", "--samples", "1", "--out", str(tmp / "log.jsonl")], capture_output=True, check=True)
    rows = [json.loads(l) for l in open(tmp / "log.jsonl")]
    v = [r["floor_patch_mean"] for r in rows]
    drift = (max(v[:6]) - min(v[:6])) / np.mean(v[:6]) * 100
    r = subprocess.run([sys.executable, "-I", str(GTC / "calib/light_log.py"), "report", "--out", str(tmp / "log.jsonl")],
                       capture_output=True, text=True)
    ok = len(rows) == 7 and abs(drift - 1.5) < 0.5 and rows[6]["band_index_pct"] > 0.5 and rows[0]["band_index_pct"] < 0.1 \
        and "IN PROGRESS" in r.stdout
    print(f"  7 samples; drift over the first 6 = {drift:.2f} % (simulated 1.5 %); band index {rows[0]['band_index_pct']} -> "
          f"{rows[6]['band_index_pct']} %; report: {r.stdout.strip().splitlines()[-1]}")
    print("LIGHT LOG TEST", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
