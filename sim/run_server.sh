#!/bin/bash
# Start the GR00T N1.6 policy server (course real-robot image, ada build) as a
# detached container named groot-server. Same mounts and command as the course
# docker/README.md "Serving the model", minus X11/devices (not needed to serve).
#
#   sim/run_server.sh [model_subpath]      default: the sim-only checkpoint-10000
#   docker logs -f groot-server            follow it
#   docker rm -f groot-server              stop it
#
# A dedicated HF cache (~/sim2real/hf_cache) is mounted so anything the server
# fetches once is kept for offline runs; the host's own HF token is NOT mounted.
set -euo pipefail

MODEL=${1:-aravindhs-NV/grootn16-finetune_sreetz-so101_teleop_vials_rack_left/checkpoint-10000}
MODELS_DIR=${MODELS_DIR:-$HOME/sim2real/models}
HF_CACHE=${HF_CACHE:-$HOME/sim2real/hf_cache}
PORT=${PORT:-5555}
COURSE=$HOME/gtc2027/Sim-to-Real-SO-101-Workshop
OFFLINE=${HF_HUB_OFFLINE:-0}

[ -d "$MODELS_DIR/$MODEL" ] || { echo "model not found: $MODELS_DIR/$MODEL" >&2; exit 1; }
mkdir -p "$HF_CACHE"

if docker ps -a --format '{{.Names}}' | grep -qx groot-server; then
    echo "groot-server already exists; remove it first: docker rm -f groot-server" >&2
    exit 1
fi

docker run -d --name groot-server --network host --gpus all \
    -e HF_HUB_OFFLINE="$OFFLINE" \
    -v "$MODELS_DIR":/workspace/models:ro \
    -v "$HF_CACHE":/root/.cache/huggingface \
    -v "$COURSE/docker/env":/root/env:ro \
    -v "$COURSE/docker/real/scripts":/Isaac-GR00T/gr00t/eval/real_robot/SO100:ro \
    -w /Isaac-GR00T \
    real-robot \
    /Isaac-GR00T/.venv/bin/python gr00t/eval/run_gr00t_server.py \
        --model-path "/workspace/models/$MODEL" --port "$PORT"

echo "started groot-server: model=$MODEL port=$PORT offline=$OFFLINE"
