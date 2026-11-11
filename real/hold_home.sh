#!/bin/bash
# Door clearance check (J6): the follower rises to the course start pose, then on Enter goes to the course home pose
# (the move every trial ends with) and holds there until Enter; then torque off. See real/hold_home.py.
# FIRST CONNECT OF THE ARM: keep a hand on the arm and the 12 V plug within reach - torque comes on before the
# goal is set to the current position.
#   real/hold_home.sh
set -euo pipefail
GTC=$HOME/gtc2027/gtc
cd "$GTC"
FOL=$(python3 -I calib/usbcam.py find follower | cut -d' ' -f1) || exit 3
echo "follower $FOL: door clearance check at the course home pose"
exec real/run_real.sh python /workspace/gtc/real/hold_home.py --port "$FOL"
