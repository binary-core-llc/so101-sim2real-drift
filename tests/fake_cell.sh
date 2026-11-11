#!/bin/bash
# Mock cell for the queue tests (T10a): writes JSONL rows + heartbeat like sweep_eval.py.
#   fake_cell.sh <cell> <start_episode> <n_episodes>; FAKE_MODE in ok|crash|hang|crash_once
cell=$1; k=$2; n=$3; R=${GTC_Q_ROOT:-$(dirname "$0")/..}/results/${GTC_Q_SUBDIR:-sim}; mkdir -p $R
mode=${FAKE_MODE:-ok}; [[ $cell == *crash* ]] && mode=crash; [[ $cell == *hang* ]] && mode=hang; [[ $cell == *readback* ]] && mode=readback
[[ $cell == *flaky* ]] && { [ -f "$R/$cell.flag" ] && mode=ok || { touch "$R/$cell.flag"; mode=crash_after1; }; }
for ((e=k; e<n; e++)); do
  date -u +%FT%TZ > $R/$cell.heartbeat
  [ $mode = crash ] && { echo "boom"; exit 1; }
  [ $mode = readback ] && { echo "[EXIT] code 2"; exit 1; }
  [ $mode = hang ] && { echo "hanging"; sleep 3600; }
  sleep 0.3
  echo "{\"utc\": \"$(date -u +%FT%T.%3N+00:00)\", \"cell\": \"$cell\", \"episode\": $e, \"seed\": $((1000+e)), \"status\": \"ok\", \"success\": true, \"wall_s\": 0.3}" >> $R/$cell.jsonl
  [ $mode = crash_after1 ] && { echo "crash after one episode"; exit 1; }
done
exit 0
