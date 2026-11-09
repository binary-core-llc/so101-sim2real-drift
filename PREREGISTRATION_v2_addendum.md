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

## Entry 3: before the rack block and the first E3 cycle (November 9, 2026)

### G1 and D1

- **G1** (N04-G1, R1 at S1, 10 trials, November 8 23:36 to November 9 01:45 PST): 4 of 10 successes by the live score
  (N04-012, N04-017, N04-018, N04-019). **D1 (3 or fewer) does not apply.** Blind scores follow with the rest.
- Every G1 trial that started is in the record: 10 started, 10 records, each attempt 1; none was repeated or dropped.
  The 19 prestart aborts (I0, not trials; `results/real/prestart.jsonl`) all stopped before launch, among them the
  re-try before N04-017 (tube check: vial_2 8.6 mm across).

### 5 and 8. Slip rule, November 9 00:10 PST: K6, K7 and K8

- **Window:** blind scoring needs at least 12 h after each trial of the last trial day (v2 item 10). For the analysis
  and the poster to be submitted before Tuesday November 10, 17:00 PT, blind scoring starts Tuesday 07:00, so the
  trials end Monday 20:30 PST. Robot window from the check: about 830 min, 770 after C's 60 min daily margin. It
  assumed November 9, 00:10-01:30 PST (80 min, G1) and 07:00-20:30 PST less 60 min for meals (750 min).
- **Time per trial at S1:** 7 min nominal (5.0 min measured in N04B-R0, plus about 2 min to place the tubes and the rack
  with the live checks below), 10 min pessimistic (N04-012).
- **Remaining robot minutes** (87 rows, rack moves, camera setups, E3 cycles, the E3 freeze): about 1,320 nominal in
  entry 2's order; 1,144 with no returns to S1 and the set P photos after the last trial (below); 1,031 with K6;
  968 with K6 and K7; **756 with K6, K7 and K8** (fits). Pessimistic, 1,123 with K6-K8: over the window, so the stop
  rule below applies.
- **Cuts applied, in C's registered order: K6, K7, K8.** The cuts follow C's registered order and use no trial
  outcome; K6's row choice uses layouts only. K9 does not apply (R0 has run).
  - **K6 (R6/R7 3 × 4 → 2 × 5):** each method's cycle 3 is removed and two of its rows become the 5th trial of
    cycles 1 and 2. Rule: for cycle 1, then cycle 2, the first remaining cycle-3 row in uid order whose layout that
    cycle does not have yet (taking the first two rows as they are would repeat L08 in M2-C1). M1: N07-018 (L04) → C1,
    N07-019 (L02) → C2; N07-020 and N07-021 removed. M2: N07-005 (L00) → C1, N07-004 (L08) → C2; N07-006 and N07-007
    removed. H3a has 2 clusters per mis-setup.
  - **K7 (R1 25 → 20; R2 and R4 12 → 10):** the last rows in uid order, as for K5: R1 N07-001, -002, -003, -012, -013
    (the N07 controls); R2 N05-026, N05-027; R4 N06-024, N06-025.
  - **K8 (R3 and R5 → 0):** R3 N05-005, -006, -008, -009, -014, -017, -019, -020; R5 N06-008 to N06-015 (camera
    blocks CAM2 and CAM3). H1 reduces to "nominal vs outside".
- **Result:** C's minimum viable result: R1 20, R2 10, R4 10, R6 10, R7 10 (plus R0 and N04B-R0, 20).
- **Final schedule:** `config/schedule.csv`, 80 rows, SHA-256
  2cf3bebc5b0bca11f4921fa506e0aed57e8588dd8a298dfb023df6cf01f1e65a (gtc d71cb0f: K6-K8 in cd7649b, then the block
  move below; rows unchanged).

### Block order (replaces entry 2's block-order line)

- **Run order** = the order of `schedule.csv`: N05-C, N05-RACK, N05-M1C1-E3, N05-M1C2-E3, N06-C, N06-C2, N06-CAM1,
  N06-CAM4, N06-CAM5, N06-M2C1-E3, N06-M2C2-E3. N06-C2 (R1 × 2 at S1) moves as a whole block from between CAM1 and CAM4
  to right after N06-C, so the camera does not return to S1 between camera blocks.
- **Consequence:** the M1 cycles run before the camera blocks, so E3 is frozen (below) before its camera mode has been
  checked on the camera blocks' real photos. That check, against the board-measured camera change, is then made after
  the freeze and is reported as such.
- Entry 2 stated the M1 cycles after the camera blocks; the registered `schedule.csv` (f927ef48…) listed them right
  after N05-RACK. This entry sets the order.
- **Protecting the camera blocks** (decided November 9, 09:05 PST, before N05-001, on time only; no trial outcome is
  used). Checkpoint right after the last N05-RACK trial: from today's measured pace (launch to launch from N05-001,
  block times included), project whether every row of N06-CAM1, N06-CAM4 and N06-CAM5 would start by 20:30 in the
  current order. If yes, the order stays. If not, N05-M1C1-E3 and N05-M1C2-E3 move as whole blocks to the end, after
  N06-M2C2-E3, and the camera is returned to S1 before them if they are reached. `schedule.csv` is not changed before
  the checkpoint; the projection, and the new SHA-256 if the move applies, are recorded then.
  - Projection: pace = (the last N05-RACK launch − N05-001's launch) / (launches − 1), so the references and rack
    moves between them are included. Each later row is launched one pace after the one before it; each M1 cycle and
    each camera setup before a row adds the slip check's pessimistic time (40 and 45 min), since neither has been
    measured today; the meal time not yet taken is left out of the window.

### Stop rule

- **Monday's robot work started at 08:39 PST** (the follower health check,
  `results/robot/health_follower_2026-11-09T163930+0000.json`), not at 07:00.
- **Recomputed from 08:39** (G1 done; the E3 freeze done off the robot): window 08:39-20:30 less 60 min for meals,
  650 min; 590 after the margin. Remaining: 50 rows, 6 rack moves, 5 block references, 3 camera setups, 2 M1 and 2 M2
  cycles, and 30 min of morning checks, with the check's block times (nominal / pessimistic: rack move 5 / 8,
  reference 5 / 8, camera setup 25 / 45, M1 cycle 30 / 40, M2 cycle 55 / 90 min). **680 min at 7 min per trial;
  1,223 min at the pessimistic pace,** for which G1's measured pace is used, as it is slower than 10 min: 14.2 min per
  trial (N04-011's launch to N04-020's, 127.7 min over 9 intervals). Both are over the window; no further registered
  cut applies (K9 needs R0 not to have run), so the stop rule below decides.
- Trials not started by Monday November 9, 20:30 PST are not run. They are reported as not run, by row. By the
  recompute above, a row runs only if its trial starts (is launched) by 20:30. Launches are one cycle apart, a block's
  first launch comes one cycle after the block's setup, and the 60 min for meals are taken before. Rows that would not
  run:
  - order above, at 7 min per trial, 5 rows: N06-M2C2-E3 (N06-042 to N06-045, N07-004);
  - order above, at 14.2 min per trial, 20 rows: N06-CAM1 (N06-004 to N06-007), N06-CAM4 (N06-018 to N06-021),
    N06-CAM5 (N06-022, N06-023), N06-M2C1-E3 (N06-034 to N06-037, N07-005) and N06-M2C2-E3 (N06-042 to N06-045,
    N07-004);
  - moved order (the M1 cycles at the end, after a return to S1 counted as one camera setup: 705 and 1,268 min), at
    7 min per trial, 5 rows: N05-M1C2-E3 (N05-042 to N05-045, N07-019);
  - moved order, at 14.2 min per trial, 22 rows: N06-CAM5 (N06-022, N06-023), N06-M2C1-E3 (N06-034 to N06-037,
    N07-005), N06-M2C2-E3 (N06-042 to N06-045, N07-004), N05-M1C1-E3 (N05-030 to N05-033, N07-018) and N05-M1C2-E3
    (N05-042 to N05-045, N07-019).

### Blind scoring in two batches

- Batch A: the trials that ended before Monday 19:00 PST; batch B: the rest. Each batch gets its own shuffled blind
  codes and is scored at least 12 h after its last trial (A from Tuesday 07:00, B after A). Because the blocks run in
  a fixed order, a clip's batch also hints at its block: batch B holds the last blocks. As entry 2 states, the robot
  frames already show the condition for the trials scored from them.

### Set P photos

- The 34 set P photos (15 rack, 19 camera; H3b) are taken after the last trial. No policy runs then, so no blind delay
  applies (as for the photo set in v2).

### 11. E3 freeze

- **E3 frozen at** e3 commit 399025f998ea0114dd00c21f45e7ec937ed12589, archive
  `git archive --format=tar --prefix=e3/ 399025f998ea0114dd00c21f45e7ec937ed12589` (git 2.34.1), **SHA-256
  17fed03e9c82f4c9b05a70da541e23c3e0c4d536c1773de0857fa08395312291**, before the first M1 cycle photo. No E3 change
  after this point.
- **Light check before the freeze** (November 9, about 02:00 PST): the G1 reference taken at 13:25 PST in daytime light
  and re-taken at 23:12 PST in the night trial lighting show the same rack (scene_check: +0.3 / -0.7 mm between them,
  from the tubes lifted out next to it). E3 rack mode, rendered from the measured S1 pose (`results/poses/s1.json`),
  against the rack's nominal pose in the simulation (rack_delta: x, y in E and yaw about the rack's corner O):
  +3.27 / -1.36 mm, 1.63° (day) and +3.59 / -2.23 mm, 1.84° (night), a difference of +0.3 / -0.9 mm and +0.21°. E3
  camera mode, night photo against the day photo as reference: tilt 0.06°, pan 0.10°, roll 0.02°, positions within
  0.7 mm. No E3 change was made after the check.

### S1_measured_c920, run as registered in entry 2

- Run November 9, 01:49 to 03:07 PST, after the last G1 trial, 200/200 episodes (seeds 0-39 × 5, as S0), from gtc
  4aa8f69 with no local changes; `results/h4/cells_s1.csv` as registered (f7b45987…). Result: **99/200** (0.495;
  Wilson 0.426-0.564). Against H4_c920_measured (148/200, same focal at the sim render point), Fisher two-sided
  p 6.7e-7; against S0_nominal (124/200), p 0.016. All 101 failures ran to the 450-step limit; 99 of them had grasped
  the vial. `results/h4/s1_result.json`. It is the simulated comparator for R1, as registered; nothing else changes.

### Trial runner and placement since entry 2

Listed in `results/real/deviations.md` with numbers; all before the trials they affect.
- **Mat check (8b):** an edge whose search window lies wholly inside the reference's ignore zones is not used. At S1
  the far edge's window lies inside the arm zone and finds the wrist camera's cable, not the mat; the back and front
  edges are used, each within 1.5 px as registered. R0 references keep all three edges. From N04-011.
- **G1 reference** re-taken in the night trial lighting before the first G1 trial (the 13:25 copy, taken in daylight,
  failed the light and clean-view checks; the camera and rack had not moved). The top-right image corner (the door edge
  and a t-shirt outside the box, which change at every door re-seat) was added to the G1 reference's ignore zone from
  N04-012.
- **Placement aids** (not checks): `calib/vial_view.py` shows the runner's tube check live, per tube in mm with the
  slide that removes the offset; `calib/rack_ref_view.py` shows the runner's checks live, with the rack's outline
  against the block reference. The stencil sits on the mat. At S1 the camera reads the mat's front edge 6.7 mm off
  its simulated position at the front-right corner and turned 1.44° against E (`tools/scene_check.py --pose s1`, live
  front camera, November 8 23:09 PST: the edge fitted in the image and lifted to the mat's top plane with the measured
  S1 pose; `results/rig/scene_check_20261109T070945Z.json`). Entry 2 gives the ruler reading of the mat and its
  difference from the camera's. So stencil placement alone left the far tube up to about 8 mm off. The runner's
  checks, with the door on, decide as before.
- **Record edits:** listed in `deviations.md` (N04-018: flags added at the operator's request; the record as first
  written is kept).

## Still to come

| Item | Needed before |
|---|---|
| Blind scoring (batches A, B), kappa live vs blind, `tube_contact` | the analysis |
| Trials not run under the stop rule, if any | the analysis |
| E3 camera-mode check on the camera blocks' photos (after the freeze) | the analysis |
| Set P photos (H3b) | the analysis |
