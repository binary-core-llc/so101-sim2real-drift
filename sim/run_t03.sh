#!/bin/bash
# T03: first headless eval, course lerobot_eval.py unmodified, sim + GR00T server
# together, nvidia-smi logged every second. Needs groot-server already up (run_server.sh).
#
#   sim/run_t03.sh [num_episodes=20] [outdir=results/t03_<utc>]
#
# The course script never exits after its last episode (lerobot_eval.py:251-252,
# `while True: simulation_app.update()`), so this script stops the container once the
# "Success Rate:" line appears, and kills it anyway after HARD_TIMEOUT seconds.
set -uo pipefail
GTC=$(cd "$(dirname "$0")/.." && pwd)
cd "$GTC"
N=${1:-20}
UTC=$(date -u +%Y%m%dT%H%M%SZ)
OUT=${2:-results/t03_$UTC}
HARD_TIMEOUT=${HARD_TIMEOUT:-5400}
NAME=gtc-t03
TASK=Lerobot-So101-Teleop-Vials-To-Rack-Eval
RENAME='{"external_D455": "front", "ego": "wrist"}'
INSTR="Pick up the vial and place it in the yellow rack"
mkdir -p "$OUT"

.venv/bin/python -I sim/server_ping.py --timeout 10 > "$OUT/ping_before.json" || {
    echo "server does not answer; start it with sim/run_server.sh" >&2; cat "$OUT/ping_before.json"; exit 1; }

cat > "$OUT/run.json" <<EOF
{"test": "T03", "started_utc": "$UTC", "num_episodes": $N, "task": "$TASK",
 "script": "source/sim_to_real_so101/scripts/lerobot_eval.py (course, unmodified)",
 "seed": 1984, "seed_note": "course default --seed",
 "rename_map": $RENAME, "lang_instruction": "$INSTR",
 "server_container": "groot-server", "sim_container": "$NAME",
 "server_cmd": $(docker inspect groot-server --format '{{json .Config.Cmd}}')}
EOF

sim/gpu_log.sh "$OUT/gpu.csv" & GPULOG=$!
sleep 3   # a few baseline samples before the sim starts
date -u +%Y-%m-%dT%H:%M:%S.%3NZ > "$OUT/launch_utc.txt"

( timeout -k 30 "$HARD_TIMEOUT" sim/run_sim.sh "$NAME" \
    python source/sim_to_real_so101/scripts/lerobot_eval.py \
    --task "$TASK" --num_episodes "$N" --headless \
    --rename_map "$RENAME" --lang_instruction "$INSTR" 2>&1 \
  | python3 -I -u sim/stamp.py > "$OUT/eval.log" ) & RUN=$!

status=running
t0=$(date +%s)
while kill -0 $RUN 2>/dev/null; do
    if grep -q "Success Rate:" "$OUT/eval.log" 2>/dev/null; then
        status=completed; sleep 15; docker stop -t 10 "$NAME" >/dev/null 2>&1; break
    fi
    if grep -qE "Traceback|Segmentation fault|CUDA out of memory|Cannot connect" "$OUT/eval.log" 2>/dev/null; then
        status=error; sleep 20; docker stop -t 10 "$NAME" >/dev/null 2>&1; break
    fi
    sleep 5
done
wait $RUN 2>/dev/null
[ "$status" = running ] && status="exited_or_timeout_after_$(( $(date +%s) - t0 ))s"
kill $GPULOG 2>/dev/null; wait $GPULOG 2>/dev/null
.venv/bin/python -I sim/server_ping.py --timeout 10 > "$OUT/ping_after.json"
echo "{\"status\": \"$status\"}" > "$OUT/status.json"
.venv/bin/python -I sim/summarize_t03.py "$OUT" | tee "$OUT/summary.txt"
