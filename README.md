# How far can a real SO-101 setup drift before a sim-trained GR00T policy fails?

Arturo Morales Rangel, Binary Core LLC

Code, pre-registration and records of a study submitted to NVIDIA GTC 2027 as a poster.

## What this is

NVIDIA's course "Train an SO-101 Robot From Sim-to-Real With NVIDIA Isaac" publishes a GR00T N1.6 checkpoint, trained in Isaac Lab, that places a vial in a rack. This study asked how far a real SO-101 setup can differ from the course's simulation before that policy fails, whether the training randomization range predicts the tolerance, and whether one photo is enough to correct the setup. The checkpoint was used as published, without fine-tuning, and the study was pre-registered.

In simulation (50 single-factor cells, 2,220 episodes), the nominal scene succeeded in 124 of 200 episodes (62 %), and no registered cell brought success below half of that (the lowest was 15/40), so all five registered thresholds were censored; exploratory camera tilts of 12° and 15° gave 16/40 and 5/40. With the real camera's measured focal length, success was 148/200 at the simulated camera pose and 99/200 at the real camera's measured pose, 24.2 mm and 1.0° away (Fisher p = 6.7 × 10⁻⁷). On the real robot, blind-scored (61 trial records, 56 valid): 6 of 20 at the measured nominal pose (30 %, 95 % CI 15-52 %), 2 of 10 with the rack moved 3 cm, 0 of 6 with the camera tilted 6° further down, and 1 of 10 with the camera placed by the course's written measurements; live and blind scores agreed (Cohen's κ = 1.00). The one-photo correction was not tested on the robot. `poster/numbers.json` lists every number on the poster with its sources and method.

## What's inside

| Path | What |
|---|---|
| `PREREGISTRATION_*.md`, `sweep_cells_v1.csv` | the pre-registration (see [Pre-registration](#pre-registration)) |
| `analysis/` | the pre-registered statistics, the simulated thresholds and the blind-score analysis |
| `assets/local/` | offline wrapper layers over the course's unmodified USD files |
| `calib/` | the camera check kit: USB identity, camera lock, lens calibration, ChArUco pose, the HUD and the live viewers |
| `config/` | this study's rig, camera, layout, sweep-cell and schedule files (measured values) |
| `docker/sim/` | the course's simulation Dockerfile with two pinned dependencies, and an offline entrypoint (diffs included) |
| `docs/` | the ChArUco board: printable PDF and its definition |
| `e1/` | E1: Cosmos Reason estimates (local model) and their selection |
| `e3/` | E3: render-and-compare on the GPU, as frozen at e3 commit `399025f` (usage in `e3/README.md`) |
| `explore/` | exploratory simulation runs (not pre-registered) |
| `notes/` | run summaries, the sign table, and `gtc_file_map.md` (the source of every copied file) |
| `poster/` | `numbers.json`: every number on the poster, with its value, sources, method and status |
| `real/` | the trial runner, the robot wrappers and checks |
| `results/` | simulation episodes, trial records, blind score sheets and keys, analysis outputs, simulation reference renders |
| `sim/` | policy server, simulation wrapper, sweep queue and evaluation, scene dump, sweep-cell builders |
| `stencils/` | printable 1:1 vial stencils for the layouts L00-L09 |
| `tests/` | unit tests and dry runs |
| `tools/` | pose and scene tools, judge-clip cutting, blind renaming, reports |
| `requirements.txt`, `requirements-e1.txt` | the exact Python packages of the two host environments |

Kept exactly as used in the study, because their SHA-256 is recorded in the trial and analysis records or the pre-registration: `real/trial_runner.py`, `real/pilot.py`, `config/schedule.csv`, `config/c920_intrinsics.json`, `analysis/blind_results.py`, the E3 code (`e3/`, frozen at e3 commit `399025f`) and the E1 script `e1/e1_estimate.py`.

Code comments cite the study's private protocol documents by label: A to E with a section or row (A build specification, B measurement, C trials, D software, E premortem), and item IDs such as V25, G8 or T03 (verification items, premortem items and gates, tests). Each tool's usage and limits are in its own docstring and in this README.

## Requirements

Hardware:
- SO-101 follower and leader arms, with the follower's wrist camera, as in the course.
- A Logitech C920 webcam as the front camera.
- The lightbox, mat, rack and vials per the course's bill of materials.
- An NVIDIA GPU for the simulation and the policy server. The study used one RTX A4500 (20 GB, Ampere) for both.
- For the camera check kit: a printer for US Letter at 100 %, matte paper, a steel ruler and foam board for the sled.

Software, as pinned in `config/versions.json`:
- Linux with Docker and the NVIDIA Container Toolkit (the study: Ubuntu 22.04.5, Docker 27.5.1, toolkit 1.17.8, driver 580.65.06; the course image's Isaac Sim 5.1 crashed on driver 595 on this machine).
- The course repository at commit `ce807d9`, with its Git LFS files.
- Two images: `teleop-docker` for the simulation, built from `nvcr.io/nvidia/isaac-lab:2.3.2` with `docker/sim/Dockerfile` from this repository, and the course's `real-robot` image (Isaac-GR00T `ead52833`) for the policy server and the robot.
- The checkpoint `aravindhs-NV/grootn16-finetune_sreetz-so101_teleop_vials_rack_left`, `checkpoint-10000`, Hugging Face revision `7efab50d`.
- Python 3.12 with [uv](https://docs.astral.sh/uv/) for the host tools.

```bash
cd ~/gtc2027/Sim-to-Real-SO-101-Workshop
docker build -t teleop-docker -f ~/gtc2027/gtc/docker/sim/Dockerfile .
./docker/real/build.sh ada          # ada or blackwell; the study used ada on its Ampere card

cd ~/gtc2027/gtc
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt
# E1 only (Cosmos-Reason2-2B on the GPU; torch from the PyTorch cu128 index):
uv venv --python 3.12 .venv-e1
uv pip install --python .venv-e1/bin/python --index-strategy unsafe-best-match -r requirements-e1.txt

# the checkpoint (the `hf` command comes with huggingface_hub, in .venv-e1); the optimizer state is not needed
.venv-e1/bin/hf download aravindhs-NV/grootn16-finetune_sreetz-so101_teleop_vials_rack_left \
    --revision 7efab50dfd58cd8f1831035fd86b65410b98c448 --exclude "checkpoint-10000/optimizer.pt" \
    --local-dir ~/sim2real/models/aravindhs-NV/grootn16-finetune_sreetz-so101_teleop_vials_rack_left

# once, with internet: the course's remote assets, so that simulation runs fetch nothing
.venv/bin/python -I tools/mirror_remote_assets.py
```

## Folder layout

The scripts use fixed paths under `~/gtc2027` and `~/sim2real`, so clone this repository as `~/gtc2027/gtc`. The `source` paths in `poster/numbers.json` are relative to `~/gtc2027`.

```
~/gtc2027/
├── gtc/                          this repository
├── e3 -> gtc/e3                  symlink: sim/run_sim.sh mounts it at /workspace/e3
└── Sim-to-Real-SO-101-Workshop/  the course repository at ce807d9
~/sim2real/
├── models/                       checkpoints (sim/run_server.sh); E1: models/nvidia/Cosmos-Reason2-2B
├── assets_mirror/                the mirrored course assets (tools/mirror_remote_assets.py; sim/run_sim.sh mounts it)
└── hf_cache/                     the policy server's Hugging Face cache (sim/run_server.sh)
~/docker/isaac-sim/               Isaac Sim caches (created by sim/run_sim.sh)
~/.cache/huggingface/lerobot/calibration/   the arms' LeRobot calibration (real/run_real.sh mounts it)
~/.config/gtc/nvidia_api_key      only for e1/t23_api_identity.py (mode 600)
```

```bash
mkdir -p ~/gtc2027 && cd ~/gtc2027
git clone https://github.com/binary-core-llc/so101-sim2real-drift.git gtc
ln -s gtc/e3 e3
git clone https://github.com/isaac-sim/Sim-to-Real-SO-101-Workshop.git
cd Sim-to-Real-SO-101-Workshop && git checkout ce807d9 && git lfs install && git lfs pull
```

## Camera check kit

Measures where the real front camera is in the simulation's frame and helps set it to the simulated camera. Run every step from `~/gtc2027/gtc` with `P=".venv/bin/python -I"`. The tools find cameras and arms only by their registered USB identity and stop otherwise. `SQ` below is the measured square size of the printed board in mm (the study: 29.97).

**0. Register and lock the cameras.** No other program may hold the camera.
```bash
python3 -I calib/usbcam.py list                   # read-only: lists the USB cameras and serial adapters
python3 -I calib/usbcam.py register front         # the C920 (writes config/devices.json); then: register wrist
$P calib/camera_lock.py tune front                # click the white floor; e/E g/G w/W adjust; q
$P calib/camera_lock.py focus front --square-mm SQ
$P calib/camera_lock.py lock front --exposure E --gain G --wb W
$P calib/preflight.py
```
Good: `lock` reads every value back; `preflight.py` exits 0 (both cameras found, 640 x 480, at least 29 fps each, lock read back after the streams open). After an unplug or reboot: `$P calib/camera_lock.py apply all`.

**1. Print and check the board.** Print `docs/ChArUco_GTC_SO101_letter.pdf` at 100 % (actual size) on matte US Letter, landscape: 8 x 6 squares of 30 mm, 22 mm markers, DICT_5X5_100 (`docs/charuco_board.json`). The line under the board must measure 100 mm. With a steel ruler, measure X across columns 1-7 (six squares) in rows 1 and 5, and Y across rows 1-5 (four squares) in columns 1 and 7. Good: X 180.0 ± 0.5 mm, Y 120.0 ± 0.4 mm, X/Y within 0.2 %; otherwise reprint. SQ = mean X / 6.

**2. The sled.** The board is glued flat on a foam-board carrier, the sled: a tongue whose end face touches both front lobes of the robot base, and a key that sits in the gap between them, so the board's pose in the simulation frame is known. Grid origin = the printed top-left grid corner, title text toward the camera wall, long side along the box depth.

The study's sled, from one piece of 3/16 in foam board: a tongue 90 mm wide, 79 mm from its end face to the carrier; a carrier 285 x 222 mm, centred on the tongue's centre line; and, at the end face, a key 5 mm long that sits in the V-shaped gap between the base's two front lobes. The key's design width is 40.6 mm: cut it 41.6 mm wide, then trim both sides equally until the end face touches both lobes with at most about 0.5 mm of side play, fitting it on the loose base before the print is glued. Glue the print (the whole letter page, untrimmed) with its left edge 81.4 mm from the end face and its title edge 107.2 mm from the centre line toward the camera wall, which puts grid column line 0 at 101.1 mm and row line 0 at 89.2 mm (the design values below), and a blank sheet on the underside.

Measure the real offsets and put them in `config/board_in_E.json` (start from `config/board_in_E.template.json`):

| Field | What | Design | This study, measured |
|---|---|---|---|
| `d_x_mm` | tongue end face to grid column line 0 | 101.1 | 102.3 ± 0.8 |
| `d_y_mm` | key centre line to grid row line 0, toward the camera wall | 89.2 | 90.36 ± 0.4 |
| `h_K_mm` | board top above the surface the robot stands on | | 10.0 ± 1.0 |
| `yaw_deg` | turn of the end face against the grid | 0 | -0.145 ± 0.12 |

Seat it before every reading: end face on both lobes, key in the gap; a 0.1 mm paper strip must not slide into the joint at either lobe. After step 3, `$P tools/sled_from_views.py --views media/calib/intrinsics/A/*.png --out results/rig/sled_from_views --square-mm SQ --t-mm T` (T = carrier thickness) reads `d_x`, `d_y` and the yaw from the calibration photos as a check. Without a sled, the template's `mat` method places the board flat on the mat instead.

**3. Calibrate the lens.**
```bash
$P calib/intrinsics_capture.py --set A --square-mm SQ    # SPACE saves a view, u undoes, q quits
$P calib/intrinsics_capture.py --set B --square-mm SQ    # a second, independent set, board turned 90°
$P calib/intrinsics_solve.py --square-mm SQ --sets A B --print-x-mm X1 X2 --print-y-mm Y1 Y2
```
The capture shows its coverage live: per set, at least 45 views (30 kept), all 9 cells of a 3 x 3 grid, each image corner reached within 40 px in at least 3 views, at least 12 tilted views. Good: the solve ends `INTRINSICS PASS` (exit 0): RMS ≤ 0.30 px, σ(fx), σ(fy) ≤ 0.2 %, hold-out RMS ≤ 0.40 px, the two sets' fx within 0.5 %. It writes `config/c920_intrinsics.json`.

**4. Measure the camera pose.** Five placements, re-seating the sled between them:
```bash
$P calib/pose.py measure --tag s1_p1 --square-mm SQ      # then s1_p2 ... s1_p5
$P calib/pose.py mean --tags s1_p1 s1_p2 s1_p3 s1_p4 s1_p5 --out s1
```
Good: each reprojection RMS ≤ 0.30 px (otherwise the tool says REDO), and the spread over the placements within 0.5 mm and 0.3° (printed by `mean`). The pose is written to `results/poses/<tag>.json` in the simulation frame: lens centre, rotation, depression (tilt), heading and roll. `$P calib/pose.py diff s1 other` compares two saved poses.

**5. Compare with the simulated camera.**
```bash
$P calib/pose.py hud --target s1 --square-mm SQ [--ghost]
$P calib/overlay.py --intrinsics config/c920_intrinsics.json    # e edges, b blend, +/- amount, s save, q quit
```
The HUD's target is the simulation's render camera (`results/c1/frames_sim.json`, every randomization at its centre); it shows six errors (measured minus target: depth, lateral, height, tilt, pan, roll) and the move that removes each. The overlay draws the simulated scene's edges on the undistorted live view. To run the policy in simulation at the measured pose, as the study's `S1_measured_c920` cell: `$P sim/make_s1_cell.py --pose results/poses/s1.json --out results/h4/cells_s1.csv`, then, with the policy server up, `python3 -I sim/run_queue.py run --cells results/h4/cells_s1.csv`.

**6. Adjust with the live HUD.** With `hud --target s1` running, loosen the mount, move the camera until all six errors are green, tighten, and read again after tightening. Good: within 3 mm per axis and 0.5° per angle (aim ≤ 0.3°); `--tol-mm` and `--tol-deg` change the band. To set an offset from a saved pose: `$P calib/pose.py hud --base s1 --offset tilt_down_deg=6 --tol-mm 2 --tol-deg 0.3 --square-mm SQ` (keys `tilt_down_deg`, `pan_deg`, `roll_deg`, `depth_mm`, `lateral_mm`, `height_mm`).

**7. Check the mat and the rack.**
```bash
$P tools/scene_check.py --pose s1 --mat-width-mm W     # W = the real mat's width in mm (default 457.2)
```
It finds the mat's visible edges and the yellow rack in one front image and compares them with the simulation's, through the measured pose. Good: each mat edge within 3 mm and 0.3° (OK), the rack within 2 mm per axis and 1° (OK); otherwise it prints OFF and which way to push. `--target 0,30` checks a rack moved 3 cm toward the camera wall. It writes `results/rig/scene_check_last.json` and `.png`. The numbers are only as good as the sled measurement.

## Running trials

The study's trials ran with `real/trial_runner.py`, one row of `config/schedule.csv` (this study's 80 rows) per trial. Scored trials refuse any time cap, policy timeout, action horizon or instruction other than the pre-registered 60 s, 3 s, 16 and "Pick up the vial and place it in the yellow rack".

**Before a session:**
```bash
sim/run_server.sh                                     # the GR00T N1.6 server as container groot-server (checkpoint-10000)
.venv/bin/python -I sim/server_ping.py                # {"ok": true, ...}
python3 -I calib/usbcam.py register follower          # each arm plugged in alone; then: register leader
real/run_real.sh python /workspace/gtc/real/robot_health.py --role follower    # read-only, no torque; exit 0 = PASS
real/calibrate_arm.sh follower                        # the course's calibration and check, "Overall: ✓ PASS"; then: leader
```

**Per block:**
1. Rack: rough position with the L-jig, then a live view until it is in place: `$P calib/rack_view.py --target N` (N, X3 or Y3, against the L-jig targets) or `$P calib/rack_ref_view.py --ref <reference> --pose s1` (against a block reference at a measured camera pose).
2. Reference, with the light at trial level, the rack at the condition pose, no vials, the arm at rest and the door closed: `$P real/trial_runner.py reference --tag <block>_<cond> --draw` (drag a box over the vial zone, Enter; over the arm, Enter; Esc). For another condition at the same camera pose, `--ignore-from <tag>` instead of `--draw`. Check `media/real/refs/<tag>/ref_check.png`.
3. Tubes: print the layout's stencil from `stencils/` at 100 % (its CHECK FIRST line must measure 100.0 mm) and follow the steps printed on it; take the stencil out, then `$P calib/vial_view.py --layout L01 --ref <reference> --pose s1` and slide each tube until all three pass.

**Each trial:**
```bash
real/run_real.sh python /workspace/gtc/real/trial_runner.py next             # the next scheduled row
real/run_real.sh python /workspace/gtc/real/trial_runner.py run --uid N04-003  # one row, or the re-run of an invalid
real/run_real.sh python /workspace/gtc/real/trial_runner.py run --pilot P01 --cond R1 --layout L00   # unscored
.venv/bin/python -I real/trial_runner.py status                               # progress and open invalids
```
Three Enters: preflight (devices by USB identity, camera lock, server ping, the clean-view, light, drift, rack and vial checks against the reference and the measured pose `--pose`), connect (the arm rises to the course's start pose), policy. Keys during the run: `s` success seen, `f` safety stop, `i` invalid, `q` or space stop. A trial also ends at the 60 s cap or when the policy does not reply within 3 s. Then a score form (Enter takes the value in brackets); `trial_runner.py score --uid <uid>` finishes a form left open. Each attempt adds a record to `results/real/trials.jsonl` and `trials.csv`, a per-chunk log to `results/real/steps/`, and frames and videos to `media/real/trials/<uid>_a<n>/`.

**Safety.** The arm moves only after an Enter (`--yes` is refused without `--mock-robot`). `f` is the safety-stop key. Never press Ctrl+C twice: a second interrupt aborts the move home. The hard stop is the robot's 12 V plug: keep it within reach, and keep a hand on the arm at the first connect of each arm (torque comes on before the goal is set to the current position). Every trial ends with the course's disconnect: home pose, torque off.

**Dry run without the robot:** `tests/run_trial_dryrun.sh` runs the runner in the real-robot container against a mock policy server, with a mock arm and replayed simulation renders; it opens no camera or serial device and ends with `TRIAL DRY RUN PASS`.

**Blind scoring:**
```bash
$P tools/cut_judge_clips.py --block <block> --video <judge video>    # one clip per trial
$P tools/blind_rename.py --blocks <block> [<block> ...] --batch A     # coded copies, sealed key, its SHA-256, a scoring sheet
```
Commit the key's SHA-256 before scoring, fill in the sheet `results/real/blind_scores_<batch>_<utc>.csv` without opening the key, then run the analysis below.

## Reproducing the analysis and the poster numbers

`poster/numbers.json` lists every number on the poster with its value, k/n and 95 % interval where it is a rate, the method, and the source files (paths relative to `~/gtc2027`). From `~/gtc2027/gtc`, with the layout above:
```bash
.venv/bin/python -I analysis/thresholds.py        # results/analysis/thresholds_v1.json and .md, from results/sim/
.venv/bin/python -I tests/test_analysis.py         # the statistics against brute force and v1's power numbers
```
The thresholds come out identical to the committed files.

The blind-score analysis reads the keys and the v2 analysis code from the paths of the study's working copy, so place them there first (the files are identical):
```bash
mkdir -p media/real/judge/sealed release/prereg_v2
cp results/real/blind_key_?_20261110T064043Z.json media/real/judge/sealed/
ln -s ../../analysis release/prereg_v2/analysis
.venv/bin/python -I analysis/blind_results.py --out results/analysis/real_blind_check
```
The output matches `results/analysis/real_blind_v1.json` and `real_blind_v1_rows.jsonl` except the release times from the policy start of the 8 successful trials scored from phone clips, and the summary built on them: those need the clip-cutting logs, which stay private (below).

To rerun simulation cells, start the policy server and run `python3 -I sim/run_queue.py run --cells config/cells_sweep_v1.csv` (one JSON line per episode in `results/sim/<cell>.jsonl`; `status`, `pause`, `resume` and `stop` control it). `tests/` has the other unit tests (`.venv/bin/python -I tests/test_<name>.py`).

## Pre-registration

- `PREREGISTRATION_v1.md`: hypotheses, designs and analysis plan, with the sweep cells (`sweep_cells_v1.csv`, md5 `c8d81d681277c9119c4c3f2e96b075ae`) and the sweep code. Tag and GitHub release `prereg-v1`, October 24, 2026.
- `PREREGISTRATION_v2.md`: the items v1 left to v2, the analysis code and the simulated thresholds. Tag and GitHub release `prereg-v2`, November 6, 2026, before the first scored real-robot trial.
- `PREREGISTRATION_v2_addendum.md`, entries 1-4, each a timestamped commit before the step it governs: `392d4bf` (entry 1, November 6, before the first R0 trial; tag `prereg-v2-addendum-1`), `af1c5a2` (entry 2, November 8, before the first R1 trial), `6d49b42` (entry 3, November 9, before the rack block; it records the SHA-256 of the frozen E3), `74a7833` (entry 4, after the last trial, before blind scoring).
- Deviations: v1 section 7, v2 section 6 and `results/real/deviations.md`.

The tags hold the registered files; `git show prereg-v1:sim/run_sim.sh`, for example. The sweep ran from a working copy whose code and configuration files are byte-identical to `prereg-v1`. On `main`, 16 of those files now hold their later versions (license notices, provenance in each result row, `docker run --init`, offline by default, the read-only E3 mount, repo-relative paths, a second seed format in `map_sweep_cells.py`, input files found inside the repository, the exploratory queue setup). The trial records, scores, analysis outputs and code were added after the poster was submitted, from the study's private working repositories; `notes/gtc_file_map.md` lists each file with its source commit and SHA-256, and the few lines edited for this copy.

What stays private: the photos of the real room (the trial frames and the phone and judge videos that show it), for privacy, and the clip-cutting logs, whose video metadata holds the phone's location. Of the sources `poster/numbers.json` cites, only room photos are private.

## License and citation

Apache-2.0 (`LICENSE`), Copyright 2026 Binary Core LLC. `NOTICE` lists the files derived from NVIDIA's "Sim-to-Real-SO-101-Workshop" (Apache-2.0); they keep NVIDIA's copyright and license notices.

NVIDIA, Isaac, GR00T, Cosmos and GTC are trademarks of NVIDIA Corporation. This project is independent and is not affiliated with or endorsed by NVIDIA.

To cite:

> Arturo Morales Rangel (Binary Core LLC). *How Far Can a Real SO-101 Setup Drift Before a Sim-Trained GR00T Policy Fails?* Poster submitted to NVIDIA GTC 2027. https://github.com/binary-core-llc/so101-sim2real-drift
