#!/bin/bash
# Teleoperation (course docker/README.md "lerobot-teleoperate"), for the reach test V25: can the gripper bring an
# upright vial over the far slots with the rack at x+3? Ports only from the arms' registered USB identity; ids from
# the course docker/env. FIRST CONNECT OF EACH ARM: keep a hand on the arm and the 12 V plug within reach -
# torque comes on before the goal is set to the current position. Ctrl+C ends it.
#   real/teleop.sh
set -euo pipefail
GTC=$HOME/gtc2027/gtc
COURSE=$HOME/gtc2027/Sim-to-Real-SO-101-Workshop
cd "$GTC"
FOL=$(python3 -I calib/usbcam.py find follower | cut -d' ' -f1) || exit 3
LEAD=$(python3 -I calib/usbcam.py find leader | cut -d' ' -f1) || exit 3
eval "$(grep -E '^export (ROBOT_ID|TELEOP_ID)=' "$COURSE/docker/env")"
echo "follower $FOL ($ROBOT_ID), leader $LEAD ($TELEOP_ID)"
exec real/run_teleop.sh lerobot-teleoperate --robot.type=so101_follower --robot.port="$FOL" --robot.id="$ROBOT_ID" \
    --teleop.type=so101_leader --teleop.port="$LEAD" --teleop.id="$TELEOP_ID"
