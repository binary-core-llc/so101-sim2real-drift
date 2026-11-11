#!/bin/bash
# Arm calibration the course way (docker/README.md "Calibrate"; course page 07): lerobot-calibrate in the teleop
# container, then (follower) the course check docker/real/scripts/so101_check_calibration.py, which must end
# "Overall: ✓ PASS", then real/calib_report.py (sha256 + joint scale vs sim).
# The port comes only from the arm's registered USB identity (calib/usbcam.py); ids from the course docker/env.
#
#   real/calibrate_arm.sh follower      # robot id from docker/env ROBOT_ID (orange_robot)
#   real/calibrate_arm.sh leader        # teleop id from docker/env TELEOP_ID (orange_teleop)
#
# lerobot-calibrate turns torque off and asks you to move each joint by hand (no motor motion). The course check
# connects the follower without calibrating; LeRobot's connect() writes its standard servo settings and briefly
# enables torque, so the arm holds still; no motion is commanded.
set -euo pipefail
ROLE=${1:?usage: real/calibrate_arm.sh follower|leader}
GTC=$HOME/gtc2027/gtc
COURSE=$HOME/gtc2027/Sim-to-Real-SO-101-Workshop
cd "$GTC"
PORT=$(python3 -I calib/usbcam.py find "$ROLE" | cut -d' ' -f1) || exit 3
eval "$(grep -E '^export (ROBOT_ID|TELEOP_ID)=' "$COURSE/docker/env")"
echo "role $ROLE on $PORT"
if [ "$ROLE" = follower ]; then
    real/run_teleop.sh lerobot-calibrate --robot.type=so101_follower --robot.port="$PORT" --robot.id="$ROBOT_ID"
    echo "FIRST CONNECT of the follower next: keep a hand on the arm and the 12 V plug within reach (torque comes on"
    echo "before the goal is set to the current position). Press Enter when ready."; read -r _
    real/run_teleop.sh bash -c "export ROBOT_PORT=$PORT ROBOT_ID=$ROBOT_ID; \
        python /workspace/Sim-to-Real-SO-101-Workshop/docker/real/scripts/so101_check_calibration.py" \
        | tee "logs/robot_check_calibration_$(date -u +%Y%m%dT%H%M%SZ).log"
else
    real/run_teleop.sh lerobot-calibrate --teleop.type=so101_leader --teleop.port="$PORT" --teleop.id="$TELEOP_ID"
fi
python3 -I real/calib_report.py "$ROLE"
