#!/bin/bash
# End-to-end dry run of real/trial_runner.py in the real-robot container against the mock policy server (no GPU):
# replayed C1 renders as camera frames, a mock arm that moves nothing, no camera or serial device is opened.
# Run from gtc/:  tests/run_trial_dryrun.sh
# Everything goes to media/dryrun_real/e2e_<utc>/ (git-ignored). Containers are removed by their exact names only.
cd "$(dirname "$0")/.." || exit 1
PY=.venv/bin/python
R=media/dryrun_real/e2e_$(date -u +%Y%m%dT%H%M%SZ)
W=/workspace/gtc/$R
mkdir -p "$R/logs"
fail=0
echo "trial runner dry run, $(date -u +%FT%TZ), output $R"

server() {  # port mode -> pid of run_real.sh (container gtc-robot-<pid>)
    real/run_real.sh python /workspace/gtc/real/mock_policy_server.py --port "$1" --mode "$2" > "$R/logs/mock_$2.log" 2>&1 &
    echo $!
}
runc() {  # name feed expect_rc args... : one runner container, at most 150 s, removed by exact name afterwards
    local name=$1 feed=$2 want=$3; shift 3
    ( eval "$feed" ) | real/run_real.sh python /workspace/gtc/real/trial_runner.py "$@" > "$R/logs/$name.log" 2>&1 &
    local pid=$! t=0
    while kill -0 $pid 2>/dev/null && [ $t -lt 150 ]; do sleep 1; t=$((t+1)); done
    docker rm -f "gtc-robot-$pid" > /dev/null 2>&1
    wait $pid; local rc=$?
    if [ "$rc" = "$want" ]; then echo "  PASS  $name (exit $rc, ${t} s)"; else echo "  FAIL  $name (exit $rc, want $want; $R/logs/$name.log)"; fail=1; fi
}
COMMON=(--root "$W" --schedule /workspace/gtc/config/schedule.csv --mock-robot --yes)
F6='{"outcome":"F","grasp":"n","fail_code":"F6"}'
S='{"outcome":"S","grasp":"y","hold_2s":"y","hold_05s":"y"}'

# references from noisy copies of the render (host venv, as the operator would run it with --draw)
$PY -I -c "
import sys; sys.path[:0]=['calib']
import capture, numpy as np
img = capture.load_rgb('results/c1/nominal_front_rgb.png'); r = np.random.default_rng(1)
for k in range(10):
    capture.save_rgb('$R/frames/f%02d.png' % k, np.clip(img + r.normal(0, 2, img.shape), 0, 255).astype(np.uint8))
t = img.copy(); t[60:85, 40:110] = 235; capture.save_rgb('$R/tape_front.png', t)"
for tag in N04-R0_R0; do
    $PY -I real/trial_runner.py reference --root "$R" --mock --tag $tag --frames 10 --source "$R/frames" \
        --ignore-rects "330,200,560,330;420,300,640,480" > "$R/logs/reference.log" 2>&1 \
        && echo "  PASS  reference $tag" || { echo "  FAIL  reference $tag"; fail=1; }
done
# refused before anything runs (host)
$PY -I real/trial_runner.py next --yes > "$R/logs/yes_refused.log" 2>&1
grep -q "only for --mock-robot" "$R/logs/yes_refused.log" && echo "  PASS  --yes refused without --mock-robot" \
    || { echo "  FAIL  --yes refused"; fail=1; }

OK=$(server 5599 ok); HANG=$(server 5598 hang); sleep 10
runc cap_next        "sleep 60"            0 next "${COMMON[@]}" --policy-port 5599 --cap-s 3 --score-json "$F6"
runc key_s           "sleep 14; echo s; sleep 60" 0 run --uid N04-002 "${COMMON[@]}" --policy-port 5599 --cap-s 40 --score-json "$S"
runc cleanview_tape  "sleep 60"            3 run --uid N04-003 "${COMMON[@]}" --policy-port 5599 --mock-pre-front "$W/tape_front.png"
runc watchdog        "sleep 60"            4 run --uid N04-003 "${COMMON[@]}" --policy-port 5598 --score-json '{"outcome":"I","grasp":"n"}'
runc rerun_invalid   "sleep 60"            0 run --uid N04-003 "${COMMON[@]}" --policy-port 5599 --cap-s 3 --score-json "$F6"
runc scored_refused  "sleep 60"            1 run --uid N04-001 "${COMMON[@]}" --policy-port 5599
runc freeze_I1       "sleep 60"            0 run --uid N04-004 "${COMMON[@]}" --policy-port 5599 --cap-s 3 --mock-freeze --score-json '{"outcome":"I","grasp":"n"}'
runc pilot           "sleep 60"            0 run --pilot V28-T1 --cond R1 --layout L00 "${COMMON[@]}" --policy-port 5599 --cap-s 3 --skip-checks --score-json "$F6"
echo '{"joints": {"shoulder_pan.pos": {"scale": 0.92, "offset": 1.5}, "gripper.pos": {"scale": 0.87}}}' > "$R/jmap.json"
runc joint_map       "sleep 60"            0 run --uid N04-005 "${COMMON[@]}" --policy-port 5599 --cap-s 3 --joint-map "$W/jmap.json" --score-json "$F6"
docker rm -f "gtc-robot-$OK" "gtc-robot-$HANG" > /dev/null 2>&1

# what the records say
$PY -I - "$R" <<'EOF' || fail=1
import json, sys
from pathlib import Path
R = Path(sys.argv[1]); res = R / "results" / "dryrun_real"
recs = [json.loads(l) for l in open(res / "trials.jsonl")]
pre = [json.loads(l) for l in open(res / "prestart.jsonl")] if (res / "prestart.jsonl").exists() else []
by = {(r["uid"], r["attempt"]): r for r in recs}
ok = []
def check(name, cond, detail=""):
    ok.append(bool(cond)); print(f"  {'ok  ' if cond else 'FAIL'} {name} {detail}")
a = by.get(("N04-001", 1), {})
check("cap: N04-001 ends at the cap with keyframes, steps and MP4s", a.get("end_reason") == "cap" and a.get("n_chunks", 0) > 2
      and a.get("keyframes_written") == a.get("n_chunks") and Path(a.get("kf_front_mp4") or "/x").name == "kf_front.mp4",
      f"{a.get('n_chunks')} chunks, lat med {a.get('lat_ms_med')} ms, act period p95 {a.get('act_period_ms_p95')} ms")
check("cap: checks ran and passed", a.get("checks", {}).get("pass") is True, json.dumps(a.get("checks", {}).get("drift", {}))[:120])
b = by.get(("N04-002", 1), {})
check("key s: success_key, S scored", b.get("end_reason") == "success_key" and b.get("live_outcome") == "S", f"{b.get('run_s')} s")
check("tape in view: prestart I0, no trial record", any(p["uid"] == "N04-003" and "check failed" in p["reason"] for p in pre)
      and ("N04-003", 0) not in by)
c = by.get(("N04-003", 1), {})
check("watchdog: hang server -> watchdog, auto I3, scored I3", c.get("end_reason") == "watchdog" and "I3" in c.get("auto_invalid", [])
      and c.get("invalid_code") == "I3", c.get("end_detail"))
c2 = by.get(("N04-003", 2), {})
check("re-run of the invalid = attempt 2, rerun_of set", c2.get("rerun_of") == "N04-003_a1" and c2.get("end_reason") == "cap")
d = by.get(("N04-004", 1), {})
check("frozen frames -> auto I1", "I1" in d.get("auto_invalid", []) and d.get("invalid_code") == "I1", json.dumps(d.get("max_identical_keyframes")))
p = by.get(("V28-T1", 1), {})
check("pilot row recorded with skipped checks", p.get("block") == "PILOT" and p.get("checks", {}).get("skipped") is True)
e = by.get(("N04-005", 1), {})
steps = [json.loads(l) for l in open(R / "results" / "dryrun_real" / "steps" / "N04-005_a1.jsonl")] if e else []
sent_ok = bool(steps) and all(abs(x["shoulder_pan.pos"] - min(100, max(-100, 0.92 * y["shoulder_pan.pos"] + 1.5))) < 1e-6
                              for st in steps for x, y in zip(st.get("actions_sent", []), st["actions"]))
check("joint map: recorded with its hash, mapped actions logged", (e.get("joint_map") or {}).get("sha256") and sent_ok
      and by.get(("N04-001", 1), {}).get("joint_map") is None, json.dumps((e.get("joint_map") or {}).get("joints")))
check("provenance on every record", all(r.get("schedule_sha256") and r.get("runner_sha256") and r.get("gtc_commit") for r in recs))
check("trials.csv has one line per record", len((res / "trials.csv").read_text().splitlines()) == len(recs) + 1)
print(f"  records {len(recs)}, prestart {len(pre)}")
sys.exit(0 if all(ok) else 1)
EOF
echo "TRIAL DRY RUN $([ $fail = 0 ] && echo PASS || echo FAIL)"
exit $fail
