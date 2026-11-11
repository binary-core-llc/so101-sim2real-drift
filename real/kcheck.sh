#!/bin/bash
# K-check (B 4.9, E V30), robot part: the follower goes to the 5 poses in config/kcheck_poses.json (30 mm above,
# then the hover), the operator reads the jaw tip on the sled's grid. See calib/kcheck.py.
# Before: config/board_in_E.json measured, `.venv/bin/python -I calib/kcheck.py poses` run after it; rack and vials
# off the mat; sled seated (paper test on both lobes); door open.
# FIRST CONNECT OF THE ARM: keep a hand on the arm and the 12 V plug within reach - torque comes on before the
# goal is set to the current position.
#   real/kcheck.sh
set -euo pipefail
GTC=$HOME/gtc2027/gtc
cd "$GTC"
FOL=$(python3 -I calib/usbcam.py find follower | cut -d' ' -f1) || exit 3
echo "follower $FOL: K-check"
exec real/run_real.sh python /workspace/gtc/calib/kcheck.py run --port "$FOL"
