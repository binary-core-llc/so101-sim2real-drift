# Pre-registration v2 addendum

This file holds the items fixed after the `prereg-v2` release (GitHub release published 2026-11-06T17:18:39Z). Each entry is a new commit with its UTC time. It is made before the step that uses it and before any data it applies to. Item numbers follow `PREREGISTRATION_v2.md`. No earlier commit or tag is changed.

## Entry 1: before the first R0 trial (November 6, 2026)

### 8b. Trial runner checks: numeric thresholds

Every check compares the pre-trial front frame with the block's reference. The reference is the median of 20 frames of the clean scene: rack at the condition pose, no tubes, arm at rest, door closed, light at level. It also stores each pixel's noise SD and ignore zones over the tube area and the arm area. If a check fails, the trial does not start (I0, not a trial): the scene is fixed and the checks run again.

| Check | Rule |
|---|---|
| Clean view | A pixel counts as changed if its difference exceeds max(6 × its noise SD, 25 grey levels). After a 5 px opening, any changed region of ≥ 150 px outside the ignore zones fails. |
| Light | Mean level over the same pixels within ±5 % of the reference. |
| Camera drift | Largest displacement of a grid of image points under the image warp fitted on the static scene: ≤ max(1.5 px, 3 × the reference's frame-to-frame SD). |
| Rack pose | Largest yellow region (HSV hue 20-38, saturation ≥ 90, value ≥ 90, at least 300 px): centroid within 2.0 px and rotation within 1.0° of the reference. |
| Mat (new) | The three mat edges visible in the front view (back, front, far). Each is fitted as a line through the strongest mat/floor step on each scan line. Each line must lie within 1.5 px of the reference's line at two places. An edge that cannot be found fails. The same measure is computed on every trial's end frame and recorded; it does not change the score. |
| Tubes | Item 8c. |

During the trial:
- **Stop (3 s watchdog):** no policy reply within 3 s ends the trial, I3.
- **Auto-flags:** a chunk latency above 1 s gives I3. Three or more identical consecutive keyframes give I1. A changed camera setting, read back before and after each trial, gives I4. A served model path other than the registered one gives I6.
- **Cap:** 60 s from the first policy query.

**Shakedown values** (unscored, November 6):
- **Pilot V28-01 at R0:** changed pixels 0, light ratio 1.0005, drift 0.13 px (limit 1.5 px), rack 0.11 px and −0.02°, mat 0.09 px.
- **Mock runs** (no robot moved): the cap ended a run at 60.09 s. With the policy server paused, the watchdog ended a run (no reply within 3 s), flagged I3.

**Why the mat check:** in V28-01 the gripper reached the mat's far edge between 9.4 s and 10.1 s and turned the mat by about 1.5-2 cm at its far corner. Most of the mat's edges lie inside the other checks' ignore zones. The mat is now also held with extra tape loops. It is aligned with a live camera view of its edges against the block reference, and the pre-trial check holds each edge within 1.5 px of it.

### 8c. Tube placement check: centroid tolerance

For each tube, the centroid of the observed tube mask must lie within **4.0 px** of the centroid of its projected target. This is in addition to IoU ≥ 0.7 (per tube and combined) and the cap rule (≥ 50 %).

**Basis:**
- **Image noise:** at R0, the observed tube centroids vary by at most 0.21 px SD from frame to frame. The largest deviation was 0.59 px (15 frames, three tubes, V28-01). The 4 px leaves the rest for stencil placement and projection error.
- **Rendered test frames:** a tube moved 5 mm sideways gives 2.7 px (pass). A tube moved 10 mm along its axis gives 8.9 px (fail); IoU alone passes that case, at 0.80.

The other image settings are as in our code:
- tube mask: difference above max(6 × noise SD, 20 levels), a 30 px search band around each target, a 7 px closing, regions of at least 60 px;
- cap colour: HSV hue 95-130, saturation ≥ 80, value ≥ 50, at least 30 px.

### D15. Rack placement

After the mat was re-laid on November 6, plate N no longer put the rack within the fit test's 2 mm rule (+3.8 mm and −3.7 mm). The rack is now placed in two steps:
- **Rough placement:** the plate.
- **Final placement:** a live camera view against the fit-test targets, using the fit test's own measure. Both faces must be within 1 mm; the 2 mm rule is unchanged.

The R0 reference was taken with the rack at −0.2 mm (front face) and −0.6 mm (right face) from target N.

### R0: the course setup as written

R0 is the course setup as written:
- **Camera** placed per the course's written page (v2 rows D3 and D12).
- **Arm** calibrated with the course's procedure: LeRobot calibration as on course page 07. The course's calibration check passed except for a WARN on wrist_flex (v2 row V21).
- **Rack, mat, tubes, light and door** as in R1.

R0 runs with the arm as calibrated.

**Recorded difference (nothing changed):**
- **Sim side:** the course converts the policy's joint values (−100 to 100; gripper 0 to 100) to simulated joint angles over fixed ranges (`source/sim_to_real_so101/utils/lerobot_interface.py`, lines 47-54).
- **Real side:** on a real arm, the same values span that arm's calibrated range.

| Joint | Simulated range | Our arm, calibrated | Course statistics, 15 arms (`docker/real/scripts/calibration_stats.json`) |
|---|---|---|---|
| shoulder_pan | 220° | 237.7° | 239.5° |
| shoulder_lift | 200° | 206.5° | 206.5° |
| elbow_flex | 190° | 194.2° | 195.3° |
| wrist_flex | 190° | 199.9° | 204.7° |
| wrist_roll | 320° | 335.3° | 353.9° |
| gripper | 110° | 126.2° | 129.7° |

**What the shakedown showed:**
- At R0 the arm first turned toward the tube nearest the mat's right edge. The simulated arm does the same at this layout. The real arm did not reach the tube.
- The simulated arm, set to the real run's joint values, does reach it.
- At one held pose, the simulated and real jaw heights agree within about 5 mm (the real height judged by eye). In the wrist view, the real gripper sits further toward the mat's right edge.

**Before R1:** the arm is measured with the cameras in the C4 step. Then we choose and register here, before R1, one of two options for R1-R9:
- the course's conversion as is;
- a per-joint correction of the joint values in our trial runner.

Neither option changes the course code or the model.

## Still to come

| Item | Needed before |
|---|---|
| Arm: the course's conversion as is, or a per-joint correction (with the measured values) | R1 |
| 3. H4 result and the real nominal camera placement | S0 → S1 |
| 6. R3 sign | the rack block |
| 8. Final real schedule and its SHA-256 | R1 |
| 2b. E1 variant and prompt | E1 sees any real photo |
| 11. E3 archive SHA-256 | the first scored photo |
| 5. Any time cut from v1's order | the trials it removes |

## Entry 2: before the first R1 trial (November 8, 2026)

### 3. H4 result and the real nominal camera placement

The C920's measured focal length is fx = 630.62 px, 22.5 % above the simulated 514.7 px, so the H4 cells were run.
- **H4_c920_measured** (simulation with the C920's measured intrinsics at the sim camera pose): 148/200 (0.740; Wilson
  95 % 0.675-0.796), against S0 124/200 (0.620; 0.551-0.684). Fisher two-sided p = 0.0135.
- **Image-matched cell: not run.** The pose that best matches the simulated image puts the lens 7.4 mm past the camera
  wall's inner face and 6.0 mm above the roof's inner face. The real camera cannot be placed there.
- **Real nominal placement (S1): pose-matched**, by v1 section 6.
- For these inputs the released `analysis/real.py` prints "undecided ... the image-matched cell is needed"; this entry
  states the placement.
- **Timing:** entry 1 listed this item as due before S0 → S1. It is published here, after S1 was set on November 8,
  because this entry was held for the arm item. S1 was set by this item's rule (pose-matched).
- **S1 as set: outside E row 22, accepted at its measured pose.** S1 was set toward the sim's render point with the
  sled HUD. By hand it could not be brought inside E row 22 (3 mm, 0.5°), and it was accepted with the angles within
  about 1° and the positions about 13-15 mm off.
  - **Measured S1** (X2: 5 sled seatings, RMS 0.153-0.177 px, 35 corners each; spread SD 0.41 / 0.14 / 0.16 mm and
    heading 0.09°, inside B 4.2): lens C_E (0.1526, 0.3437, 0.4757) m, 55.00° down, heading −81.58°, roll +1.94°.
  - **S1 minus the sim render point** (B 1.3): depth +15.0 mm (toward the back wall), lateral +14.0 mm (toward the
    camera wall), height −12.9 mm, tilt down +0.73°, pan −0.38°, roll +0.35°.
  - **In all:** 24.2 mm between the two lens centres, and 1.01°, the angle of the single rotation between the two
    camera orientations. The three angles above give about 0.89° by root-sum-square. They are not rotations about one
    fixed set of axes, so the two figures differ.
  - Every real condition is set from the measured S1 (R4 and R5 by `hud --base s1`; the rack and tube checks and E3's
    reference photo at S1), so the comparisons among the real conditions are not affected.
- **New sim cell S1_measured_c920**, registered here before R1: the simulation at the measured S1 pose with the
  C920's measured focal (2.364812 mm, as in H4_c920_measured). The camera-mount offsets reproduce the measured pose
  exactly. 200 episodes, seeds as in S0 (`sim/make_s1_cell.py`; `results/h4/cells_s1.csv`, SHA-256
  f7b45987e7f0a7d72c751cc6e07f122c06954800417a2aeaa7020eb2fbea6165).
  - It is the simulated comparator for R1, the real nominal.
  - Also reported: S1_measured_c920 against H4_c920_measured (Fisher two-sided), the effect of the pose offset alone
    in the simulation.
  - It runs after the last real trial of November 8 (it shares the GPU with the policy server). H4 is unchanged.

### R0 repeated (N04B-R0)

R0 (N04-R0, 10 scored trials) ran with the mat about 18-19 mm toward the camera wall and about 9 mm farther from the
robot than the simulation. The rack and tubes were placed from the mat, so they were offset too. This was found after
the block, by the deferred tube check and by ruler from the robot's base.
- **The re-run was decided, and its 10 schedule rows committed (gtc 0d386f7, Nov 8 05:33 UTC), before any N04B-R0
  trial ran** (the first, N04B-001, started 06:33 UTC).
- **Mat:** re-placed from the robot's base with a steel ruler.
  - In front of the robot it sits within about 1 mm of its simulated position.
  - It is turned 0.6° against the seated board (ruler, ± 0.25°). At the far ends the camera reads its edges up to about
    7-9 mm from their simulated positions.
  - The camera reads the mat's edges turned 1.2-1.5°, against the ruler's 0.6°. That 0.4-1.1° difference is
    unresolved. Both readings are taken against the seated board, so the sled's link to the robot is not part of the
    difference. S1 is placed by the sled HUD, as planned.
- **Rack:** placed from the robot with the camera. Its final position by `tools/scene_check.py`: −1.0 mm in E x,
  +1.7 mm in E y.
- R0 was run again as **N04B-R0**: 10 trials, the same layouts in the same order, the camera untouched.
- **N04B-R0 is the R0 result.** N04-R0 stays on record as "R0 with the scene offset" and is not pooled.
- Results (live scores): N04-R0 1/10, N04B-R0 1/10 (Wilson 0.018-0.404 each).
- **Record edits:** N04B-001 (`regrasp_n=3` added at the operator's request) and N04B-002 (record rebuilt from disk
  after an interrupted score form) are listed in `results/real/deviations.md`, with audit copies.

### Judge video for the R0 blocks

- **No phone video exists for N04-R0 or for N04B-001 to N04B-003.** N04B-004 to N04B-010 each have their own
  recording, one per trial (`results/real/deviations.md`).
- **No trial is re-run.** Those trials keep their live scores.
- **Their blind scoring**, including the exploratory `tube_contact` measure, uses the runner's saved front and wrist
  camera frames instead of a phone clip, under the same blind codes, marked "scored from robot frames". The front
  frames show the R0 camera view, so for these trials the scorer can tell the condition.
- If those frames cannot show the outcome or a tube contact for a trial, that trial is reported as missing for that
  item.

### 8c. Tube placement check: method

**Finding.** On the 10 N04B-R0 pre-trial frames the projected targets sit on the real tubes, yet the registered rule
(IoU ≥ 0.7 per tube and combined, centroid within 4.0 px) passes 0 of 10:
- where two tubes touch in the image, they form one changed region, which goes whole to one target (4 of 10);
- one tube's changed region is 20-40 % larger than its silhouette (shading on the mat). This caps the IoU near
  0.75-0.8 even for an exact placement, and pulls the region's centroid off.

**New method, from R1 on:**
1. Each changed pixel (thresholds as in entry 1) goes to the nearest projected tube silhouette, so touching tubes are
   split where they meet.
2. For each tube, the image shift that best overlaps its silhouette with its pixels gives the tube's offset. The offset
   is converted to mm on the mat, across and along the tube's axis.
3. **A tube passes** when:
   - it is within **7.5 mm across and 7.5 mm along** its target;
   - at least 85 % of the shifted silhouette is covered;
   - the cap rule of entry 1 holds (≥ 50 % of the cap blue on the projected cap).
4. IoU is still recorded but no longer decides. Each trial records every tube's offset in mm.

The limits keep entry 1's two stated examples: a tube 5 mm sideways passes, and a tube 10 mm along its axis fails.
The 7.5 mm limits were chosen after the validation results below were known.

**Validation** (`tools/vial_check_validate.py`, saved frames, nothing written to the trial records):

| Case | n | Registered rule passes | New rule passes |
|---|---|---|---|
| N04B-R0 as placed | 10 | 0 | 7 |
| The same frames checked as the next layout | 10 | 0 | 0 |
| One tube removed (pixels from the tube-free reference) | 10 | 0 | 0 |
| N04-R0 (mat offset) | 11 | 0 | 0 |

- **Measurement check:** a tube moved 3, 6, 10 or 15 mm across its axis (synthetic) is measured as +3.1, +6.4, +10.4 and
  +15.5 mm (SD ≤ 1.0 mm, n = 10 each).
- **Measured placement in N04B-R0:** across +2.6 ± 4.3 mm, along +2.5 ± 3.1 mm (30 tubes).
- **Considered and not chosen:** 10 mm across and along (the simulation's ±10 mm tube randomization across the tube)
  passes 8 of 10, but it lets a 10 mm along-axis offset pass, which entry 1's example fails.
- **R0 blocks:** they keep the registered check's results, as recorded. Under the new method, N04B-R0 is recorded as
  "7 of 10 within limits".
- **Fallback if this item is not published before R1:** R1 runs with `--checks warn`. The registered check is then
  computed and recorded but does not block the start.

### Arm conversion

Entry 1 left this open: the course's conversion as is, or a per-joint correction in our runner.
- **Both R0 blocks show the same failure:** in 18 of the 18 failed trials the arm turned right until it touched the
  wall or door.
- **Pose check at S1** (Nov 8; three poses from the sim's L00 trace: above vial 3, the lower approach, the grasp; no
  vials placed):
  - The real arm reached the commanded joint values within 0.7 units, except the elbow, which stopped 1.7-2.8 units
    short each time.
  - At the reached values, the real wrist and gripper sit about 20-33 mm from where the course USD puts them, seen
    through the front camera at S1. This is the image shift that lines the sim's silhouette up with the real arm,
    converted at the gripper's depth. The overlap after the shift is 0.38-0.54, with the gripper partly out of view,
    so the figures are an indication. The Nov 6 check at R0 gave about 24 mm.
  - With the sim arm at the real calibrated joint ranges (entry 1's table), the offset along the reach halves (about
    20 to about 10 mm); the rest does not follow any single joint.
- **Decision: the course's conversion, as is.** The check points to no single per-joint correction, and the study
  asks how the course's pipeline, as shipped, tolerates drift. D1 applies to G1 as registered.

### 5 and 8. Time cuts and the final real schedule

- **Measured cycle:** 5.0 min per trial in N04B-R0 at steady state (N04-R0: 6.85).
- **Slip rule applied on Nov 8 at 09:30:** from then, the remaining plan with K2-K4 was about 145 min over the
  remaining window (Sunday and Monday morning, 60 min margin per day) at the measured 5.0 min per trial. The R3 and R5
  trials run before the 20:00 check, so K5 is applied now.
- **Cuts applied, in C's registered order: K2-K5.**
  - **K2:** reserve 15 → 10.
  - **K3 and K4:** no E1 closed-loop trials (R8 and R9 removed, 24 trials). E1 is judged on photos only (H3b), as K4
    states.
  - **K5:** R3 and R5 12 → 8 each. Rows removed by a fixed rule: the last 4 R3 rows in `uid` order (N05-021, N05-025,
    N05-028, N05-029) and the last R5 camera block (N06-CAM6: N06-026 to N06-029).
- **The slip rule continues as registered.** Further cuts follow C's order (K6: R6/R7 3 × 4 → 2 × 5; then K7 onward)
  and are published before the trials they remove. The next check is Sunday 20:00.
- **Block order:** the M1 cycles (N05-M1C1-E3, N05-M1C2-E3) run after the camera blocks, so that E3 is frozen after
  its camera-mode check on the camera blocks' photos. The slip rule allows whole blocks to move later.
- **Final schedule:** `config/schedule.csv` (gtc 42d5dff), 109 rows, SHA-256
  f927ef48d0a043cd7ad96629b686e653ab4712f183efceeffdfb91cce8561915. It is the schedule of entry 1 with N04B-R0 added
  after N04-R0 (0d386f7), the 24 R8/R9 rows removed (128cec8) and the 8 K5 rows removed (42d5dff).

### 6. R3 sign

**R3 is x+3**, by reach only (v1 section 5). In the V25 reach test (teleop, November 8, the rack at x+3 by the L-jig's
X3 stops), the gripper brought an upright tube over the openings of both far slots. One far slot is at the edge of
reach: there the tube went only about halfway down.

### 2b. E1 variant and prompt

E1 is Cosmos-Reason2-2B (v2 item 2), run locally at revision 9ce19a19 in BF16 (transformers 4.57.1, torch 2.8.0), with
the checkpoint's generation settings (sampling, seed 0 per photo) and max_new_tokens 4096.
- **Input:** image A, the simulation's view at the nominal pose rendered with the C920's measured focal (630.62 px),
  and image B, the photo.
- **Prompt:** a scene description, the physical sign definitions (B 1.3 terms and the box's walls), and a JSON answer
  inside `<answer>`. The full text is in `e1/e1_estimate.py` (gtc commit a294ec3).
- **Variants:**
  - v1: metric deltas;
  - v2: per quantity a direction and a size bin (small / medium / large), scored at the bin centres;
  - v1b and v2b (round 2): the same answers, asked with typed placeholders instead of an example answer, plus one
    sentence on what to compare (the rack, the mat's edges, the box's walls and corners).
- **Parser:**
  - takes the last `<answer>`, else the first balanced `{...}` after the reasoning;
  - strips code fences;
  - repairs nothing beyond trailing commas;
  - reads a quantity left out as 0 ("no change") and records it;
  - a failure counts as "no correction".
- **Selection, on simulated scenes only:** 25 scenes of the course scene with the C920's focal:
  - the nominal;
  - 12 camera mis-setups up to 6° and 20 mm, single and combined;
  - 12 rack mis-setups up to 30 mm and 15°.

  The rule, committed before any result was read (`e1/eval_selection.py`, gtc a294ec3): the lower median of the
  error over all nine quantities, each scaled by the planned mis-setup size (6°, 30 mm, 15°); a tie goes to v1.
- **Round 1 (v1, v2):** v1 median 1.00 (7 of 25 answers not parseable), v2 median 0.67. v2 answered "nothing moved"
  in all 25 scenes, so its error equals "no correction" (median 0.67). v1 mostly repeated the example answer's zeros.
- **Round 2 (v1b, v2b):** added because both round 1 variants mostly copied the example answer. The candidates and the
  rule (lowest median of v1, v2, v1b, v2b; a tie goes to the earlier) were committed before the round 2 runs (gtc
  ca77e84). v1b median 2.90 (it gives numbers, but they are wrong: worse than no correction); v2b median 0.67 (19 of
  25 answers not usable).
- **Chosen: v2** (median 0.67, tie with v2b, v2 is earlier). On the simulated scenes no variant does better than no
  correction. E1 enters the real photos as registered, with v2.
- All runs and the per-scene errors: `results/e1/selection_runs/`, `results/e1/selection_eval.json`
  (round 1 alone: `selection_eval_round1.json`).

### E3 implementation (transparency)

E3 is the GPU render-and-compare of v1 H3a/H3b. It is built as D C12 specifies in its objective and search:
- **Objective:** class-weighted soft IoU over white (floor and walls), mat and rack, plus an edge chamfer.
- **Search:** the cross-entropy method, population 64, 15 iterations per level, coarse to fine (160 × 120, then
  320 × 240), fixed seed.

It differs from D's design in two details:
- **Renderer:** E3 renders the course scene (from the C1 dump and the course USD meshes) with our own z-buffer in CUDA
  PyTorch, not Isaac Lab's TiledCamera. A CPU twin gives identical class images.
- **Camera estimates are differential:** E3 is run on the nominal reference photo and on the photo, and reports the
  change between them. On the N04B-R0 reference the absolute camera estimate differs from the board-measured pose by
  tilt −0.8°, pan −1.2°, depth +5 mm and height −7 mm. The real scene differs from the simulation (for one, the mat
  is turned 0.6°), and that difference is the same in both photos of a cycle.

E3 was developed on simulated scenes, R0 frames and the DEV photos only (no hypothesis grades them).
- On the 25 simulated E1 selection scenes it estimates the 12 camera changes within 0.5° and 1.7 mm, and 11 of the 12
  rack changes within 0.5 mm and 0.2° (the 12th: 4.4 mm).
- **These figures are not held-out:** the same 25 scenes were used during development (they showed a segmentation
  error, which was then fixed).

### Exploratory measure: gripper contact with a tube

Registered now, before any blind scoring has started.
- **Per trial,** scored blind from the judge clip, with the success score and under the same blind codes:
  `tube_contact` = none / touched / closed.
  - none: the gripper never touches a tube;
  - touched: it touches or pushes a tube without closing on it;
  - closed: its jaws close with a tube between them, lifted or not.
- C's F1 sub-flags cover failed grasps only; this measure is scored on every trial.
- **Reported** for N04-R0, N04B-R0 and every later block.
- **Exploratory:** it tests no hypothesis and is labeled exploratory wherever it is reported.

## Still to come

| Item | Needed before |
|---|---|
| 11. E3 archive SHA-256 (entry 3) | the first scored photo |
| Further cuts (K6 onward), by the slip rule | the trials they remove |
