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
