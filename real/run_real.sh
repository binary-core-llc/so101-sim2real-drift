#!/bin/bash
# Run a command in the course's real-robot image (Isaac-GR00T ead52833, LeRobot 0.4.1) with the robot's USB
# devices: the robot health check and the pilot. Same device and calibration mounts as the course
# docker/README.md "Real Robot Container"; our repo is mounted at /workspace/gtc. The policy server is the
# separate groot-server container (sim/run_server.sh) on localhost:5555 (--network host). No GPU is used here.
#
#   real/run_real.sh python /workspace/gtc/real/robot_health.py --role follower
#   real/run_real.sh python /workspace/gtc/real/pilot.py --run pilot01
set -euo pipefail
COURSE=$HOME/gtc2027/Sim-to-Real-SO-101-Workshop
GTC=$HOME/gtc2027/gtc
CALIB=$HOME/.cache/huggingface/lerobot/calibration
mkdir -p "$CALIB"
TTY=(-i)
[ -t 0 ] && TTY=(-it)
cmd=("$@")
[ "${cmd[0]}" = python ] && cmd[0]=/Isaac-GR00T/.venv/bin/python

# The container runs as root; hand anything it writes under /workspace/gtc back to the host user.
exec docker run --rm "${TTY[@]}" --name "gtc-robot-$$" --privileged --network host --init \
    -e HOST_UID="$(id -u)" -e HOST_GID="$(id -g)" -e PYTHONUNBUFFERED=1 \
    -v /dev:/dev -v /run/udev:/run/udev:ro \
    -v "$CALIB":/root/.cache/huggingface/lerobot/calibration \
    -v "$COURSE/docker/env":/root/env:ro \
    -v "$COURSE/docker/real/scripts":/Isaac-GR00T/gr00t/eval/real_robot/SO100:ro \
    -v "$GTC":/workspace/gtc \
    -w /Isaac-GR00T real-robot \
    bash -c '"$@"; rc=$?; chown -R "$HOST_UID:$HOST_GID" /workspace/gtc/results /workspace/gtc/media /workspace/gtc/logs 2>/dev/null; exit $rc' _ "${cmd[@]}"
