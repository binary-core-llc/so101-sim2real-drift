#!/bin/bash
# Hold the follower at the course start pose (docker/README.md "Reset to home": so101_control.py moves to the
# initial pose on start and to the home pose on Ctrl+C). No camera is given to it, so the wrist camera stays free
# for: .venv/bin/python -I calib/overlay.py --camera wrist   (E_premortem G10, V19).
# FIRST CONNECT OF THE ARM: keep a hand on the arm and the 12 V plug within reach - torque comes on before the
# goal is set to the current position.
#   real/start_pose.sh          (Ctrl+C: the arm goes to the home pose)
set -euo pipefail
GTC=$HOME/gtc2027/gtc
COURSE=$HOME/gtc2027/Sim-to-Real-SO-101-Workshop
cd "$GTC"
FOL=$(python3 -I calib/usbcam.py find follower | cut -d' ' -f1) || exit 3
eval "$(grep -E '^export ROBOT_ID=' "$COURSE/docker/env")"
echo "follower $FOL ($ROBOT_ID): moving to the course start pose; Ctrl+C to go home"
exec real/run_real.sh python /Isaac-GR00T/gr00t/eval/real_robot/SO100/so101_control.py \
    --robot.type=so101_follower --robot.port="$FOL" --robot.id="$ROBOT_ID"
