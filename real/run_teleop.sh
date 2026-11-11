#!/bin/bash
# Run a command in the course's teleop/sim image (teleop-docker) with the robot's USB devices, the way the course
# runs arm calibration (docker/README.md "Simulation & Teleop Container" -> "Calibrate"): /dev, udev, the
# calibration folder, docker/env and the course scripts. Our offline entrypoint replaces the course one (no
# runtime pip install). No GPU and no display are needed for calibration.
#
#   real/run_teleop.sh lerobot-calibrate --robot.type=so101_follower --robot.port=/dev/ttyACM0 --robot.id=orange_robot
set -euo pipefail
COURSE=$HOME/gtc2027/Sim-to-Real-SO-101-Workshop
GTC=$HOME/gtc2027/gtc
CALIB=$HOME/.cache/huggingface/lerobot/calibration
mkdir -p "$CALIB"
TTY=(-i)
[ -t 0 ] && TTY=(-it)
exec docker run --rm "${TTY[@]}" --name "gtc-teleop-$$" --privileged --network host --init \
    -e ACCEPT_EULA=Y -e PRIVACY_CONSENT=Y -e PYTHONUNBUFFERED=1 \
    -v /dev:/dev -v /run/udev:/run/udev:ro \
    -v "$CALIB":/root/.cache/huggingface/lerobot/calibration \
    -v "$COURSE/docker/env":/root/env:ro \
    -v "$COURSE/source":/workspace/Sim-to-Real-SO-101-Workshop/source:ro \
    -v "$COURSE/docker/real/scripts":/workspace/Sim-to-Real-SO-101-Workshop/docker/real/scripts:ro \
    -v "$GTC":/workspace/gtc \
    -v "$GTC/docker/sim/entrypoint_offline.sh":/gtc_entrypoint.sh:ro \
    --entrypoint /gtc_entrypoint.sh \
    teleop-docker:latest "$@"
