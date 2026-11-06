# Pre-registration v2: How far can a real setup drift before a sim-trained robot fails?

**Author:** Arturo Morales Rangel (Binary Core LLC)
**Version 2.** Released before the first scored real-robot trial, R0 included. Version 1 (`PREREGISTRATION_v1.md`, tag `prereg-v1`, commit `015789a`) stays in force except where this document says otherwise. Version 2 adds the items of v1 section 8 that are fixed before this release, fixes the analysis details v1 leaves open, and reports every deviation so far. The date of record is the date of the GitHub release `prereg-v2`.
**Addendum.** Items that can only be fixed after this release are marked *addendum* below. Each one is published in `PREREGISTRATION_v2_addendum.md`, as a new commit with its UTC time, before the step that uses it and before any data it applies to. No earlier commit or tag is changed.

## 1. Status at release
- **Simulation:** sweep v1, priorities 1-3, is complete (50 cells, 2,220 episodes, finished October 24, 2026). The 4 priority-4 cells (560 episodes: `H4_c920_measured`, `H4_c920_image_matched`, `G3_joint_scale`, `R_replay_oct26`) have not been run yet. The two H4 cells need the C920 intrinsics, which are measured after R0.
- **Real robot:** no scored trial yet. R0 runs under this version.
- **Real trials:** planned for November 6-7, 2026 (section 5).

## 2. Items added in version 2 (v1 section 8)

| # | Item | Value |
|---|---|---|
| 1 | Simulated threshold per factor, with 95 % CI and the registered prediction | **All five thresholds are censored.** Success never falls to half of S0 at any tested level (S0 124/200 = 0.620; half = 0.310). The lowest success rate at any level is 0.50-0.60. S1 > 8.6° (code pitch), S2 > 4 cm, S3 > 8 cm, S7 > 8.6° (code units; v1: +10° code = 16.7° physical pan), S8 > 3 cm. 99.35-100 % of the bootstrap resamples are censored. v1 counts a censored threshold as "prediction not met", so the registered prediction is not met for any factor. Files: `results/analysis/thresholds_v1.json` and `.md`, `analysis/thresholds.py`. The sweep episode files are published with the dataset; their SHA-256 are listed in `thresholds_v1.json` |
| 2 | E1 model and route | **Cosmos-Reason2-2B** (`nvidia/Cosmos-Reason2-2B`, Hugging Face revision `9ce19a19`), run locally on the A4500 in BF16 (transformers 4.57.1, torch 2.8.0). Our protocol planned the 8B model through build.nvidia.com. That route was unavailable on November 6, 2026: HTTP 404 for `nvidia/cosmos-reason2-8b` and for `nvidia/cosmos3-nano-reasoner` with our account's key. The 2B model is our choice. The poster states that E1 is the 2B model. A one-image test on the A4500 peaked at 6.3 GB for the whole GPU |
| 2b | E1 variant and prompt | *Addendum.* One of two variants: metric deltas, or a categorical direction × magnitude bin. It is chosen on simulated scenes only, before E1 sees any real photo (v1 section 5). Prompt: two labelled images (A = sim reference rendered with the measured C920 intrinsics; B = the photo), physical sign definitions, and a JSON answer |
| 3 | H4 result and the real nominal camera placement | *Addendum*, once the C920 intrinsics are measured (after R0). The placement rule is v1 section 6's. If the measured fx is within 5 % of 514.7 px, the placement is pose-matched without waiting for the simulation. Otherwise it waits for the cells `H4_c920_measured` and `H4_c920_image_matched` (200 episodes each). The H4 test itself uses `H4_c920_measured`. Limitation: the simulated camera is a centred square-pixel pinhole, so only fx changes; the measured fy/fx, principal point and distortion are not represented |
| 4 | R1 target pose | The lens of the camera that renders the policy's front view (`Camera_OmniVision_OV9782_Right`), from the course scene. In the task frame: (0.13755, 0.32973, 0.48858) m, 54.266° down, heading −81.196° (8.804° pan toward the back wall), roll +1.584°. In tape terms: 46.045 cm above the foam floor, 23.958 cm from the open front edge, 5.171 cm from the left wall's inner face. Valid if item 3 gives pose-matched |
| 5 | Camera tolerances | R1 is accepted at ≤ 3 mm per axis and ≤ 0.5° per angle, absolute, as the mean of 5 board placements (aim ≤ 0.3°). Deliberate levels: the measured change within ±0.3° of the level. Per-trial image drift ≤ max(1.5 px, 3 SD). I4 above 1.0° or 5 mm. Board placement repeatability σ ≤ 0.5 mm / 0.3° |
| 6 | R3 sign | *Addendum*, after the reach test: x+3 if the far rack slots are reachable at x+3, else x−3 (v1) |
| 7 | R5 level | Tilt down +1.5° (unchanged from v1) |
| 8 | Final real schedule and its SHA-256 | *Addendum*, before R1. **Fixed now for R0:** 10 trials with layouts in the order L01, L07, L04, L02, L05, L03, L08, L09, L06, L00 (uids N04-001 to N04-010; the prefix is the day of the original draw). The schedule comes from our seeded generator, unchanged. Changes before R1 only move whole blocks between days, keep each H1 pair and each cycle's two methods on the same day, or apply v1's time-cut order (section 5). Trials inside a block are never reordered |
| 8b | Trial runner checks | Implemented: clean view (6 × pixel noise, 25 floor levels, blobs ≥ 150 px), rack colour range, a 3 s policy watchdog (→ I3), frozen frames (→ I1), camera-setting readback before each trial. *Addendum:* the numeric thresholds, after the unscored shakedown and before R0 |
| 8c | Vial placement check | Paper stencil, then an automatic check before each trial: vial masks against the projected targets, IoU ≥ 0.7 per vial and combined, and each visible cap's blue on its projected cap (≥ 50 %). R0's camera pose is measured only after the R0 trials, so R0 frames are checked afterwards. An R0 trial that fails the check becomes I4 and is re-run from the reserve. The check runs as soon as the R0 pose is measured (C920 intrinsics and the R0 board pose, after the R0 trials), before the camera leaves R0. A re-run then uses the camera untouched at R0, confirmed on screen with the pose display against the R0 measurement (within 2 mm and 0.25°). If the camera has already left R0, it is set back on screen with the same display and tolerance, not by tape only. *Addendum:* a centroid tolerance from the real image noise, after the shakedown |
| 9 | Analysis code and its SHA-256 | `analysis/stats.py`, `analysis/thresholds.py`, `analysis/real.py`; hashes in section 7. numpy and the standard library only. Checked against scipy 1.15.3 (Fisher, Boschloo, Wilcoxon, McNemar, Wilson, Clopper-Pearson, within 3e-13); the exact CMH test checked against brute-force enumeration |
| 10 | Blind scoring delay | Unchanged: ≥ 24 h, and ≥ 12 h for the last trial day |
| 11 | E3 archive SHA-256 | *Addendum*, before the first scored photo. E3 is developed on 6 development photos taken at the nominal camera pose on November 6 (instead of about 10 on October 26). They are excluded from H3b |
| 12 | Unscored runs | The pilots and shakedown runs (November 3-6) are unscored and excluded from every analysis, as in v1. Some now happen after this release, on November 6 |

## 3. Analysis details v1 leaves open (fixed as implemented in `analysis/`)
- **Threshold model:** P(success | x) = p0 / (1 + exp(k (x − t) / h)), k ≥ 0, with p0 the S0 rate and h the training half-range. It is fitted on the factor's own cells; S0 enters through p0, not as a point at x = 0. Maximum likelihood on a grid, then Nelder-Mead. A threshold is censored when t lies above the largest tested level.
- **Threshold CI:** 2,000 bootstrap resamples by vial seed. The 40 seeds are drawn with replacement, and every episode with a drawn seed is kept (S0's 5 repeats per seed included, so p0 is resampled too). The same draws serve every factor. Percentile 2.5 / 97.5, with censored resamples counted as +∞. RNG: numpy `default_rng(20261103)`.
- **S7** thresholds are in code units (v1: × 1.67 for the physical pan).
- **p_inside − 0.5 · p_nominal:** adjusted Wald (Price-Bonett: 1 success and 2 trials added per group).
- **p_nominal** = all valid R1 trials, minus a D1 pre-fix block if there is one.
- **Strata:** H1a rack = R3 vs R2, camera = R5 vs R4. H3a M1 = R6 vs R2, M2 = R7 vs R4.
- If H1 is both "supported" and "falsified" by the two rules, it is reported as falsified (v1 is silent on this).
- **Wilcoxon:** zero differences dropped, midranks for ties, exact distribution.
- **H3b:** residual = truth delta + correction on each degree of freedom. A missing output or degree of freedom counts as no correction (0). "Inside the box" = every degree of freedom within its training half-range.
- **McNemar:** two-sided, min(1, 2 × the smaller tail). **Boschloo:** maximised over a 20,001-point grid plus golden-section refinement.
- **Cycle-level permutation:** R2 and R4 have no cycles, so they are clustered by their block (or, without one, in consecutive fours by uid). Exact when there are ≤ 10^6 assignments, otherwise 200,000 random ones with seed 20261103.
- Not computed by this code: the exploratory sim-real agreement, which needs the simulated predictions at the measured real offsets.

## 4. Power figures
v1 section 6's power figures (0.88 / 0.93 for H1a, 0.91 for H3a) are those of a pooled one-sided Fisher test, not of the registered stratified exact CMH test. For the CMH test with 12 vs 12 per stratum: H1a 0.874 at α = 0.025 and 0.928 at 0.05; H3a 0.900 at 0.025 and 0.948 at 0.05. The registered test is unchanged.

## 5. Schedule and run order
- **Trial days:** v1 planned the real trials from November 4 and this release for November 2. The setup work took longer, so the real trials run on November 6-7. November 6: R0, the R1 gate block, the rack block (R2, R3) and the M1 correction cycles. November 7: R4 and R5, the M2 correction cycles and the reserve. Last scored trial: November 7, 20:00 PT.
- **Light drift log:** run on November 6 before R0 and every other trial: ≥ 2 h from switch-on, box closed, nobody at the box.
- **Blind scoring** (≥ 24 h after the trial; ≥ 12 h for November 7's trials): R0 (November 6, late morning) is scored on November 7. The other November 6 trials are scored from November 7 evening, each once 24 h have passed, and the rest on November 8. November 7's trials are scored on November 8 from 10:00 PT, after the photo set below, which keeps their delay above 12 h.
- **Photo set:** the 19 camera photos of the H3b photo set move to November 8, 08:00-10:00 PT, before the blind scoring of November 7's trials. No policy runs then, so no blind delay applies.
- **Time cuts:** if time runs short, v1's order applies (section 5, "Time cuts"). Item 1 of that order (the N1.7 block) is already applied: the N1.7 comparison is dropped. Any further cut is decided from the measured trial time and published in the addendum before the trials it removes.

## 6. Deviations from v1 and differences from the course setup
Each is our choice unless stated otherwise. Readings are logged in the repository's results and published with the dataset.

| # | What | Plan | What we did | Effect |
|---|---|---|---|---|
| D1 | Light slot in the box roof | 30 cm × (tube diameter − 1 cm) | 30.0 × 1.0 cm, the size of the simulated rect light | Same light in every condition, R0 included |
| D2 | Light position | Course video: the light inside the box | The light on the roof, over the slot | Known difference from the course's box |
| D3 | R0 reading | Course page 05: the table's row label says "back wall"; its value says "back of robot to center of camera lens"; the video shows a hole position | R0 follows v1's reading of the written page (40.0 cm / 27.0 cm / 45.0°) | The video's reading is reported as an ambiguity |
| D4 | R1 target point | Our protocol used the camera mount's origin | The rendering camera's lens (item 4), 4.75 cm from the mount origin | R1 target as item 4 |
| D6 | Camera mount | A clip arm through oversize wall slots (one for the simulated pose, one for R0) with foam shims, pitch by the clip hinge | An articulated arm on a desk-clamp pole, through a hole of about 4 cm in the left wall; the camera touches nothing in the box. For R0, no second hole: a slot 4.0 cm wide is cut straight down from that hole, its bottom at 38.0 cm above the left wall's bottom edge; the camera's folded clip passes through it. A felt flap covers the opening (hole and slot) from outside. The clip hinge sits at its mechanical stop. Roll is set explicitly from the image | Targets and tolerances unchanged. Tilt levels are set with the arm |
| D7 | Board sled key | 44.0 mm wide, 10 mm long | 5 mm long, 40.6 mm wide, fitted on the real base, which matches the course mesh within ±0.5 mm | Registration datums unchanged |
| D12 | Angle gauge | v1: R0 only. Our protocol also used it for later camera checks | R0 by tape before the gauge: lens about 40.3 cm above the foam floor (target 40.0), 28.2 cm from the floor's front edge (target 28.4, i.e. 27.0 cm from the plate's rear face) and 5.2 cm from the left wall's inner face (target 5.2); not re-read after the gauge and the aim (our choice). The gauge was used once, at R0 with the roof off (it does not fit under the roof): pitch 45.0°. Roll was set level from the board's horizon in the image, as the gauge cannot read roll on the camera's top. Pan was set so the image centre falls on the mat centre. When the roof went on, the still check showed an even 1.35 px shift of the board corners (limit 1.0 px), stable over 7 captures; accepted, and that capture became the accepted R0 capture. After the box work (the felt flap over the camera opening (hole and slot) in the left wall, seams, door), the still check against it: PASS, median 0.37 px, max 0.80 px. Every other camera setting uses the on-screen pose display and the ChArUco board | No registered step changes. The R0 gauge reading is compared with the R0 board pose descriptively |
| D13 | Front door | A hinged matte-black door, taped hinge on the left panel's front edge | A lift-off door, seated on a pencil line on the base board and held by 2 tape tabs at its top corners, no hinge | The door goes back on the same line at every reset |
| D14 | Mat placement | A foam rake from the robot plate's front and left faces, tape loops, a pencil outline 5 mm inside the mat; each trial block starts with the rake check or the outline | The rake's two distances set with a steel ruler (near edge 6.87 cm from the plate's front face, left edge 15.23 cm left of the plate's left face), tape loops; no rake and no pencil outline. The two ruler distances are re-checked before each trial block | Same mat position; the check is by ruler |
| D15 | Rack placement jig | A lipped front plate with spacers and a ruler for every rack position; a later protocol revision replaced it with an L-jig with fixed stops | The L-jig: three foam-board plates (nominal, x+3, y+3), each with 1 cm lips that hook the mat's front-left corner and a fixed stop for the rack. The stop positions are checked by a camera fit test before R0, not with a ruler | Rack positions as registered |
| V21 | Arm calibration | Course check: "Overall: PASS" | "Overall: WARN" on wrist_flex only: range 2,274 counts, −3.2σ from the course's 15-robot mean, the same in 4 runs at both hard stops. Taken as this unit's range | The policy's wrist_flex ±100 spans 2.4 % fewer counts than the course mean |
| G5 | October 26 build gate | Calibration, intrinsics, wrist check, light log, ≥ 1 pilot and tilt reach on October 26 | Not done on October 26. Arm calibration on November 4; light log, the first pilot and the shakedown on November 6 before R0; the C920 intrinsics after R0 | The pilot findings come shortly before R0, not 9 days before |
| DEV | E3 development photos | About 10 photos on October 26 | 6 photos on November 6, at nominal | E3 is frozen and hashed before the first scored photo |
| N1.7 | GR00T N1.7 comparison | Optional 20 trials | Dropped (v1 time-cut item 1) | No N1.7 trials |

## 7. Files in this release
| File | SHA-256 |
|---|---|
| `analysis/stats.py` | `52029aacf72c7360ddc828be7d520dbe92ed45a2f0e5c5c30869069e9074cf8a` |
| `analysis/thresholds.py` | `f686b996c4a95cd101dfd4e53f60eb455335c1e1c38483bb49ee92c8b8cf4d4b` |
| `analysis/real.py` | `25554ae90b10a91041d98eb872e59409ef9a346a4e682d41119ef015dcc26f7b` |
| `results/analysis/thresholds_v1.json` | `8e5b4fa99bd0c0c9361a4e9e7589387be3c07dad38d11ca1daada09bc18617a5` |
| `results/analysis/thresholds_v1.md` | `719cc37cf736fb0bbe7bb30fc6d5ee384f31ce2b31868a2a2ee72d1e632c0c3f` |

`analysis/thresholds.py` checks that every sweep row carries the stamp `gtc@0f2b1f7`, the working copy the sweep ran from. Its sweep files are byte-identical to `prereg-v1` (README).
