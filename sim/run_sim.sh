#!/bin/bash
# Run a command in the course sim image (teleop-docker), headless.
# Same image, entrypoint and Isaac Sim cache mounts as the course docker/README.md
# "Simulation & Teleop Container", minus X11, /dev and the calibration mount.
# Our repo is mounted at /workspace/gtc (results are written there) and the local asset
# mirror (T32) at /workspace/assets_mirror.
#
#   sim/run_sim.sh <name> <command...>
#   e.g. sim/run_sim.sh t03 python source/sim_to_real_so101/scripts/lerobot_eval.py --headless ...
#
# Network modes (T32):
#   default      --network=host, NVIDIA's S3 hosts blocked (resolve to 127.0.0.1); localhost works
#   NET=none     no network at all (scene tests without the policy server)
#   ALLOW_S3=1   do not block S3 (only to reproduce the course's online behaviour)
#
# Entrypoint: docker/sim/entrypoint_offline.sh = the course entrypoint without its runtime
# `pip install -e` (PyPI at every start); the course source is imported via PYTHONPATH.
set -euo pipefail
NAME=${1:?usage: run_sim.sh <container-name> <command...>}; shift
COURSE=$HOME/gtc2027/Sim-to-Real-SO-101-Workshop
GTC=$HOME/gtc2027/gtc
MIRROR=$HOME/sim2real/assets_mirror
C=$HOME/docker/isaac-sim
mkdir -p $C/cache/{kit,ov,pip,glcache,computecache} $C/{logs,data,documents}

NETARGS=(--network=host)
[ "${NET:-host}" = none ] && NETARGS=(--network=none)
if [ "${ALLOW_S3:-0}" != 1 ] && [ "${NET:-host}" != none ]; then
    NETARGS+=(--add-host omniverse-content-production.s3-us-west-2.amazonaws.com:127.0.0.1
              --add-host omniverse-content-production.s3.us-west-2.amazonaws.com:127.0.0.1)
fi

# The container runs as root; hand anything it writes under /workspace/gtc back to the host user.
exec docker run --name "$NAME" --rm --gpus all "${NETARGS[@]}" \
    -e ACCEPT_EULA=Y -e PRIVACY_CONSENT=Y -e OMNI_KIT_ACCEPT_EULA=YES \
    -e HOST_UID="$(id -u)" -e HOST_GID="$(id -g)" -e PYTHONUNBUFFERED=1 -e GTC_GIT -e GTC_IMAGE \
    -v $C/cache/kit:/isaac-sim/kit/cache:rw \
    -v $C/cache/ov:/root/.cache/ov:rw \
    -v $C/cache/pip:/root/.cache/pip:rw \
    -v $C/cache/glcache:/root/.cache/nvidia/GLCache:rw \
    -v $C/cache/computecache:/root/.nv/ComputeCache:rw \
    -v $C/logs:/root/.nvidia-omniverse/logs:rw \
    -v $C/data:/root/.local/share/ov/data:rw \
    -v $C/documents:/root/Documents:rw \
    -v "$COURSE/docker/env":/root/env:ro \
    -v "$COURSE/source":/workspace/Sim-to-Real-SO-101-Workshop/source:ro \
    -v "$GTC":/workspace/gtc \
    -v "$MIRROR":/workspace/assets_mirror:ro \
    -v "$GTC/docker/sim/entrypoint_offline.sh":/gtc_entrypoint.sh:ro \
    --entrypoint /gtc_entrypoint.sh \
    teleop-docker:latest \
    bash -c '"$@"; rc=$?; chown -R "$HOST_UID:$HOST_GID" /workspace/gtc/results /workspace/gtc/media /workspace/gtc/logs 2>/dev/null; exit $rc' _ "$@"
