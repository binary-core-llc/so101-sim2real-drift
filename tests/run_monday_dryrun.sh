#!/bin/bash
# Dry run of every Oct 26 tool with recorded/rendered images, fakes and mocks: no camera is opened or configured,
# no robot moves. Run from gtc/:  tests/run_monday_dryrun.sh [--no-docker] [--no-gui]
# Writes logs/dryrun/<test>.log and prints one line per test.
cd "$(dirname "$0")/.." || exit 1
PY=.venv/bin/python
S=$(mktemp -d)
mkdir -p logs/dryrun
fail=0
run() {  # name, command...
    local name=$1; shift
    if "$@" > "logs/dryrun/$name.log" 2>&1; then echo "  PASS  $name"; else echo "  FAIL  $name (logs/dryrun/$name.log)"; fail=1; fi
}
echo "Monday dry run, $(date -u +%FT%TZ), gtc $(git rev-parse --short HEAD)"
run v4l2_abi            python3 -I tests/test_v4l2_abi.py
run units_with_fakes    $PY -I tests/test_monday_units.py
run calib_synthetic_sets $PY -I tests/make_synthetic_calib.py "$S/raw" --views 45
run capture_set_A       $PY -I calib/intrinsics_capture.py --set TA --source "$S/raw/A" --out "$S/cap/TA" --meta-dir "$S/meta" --headless-auto 45
run capture_set_B       $PY -I calib/intrinsics_capture.py --set TB --source "$S/raw/B" --out "$S/cap/TB" --meta-dir "$S/meta" --headless-auto 45
# the solver exits 1 when a check FAILs; with synthetic sets only the 40 px image-corner coverage can fail (see log)
$PY -I calib/intrinsics_solve.py --square-mm 30.0 --sets TA TB --set-dirs "$S/cap/TA" "$S/cap/TB" --out "$S/intr.json" > logs/dryrun/intrinsics_solve.log 2>&1
$PY -I -c "
import json,sys
t=json.load(open('$S/raw/truth.json')); r=json.load(open('$S/intr.json'))
e=100*abs(r['K'][0][0]/t['K'][0][0]-1); bad=[c for c in r['checks'] if c['result']=='FAIL' and 'coverage' not in c['check']]
print('fx error %.3f %%, non-coverage FAILs:' % e, bad); sys.exit(0 if e < 0.5 and not bad else 1)" >> logs/dryrun/intrinsics_solve.log 2>&1 \
    && echo "  PASS  intrinsics_solve (fx within 0.5 %; every non-coverage check passes)" || { echo "  FAIL  intrinsics_solve"; fail=1; }
run pose_r0_and_reach   $PY -I tests/test_pose_synthetic.py
run pose_with_fitted_K  $PY -I tests/test_pose_synthetic.py "$S/intr.json"
run overlay_T20         $PY -I tests/test_overlay_synthetic.py
run drift_check         $PY -I tests/test_drift_synthetic.py
run light_log           $PY -I tests/test_light_log.py
mkdir -p "$S/W" && cp $(ls "$S"/cap/TA/view_0*.png | head -14) "$S/W/"
run wrist_intrinsics    $PY -I calib/intrinsics_solve.py --camera wrist --square-mm 30 --sets W --set-dirs "$S/W" --out "$S/wrist.json"
run wrist_overlay       $PY -I calib/overlay.py --camera wrist --source results/c1/nominal_wrist_rgb.png --headless-frames 3
run r0_board_frames    $PY -I tests/make_r0_board_frames.py "$S/r0"
run pose_measure_cli    env GTC_POSES_DIR="$S/poses" $PY -I calib/pose.py measure --tag dryrun_r0 --source "$S/r0" --frames 4 \
                            --intrinsics "$S/r0/intr.json" --board-in-e "$S/r0/board.json" --note course_35cm_measured_cm=35.0
run pose_reach_cli      env GTC_POSES_DIR="$S/poses" $PY -I calib/pose.py reach dryrun_r0
run unregistered_stops  bash -c "! python3 -I calib/usbcam.py find front && ! real/teleop.sh && ! real/start_pose.sh \
                            && ! real/calibrate_arm.sh follower && ! $PY -I calib/drift_check.py check --ref $S/none.png"
if [[ " $* " != *" --no-gui "* ]] && [ -n "${DISPLAY:-}" ]; then
    run gui_overlay     env GTC_GUI_SMOKE=20 $PY -I calib/overlay.py --ref sim_r0 --source results/overlay_refs/sim_r0_front_rgb.png
    run gui_capture     env GTC_GUI_SMOKE=20 $PY -I calib/intrinsics_capture.py --set GUI --source "$S/raw/A" --out "$S/cap/GUI" --meta-dir "$S/meta"
    run gui_pose_hud    env GTC_GUI_SMOKE=20 GTC_POSES_DIR="$S/poses" $PY -I calib/pose.py hud --ref dryrun_r0 --source "$S/r0" \
                            --intrinsics "$S/r0/intr.json" --board-in-e "$S/r0/board.json"
fi
if [[ " $* " != *" --no-docker "* ]]; then
    run calib_report    python3 -I real/calib_report.py --file ../Sim-to-Real-SO-101-Workshop/docker/real/scripts/sample_callibrations/orange.json
    (real/run_real.sh python /workspace/gtc/real/mock_policy_server.py --port 5599 --mode ok > "$S/mock_ok.log" 2>&1 &); sleep 8
    run pilot_cap_mock  bash -c "(sleep 40) | timeout 90 real/run_real.sh python /workspace/gtc/real/pilot.py --run dryrun_cap_$$ --mock-robot --yes --policy-port 5599 --cap-s 3"
    docker ps --format '{{.Names}}' | grep '^gtc-robot' | xargs -r docker rm -f > /dev/null
    (real/run_real.sh python /workspace/gtc/real/mock_policy_server.py --port 5599 --mode hang > "$S/mock_hang.log" 2>&1 &); sleep 8
    run pilot_timeout   bash -c "(sleep 30) | timeout 90 real/run_real.sh python /workspace/gtc/real/pilot.py --run dryrun_hang_$$ --mock-robot --yes --policy-port 5599; test \$? -eq 4"
    docker ps --format '{{.Names}}' | grep '^gtc-robot' | xargs -r docker rm -f > /dev/null
fi
echo "DRY RUN $([ $fail = 0 ] && echo PASS || echo FAIL)"
exit $fail
