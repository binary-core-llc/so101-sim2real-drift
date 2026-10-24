# Pre-registration v1: How far can a real setup drift before a sim-trained robot fails?

**Author:** Arturo Morales Rangel (Binary Core LLC)
**Version 1.** Written before the simulation sweep and before any scored real-robot trial. The date of record is the date of the GitHub release that contains this file. The release commit also pins the sweep cell list (`sweep_cells_v1.csv`), the sweep code (including `overrides.py`) and the measured sign table (`sign_table.json`).
**Version 2** will be released before the first scored real trial (planned November 2, 2026). It adds the items listed in section 8 and the analysis code. Every deviation from this document will be reported.

## 1. Question and fixed system

Question: with NVIDIA's official SO-101 sim-to-real course policy, does the training randomization range predict how far a real setup can drift before the policy fails? When the setup is outside that range, does one photo suffice to correct it?

Fixed for every simulated and real run:

| Item | Value |
|---|---|
| Course | "Train an SO-101 Robot From Sim-to-Real With NVIDIA Isaac"; repo `isaac-sim/Sim-to-Real-SO-101-Workshop` at commit `ce807d9` |
| Policy | GR00T N1.6, `aravindhs-NV/grootn16-finetune_sreetz-so101_teleop_vials_rack_left`, `checkpoint-10000` (sim-only), Hugging Face revision `7efab50d`. The course reports it was trained on 75 simulated demonstrations. |
| Policy server | Isaac-GR00T at `ead52833` (the course's `GROOT_REF`), action horizon 16 |
| Instruction | "Pick up the vial and place it in the yellow rack" |
| Simulator | The course's simulation image built on `nvcr.io/nvidia/isaac-lab:2.3.2` (reports Isaac Sim 5.1.0-rc.19; local image ID `sha256:c84df9ea067f`), task `Lerobot-So101-Teleop-Vials-To-Rack-Eval` |
| Hardware | One NVIDIA RTX A4500 (20 GB), driver 580.65.06 |
| Real robot | SO-101 follower and leader (WowRobo, orange, assembled), the kit's wrist camera, a Logitech C920 as the external camera, workspace per the course bill of materials |

An optional comparison with GR00T N1.7 is reported separately and never pooled with N1.6.

## 2. The training randomization ("the box"), as coded at `ce807d9`

Paths are relative to `source/sim_to_real_so101/`.

| Factor | Range per reset | Where |
|---|---|---|
| External camera mount | x, y ±2 cm; z ±1 cm; roll, pitch, yaw ±0.05 rad (±2.865°) | `tasks/task_env_cfg.py:147-163` |
| Lightbox light | −3 to +1 EV (centre −1 EV) | `tasks/task_env_cfg.py:120-124` |
| Mat yaw | ±0.1 rad (Eval task); ±0.3 rad (DR task) | `tasks/task_env_cfg.py:129-133`; `tasks/vials_to_rack_env_cfg.py:186-192` |
| Rack | corner x ±4 cm, y ±1 cm; yaw ±0.5 rad about the corner | `tasks/vials_to_rack_env_cfg.py:146-150`; `mdp/resets.py:283-315` |
| Vials | x ±4 cm, y ±1 cm, roll ±0.3 rad | `tasks/vials_to_rack_env_cfg.py:150-155` |
| A vial pre-placed in the rack | probability 0.33 per reset | `mdp/resets.py:326` |
| Wrist camera focal length | 12-15 mm | `tasks/task_env_cfg.py:138-145` |
| DR task only: robot colour | random from a colour list | `tasks/vials_to_rack_env_cfg.py:165-171` |
| DR task only: sky (dome) light | −4 to +3 EV, 2500-9500 K, random HDRI | `tasks/vials_to_rack_env_cfg.py:173-182` |

The external camera's intrinsics are never randomized. The simulated external camera is a pinhole with fx = fy = 514.7 px (63.7° horizontal field of view), pointing 54.3° down, confirmed by a scene dump on October 23, 2026. Because the demonstrations also saw a randomized sky light, lightbox-exposure levels outside −3 to +1 EV are not treated as "outside the box" for H1; light results are descriptive.

**Rack distance from training (defined here, used in H1).** For a test rack pose, the distance is the RMS distance between its 4 slot centres and those of the nearest training rack pose, minimized over the 4 cyclic relabellings of the slots (the rack looks the same after 90°). "Training rack poses" are 2,000,000 resets sampled from the coded distribution above; the nearest of 75 independent draws (the demonstration count) is also reported, over 4,000 replicates.

## 3. Hypotheses

**H1 (primary): the training box is the real tolerance.** Inside the box, real success stays at or above half of nominal; outside it, it falls below half. The sharpest test uses the same 3 cm rack shift in two directions:
- 3 cm toward the back wall (x+3) lies inside the training distribution: slot layouts this close occur as often as for the nominal pose (0.8% of the sampled resets within 5 mm);
- 3 cm toward the camera wall (y+3), square-on, lies outside it: none of the 2,000,000 sampled resets places the slots within 10 mm (the nearest is 12.5 mm and requires 12° of yaw), even though the rack's centre alone stays inside the range the centre visits when the rack is yawed.

For the camera: 1.5° further down lies inside the ±2.865° pitch randomization; 6° further down is 2.1 times outside.

**H3: one photo suffices to correct the setup.**
- **H3a (primary, closed loop):** after a deliberate mis-setup, a correction estimated from one photo by GPU render-and-compare (E3) raises real success relative to no correction (E0).
- **H3b (secondary, estimation):** E3 estimates the needed correction more accurately than the best zero-shot vision-language model (E1, Cosmos Reason).

**H4 (secondary, simulation only):** the external camera's intrinsics mismatch (C920 vs the simulated camera) changes simulated success at the nominal pose.

**Exploratory:** agreement between simulated and real success across all real conditions (correlation and SIMPLER's MMRV).

## 4. Simulation design

**Configuration.** Every sweep cell fixes all randomization at the centre of its range (light at −1 EV, no pre-placed vial), except the one factor being tested. Vial layouts come from seeds; seeds 0-39 are used at every level, and seeds 0-9 are also the 10 real layouts L00-L09. Success is the course's own termination: a vial the jaw contacted is released inside the rack footprint below the slot entry, within 45.6° of vertical, held for 25 steps, before the 450-step timeout. Episodes interrupted by an infrastructure fault (policy-server timeout or crash) are re-run with the same seed and counted once; an episode is never re-run because it failed. All re-runs are reported.

**Cells.** 50 cells and 2,220 episodes run before the October 26 build, plus 4 cells and 560 episodes after it. The full list is `sweep_cells_v1.csv` (md5 `c8d81d681277c9119c4c3f2e96b075ae`; stored with `-text` in `.gitattributes` so the hash is stable). Summary:

| Cell | Levels | Episodes |
|---|---|---|
| S0 nominal | all at centre; seeds 0-39 × 5 repeats (the repeats measure the policy's own run-to-run variability) | 200 |
| S1 camera tilt down | 1.43, 1.5, 2.87, 3.58, 4.3, 5.73, 6.0, 8.6° | 8 × 40 |
| S2 rack toward the camera wall | 0.5, 1, 1.25, 1.5, 2, 3, 4 cm | 7 × 40 |
| S3 rack toward the back wall | 2, 3, 4, 5, 6, 8 cm | 6 × 40 |
| S-course | the Eval task exactly as shipped (seeds 0-99) | 100 |
| S4 / S5 lightbox light | −2, −3, −3.5, −4, −5, −7 EV; +1, +2, +3 EV | 9 × 40 |
| S6 external field of view | 55.8, 60.0, 65.9, 70.4° at the simulated pose | 4 × 40 |
| S7 camera yaw (code units; +10° code = 16.7° physical pan) | 1.43 to 8.6° | 6 × 40 |
| S8 camera raised | 0.5 to 3 cm (wall limit 4.1 cm) | 6 × 40 |
| S9 camera tilted up | 2.87, 5.73° | 2 × 40 |
| After October 26 | measured C920 intrinsics at the simulated pose; at the image-matched pose; the real arm's joint scale; the camera pose measured on October 26 | 200, 200, 80, 80 |

**Thresholds.** For the geometric factors S1, S2, S3, S7 and S8, the threshold is the offset at which success falls to half of the S0 rate, from a logistic fit with its upper asymptote fixed at the S0 rate and a 95% CI from 2,000 bootstrap resamples by seed. If success never falls below half, the threshold is reported as censored (above the largest level). S4, S5, S6, S9 and S-course are descriptive: k/n per level only.

**Registered simulation prediction.** For each geometric factor, the box predicts the threshold if the threshold lies between 1 and 2 times the training half-range: success holds inside the box and drops soon outside it. The prediction counts as met when the threshold's 95% CI overlaps that interval; a censored threshold counts as not met.

**Pilot disclosure.** A pilot of 110 episodes ran on October 24, 2026, before this registration, to test the pipeline.
- Nominal: 35 of 50 episodes. On seeds 0-9 it scored 9 of 10.
- Six extremes, 10 episodes each, on seeds 1000-1009, all below the same-seed nominal: tilt down +8° 4/10, tilt up 4° 5/10, field of view 70.4° 5/10, rack y+4 cm 7/10, light +2 EV 7/10, rack x+6 cm 8/10.
- No difference was significant (exact McNemar for tilt down +8°: p ≈ 0.13).

The sweep levels follow the plan written before the pilot (multiples of the training half-range plus the real-trial levels). Added after seeing the pilot: the brighter light levels, the 60.0° field of view and the tilt-up cells, all descriptive. Pilot episodes are excluded from every analysis.

## 5. Real-robot design

**Conditions.** One factor changes at a time; everything else is as in R1.

| Condition | Definition | n |
|---|---|---|
| R0 | Camera per the course instructions: left wall, lens 40.0 cm above the foam floor, 27.0 cm from the plate's rear face, 45.0° down by angle gauge, aimed at the mat centre | 10 |
| R1 | Sim-matched nominal: camera within 3 mm per axis and 0.5° per angle of the target pose fixed in v2 (ChArUco, mean of 5 placements); rack at the simulated nominal by jig | 25 |
| R2 = M1 | Rack y+3 cm (toward the camera wall), uncorrected (E0) | 12 |
| R3 | Rack x+3 cm (toward the back wall); x−3 cm only if x+3 fails the reach test | 12 |
| R4 = M2 | Camera tilted 6.0° further down, uncorrected (E0) | 12 |
| R5 | Camera tilted 1.5° further down | 12 |
| R6 / R7 | E3 correction at M1 / M2: 3 independent photo-and-correction cycles × 4 trials | 12 + 12 |
| R8 / R9 | E1 correction at M1 / M2: 3 cycles × 4 trials (descriptive) | 12 + 12 |
| | **Total planned** | **131** |

**R1's 25 trials** are the 10-trial gate block on the first trial day plus 3 controls at the start of each later day and 2 interspersed (15). The camera conditions run in ABBA blocks, with a fresh ChArUco measurement at each change. Vial start layouts L00-L09 are placed with 1:1 paper stencils and checked automatically before each trial. Trial order is randomized by a seeded script; the final schedule and its hash are fixed in v2.

**Correction cycles (R6-R9).** Each cycle is one independent mis-setup.
1. A clean photo is taken at the mis-setup. Its ground truth is measured by ChArUco for the camera, or by ruler from the mat edges for the rack.
2. Each method's estimate is computed from that photo before any trial.
3. The rig is set to an absolute target: the measured mis-setup pose plus the method's estimated correction, on the degrees of freedom the method estimates. The setting is redone if it misses by more than 0.5° or 2 mm. Any degree of freedom the rig cannot execute is recorded as "not applied".
4. 4 trials run per method. The order of the two methods within a cycle is assigned by the seeded schedule.

E3 may be tuned on real development frames (about 10 photos taken on October 26); E1 is chosen on simulated scenes only. The development frames are excluded from H3b.

**Real success (primary).** At the end of the trial, at least one vial the gripper picked up is:
- seated in a rack slot, with its bottom below the rack's top surface;
- within 45° of vertical;
- released;
- still in place 2 s after release.

The release must occur within 58 s of the first policy query, so that the 2 s hold is observed before the 60 s cap; a later release is a failure for the primary endpoint and is reported.

Secondary measures:
- release by the end of action chunk 28 (the simulated episode budget);
- a 0.5 s hold;
- grasp success;
- time to success;
- a failure taxonomy.

Pushing the rack does not fail a trial.

**Failure.** Every trial with a first policy query that is not invalid and does not meet the success criteria. This includes collisions, servo overloads and safety stops caused by the policy's own motion, and any human contact with the robot, a vial or the rack during the trial.

**Invalid trials** are excluded, re-run with the same condition and layout, and every one is reported:
- **I1:** a camera dropout or freeze;
- **I2:** a servo-bus dropout not preceded by a collision or overload;
- **I3:** a policy-server crash, hang, or latency spike over 1 s not caused by the policy;
- **I4:** a wrong setup caught at the start, or the camera found more than 1.0° or 5 mm off its target at the next check;
- **I5:** a foreign object or person in either camera view not caused by the operator's intervention;
- **I6:** a procedural error (wrong checkpoint, instruction, horizon or cap).

A trial is never re-run because it failed. Re-runs come from a reserve of up to 15 trials; when the reserve is spent, the reduced n is reported. Trials run since the last passing camera check, when that check shows 0.5°-1.0° or 3-5 mm of drift, are flagged and excluded only in a sensitivity analysis.

**Scoring.** Primary scoring is blind, from a judge camera above the rack plus the wrist keyframes, with renamed and shuffled clips. Clips are scored at least 24 h later (12 h for the last trial day). Live scores are kept, and Cohen's kappa between live and blind is reported. Blinding is partial, because the judge view shows the rack position.

**Unscored runs.** The 3-5 pilot runs on October 26 and the shakedown runs on November 3 happen before v2. They are unscored, excluded from every analysis, and reported qualitatively.

**Decision rules.**
- **D1, low nominal.** If the 10-trial gate block gives 3 or fewer successes, the setup is diagnosed in a fixed order, one change at a time, and a second block of 10 is run. If a fault was found and fixed, the first block is reported as a pre-fix block and excluded from R1. If the second block is also 3 or fewer, or both blocks together are 6 or fewer of 20, the minimum plan applies: R1 at 25-30; R2 and R4 at 10 each; E3 at 2 cycles × 5 per mis-setup; R8 and R9 dropped; the course's sim-and-real checkpoint added at nominal (10-15 trials); N1.7 nominal (20) added if validated. The photo set is unchanged.
- **D2, daily controls.** If a day's 5 controls give 1 or fewer successes, trials stop. The calibration, the camera pose and the light are checked, the 5 controls are re-run, and the day is flagged. A second failure triggers D1.
- **D3, no effect.** A mis-setup shows no effect if its E0 condition gives at least 7 of 12 and at least 0.8 times the pooled R1 rate so far (checked when R2, then R4, is complete). Its H1 data stand as a result, and trials are never added.
    - If only one mis-setup shows no effect, it keeps 1 cycle (descriptive), and its other 2 cycles move to the other mis-setup.
    - If both show no effect, the correction cycles move to a camera tilted 10° further down, with an 8-trial E0 block there.
- **Time cuts.** If time runs short, cuts follow this order:
    1. the N1.7 block;
    2. the reserve to 10;
    3. the third E1 cycle;
    4. the other E1 cycles;
    5. R3 and R5 to 8 each;
    6. E3 to 2 × 5 cycles;
    7. R1 to 20, with R2 and R4 to 10;
    8. R3 and R5 dropped;
    9. R0 dropped.

## 6. Analysis

- **H1a (primary):** pooled outside levels (R2, R4) against pooled inside levels (R3, R5). One-sided exact Cochran-Mantel-Haenszel test, stratified by factor (rack, camera). Sensitivity: pooled one-sided Fisher and Boschloo tests.
- **H3a (primary):** E3-corrected (R6, R7) against uncorrected (R2, R4). One-sided exact Cochran-Mantel-Haenszel test, stratified by mis-setup. A cycle-level permutation test is reported as a sensitivity analysis.
- **Multiplicity:** Holm across H1a and H3a, family α = 0.05.
- **H1b and H1c (secondary, α = 0.05 each, one-sided adjusted Wald tests):**
    - H1b, retention: p_inside − 0.5 × p_nominal > 0;
    - H1c, drop: p_outside − 0.5 × p_nominal < 0.
- **H1 is supported** if H1a rejects at its Holm level and H1c rejects. **H1 is falsified** if the pooled outside estimate is at or above half of nominal, or if the one-sided test of p_inside − 0.5 × p_nominal < 0 rejects at α = 0.05.
- **H3b (secondary, α = 0.05, one-sided):**
    - **Photos:** the 38 real photos of the photo set (34 mis-setups plus 4 at nominal).
    - **Ground truth:** ChArUco for the camera, jig or ruler for the rack.
    - **Score per photo and method:** the RMS of the residual error after correction, over the photo's degrees of freedom (6 for camera photos; x, y and yaw for rack photos), each normalized by its training half-range. A missing or unparseable estimate counts as no correction.
    - **Test:** a Wilcoxon signed-rank test, E3 against the best E1 variant.
    - **Descriptive:** the share of residuals inside the box (McNemar), the "predict zero" baseline and simulated scenes.
- **H4 (secondary, two-sided Fisher test):** simulated intrinsics against measured C920 intrinsics, both at the simulated pose.
- **Real nominal camera placement:** pose-matched (the simulated pose), unless the measured C920 fx differs from 514.7 px by more than 5% and the image-matched arm has higher simulated success than the pose-matched C920 arm with non-overlapping 95% CIs.
- **Reporting:** every condition as k/n with a Wilson 95% CI and its ratio to nominal, next to the simulated prediction at the measured real offset.

**Power** (exact enumeration, one-sided):
- **H1a:** 24 inside against 24 outside trials gives 0.88 power at the Holm level α = 0.025 if inside is 60% and outside 15% (0.93 at α = 0.05).
- **H3a:** 24 against 24 gives 0.91 at α = 0.025 for 55% against 10%. Clustering within correction cycles (design effect about 1.8) lowers its effective power.

## 7. Deviations from the course already made (documented in the repository)

- **Driver:** 580.65.06, the version Isaac Sim 5.1 is tested on, because the course simulator crashes on the 595 branch.
- **FFmpeg:** the course's download link returns 404, so the same FFmpeg 7.1 build is used from a pinned copy.
- **pyarrow:** pinned to 25.0.0, the newest at the course commit date, because newer versions break the course's NumPy 1.26.
- **Offline assets:**
    - The scene's 46 remote files (the D455 camera, and 4 materials with their textures) are mirrored locally.
    - The container's start-up `pip install` is replaced by an offline entrypoint, and the course source is mounted read-only.
    - The rendered camera matrix, pose and masks are identical; mean RGB differs by 0.14/255.
- **Policy-call timeouts:** the course's client stores a timeout but never applies it. Our clients time out after 10 s in simulation and 3 s on the real robot, and a timed-out episode or trial is handled as above.
- **Randomization:** the sweep fixes every factor at its centre and sets the pre-placed-vial probability to 0, because the shipped Eval task still randomizes the camera, light, rack and mat. The shipped task is run separately as S-course.
- **E3 camera moves** are written to the camera prims' USD transforms, as the course's own randomization does, because `Camera.set_world_poses` has no effect in Isaac Lab 2.3.2 with Fabric enabled.

## 8. Added in version 2 (before the first scored real trial)

- the simulated threshold per factor, with its CI;
- the chosen E1 variant and prompt;
- the H4 result and the real nominal camera placement;
- the R1 target pose;
- the R3 sign, from the reach test;
- the final real schedule and its hash;
- the analysis code and its hash.
