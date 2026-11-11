#!/bin/bash
# Log GPU memory/utilisation every second (UTC timestamps) until killed.
#   sim/gpu_log.sh <out.csv>  &   ...   kill %1
# Two files: <out.csv> = whole GPU; <out>.procs.csv = per-process memory.
set -u
OUT=${1:?usage: gpu_log.sh out.csv}
PROCS=${OUT%.csv}.procs.csv
echo "utc,mem_used_mib,mem_total_mib,util_gpu_pct,temp_c,power_w" > "$OUT"
echo "utc,pid,process_name,used_mib" > "$PROCS"
while true; do
    ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    nvidia-smi --query-gpu=memory.used,memory.total,utilization.gpu,temperature.gpu,power.draw \
        --format=csv,noheader,nounits | sed "s/^/$ts,/; s/, /,/g" >> "$OUT"
    nvidia-smi --query-compute-apps=pid,process_name,used_memory \
        --format=csv,noheader,nounits | sed "s/^/$ts,/; s/, /,/g" >> "$PROCS"
    sleep 1
done
