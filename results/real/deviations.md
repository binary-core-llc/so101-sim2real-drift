# Real-trial deviations and notes (append only)

## N04-001 (R0, L01), 2026-11-07 02:58 UTC: stopped with f while holding at the pan limit
- The arm turned right past the tubes toward the right wall (as in the unscored V28-01) and held at the right end of
  shoulder_pan without touching anything. The operator pressed `f` at 34.05 s after T0 (run 37.57 s); live score F,
  grasp n, code F5.
- C 2.1 D: `f` is for a safety stop; otherwise the trial runs to the 60 s cap. Holding at the pan limit without contact
  is not a safety event: servo temperatures rose at most 1 deg C over the trial (pan 34 -> 35 deg C; V28-01, 50 s at the
  same limit: pan 35 -> 35 deg C).
- Rule for every remaining trial (Arturo's OK, Nov 6 19:05 PST): holding at a joint limit without contact runs to the 60 s cap; `f`
  only for contact that strains (wall, rack, pressing into the mat or a tube) or any sign of damage.
- The record is unchanged (records are never edited). The live outcome F does not depend on the stop: no tube was
  reached. The primary score is the blind score from the judge clip and the wrist keyframes (C 1.7).

## N04-001 attempt 1 relabelled invalid (I4), 2026-11-07 03:1x UTC
- Reported by the operator at about 03:05 UTC: no tubes were on the mat in attempt 1 (reset error: the tubes were taken
  off for the 18:3x PST reference re-take and not put back for L01). The pre-trial frame and the first keyframe confirm it:
  no change region in the tube zone (with three tubes, V28-01 shows five regions of 2,650-5,122 px). The R0 tube check
  could not catch it before the trial: it is deferred until the R0 pose is measured (v2 8c), and the tube zone is ignored
  by the clean-view check.
- Relabelled from F (F5) to I4, "wrong setup", C 1.5. The original live score is kept inside the record (`relabel`);
  audit copy `trials.jsonl.pre-relabel-*`, never deleted.
- Re-run as N04-001 attempt 2, same condition and layout (L01), appended to the current R0 block with the camera
  untouched at R0, from the reserve (1 of 15 used). C 1.5 re-runs within 10 min of the fix; the fix (placing the tubes)
  takes under a minute once found, and the alternative (the Nov 7 reserve block) would need the camera set back to R0.
  To be reviewed again in the evening (C 1.5).

## Flag wall_contact added to N04-001 attempt 2 and N04-002 attempt 1, 2026-11-07 03:3x UTC
- Both records' notes say the arm pressed on the right wall (the reason for `f`); the flags were left empty in the form.
  Added `wall_contact` from those notes at the operator's request (logged in each record under `flag_edits`; audit copy
  `trials.jsonl.pre-flags-*`). The operator types it in the form from now on.

## Judge recording: one continuous recording for the rest of R0 (our choice), 2026-11-07 03:5x UTC
- C (judge view): one continuous recording per block of at most 30 min, with a UTC clock slate at the start. Recordings 1-3
  followed it (slates 01:48:05, 02:30:15, 03:05:20 UTC); recording 1 holds no trial, recording 2 holds N04-001 attempt 1,
  recording 3 started at 03:05:20 UTC (no recording 4 was started: recording 3 runs on, Arturo).
- From N04-004 on, the recording then running continues through the rest of R0 with no new slate (Arturo, our choice, to
  save time).
- Clip sync instead: the file's own start time (phone metadata) plus the arm's visible rise to the start pose at connect,
  matched to the runner's `t_launch` of each trial (sub-second); the recording's opening slate, where there is one, checks
  the offset. Clips are cut from `t_launch` - 2 s to `t_end` + 3 s (C).
- Risks checked after the block: the phone splitting the file (some phones split near 4 GB, about 30 min at 1080p) and
  free storage; the clip count against the trials.

## N04-004 (R0, L02): stopped with f at 23.96 s at the pan limit, no contact; flag and note corrected
- The arm went toward a tube, missed, then kept turning toward the right wall to the pan limit without touching anything.
  The operator pressed `f` at 23.96 s after T0. Under the agreed stop rule this is not a safety event; the record keeps
  F / F5 as scored (Arturo), for the evening review.
- `wall_contact` was typed in the form but there was no contact: removed; note typo "ent" -> "went" (both logged in the
  record; audit copy `trials.jsonl.pre-n04004-*`).
- From N04-005 on, a trial that only holds at a joint limit runs to the 60 s cap (Arturo).

## N04-004 correction (supersedes the entry above, except the note typo fix), 2026-11-07 04:2x UTC
- Operator's correction: the arm did touch the black lift-off door and pushed against it; the door, held by two tape tabs,
  gave way a little and the wrist went partly out of the box. `f` at 23.96 s was a real safety event. `wall_contact` is
  restored (logged in the record; audit copy `trials.jsonl.pre-n04004b-*`); F / F5 stand; the "ent" -> "went" fix stays.
- The note typed in the form still says "without touching it"; the correction is in the record's `flag_edits`.
- Before N04-005: door re-seated on its pencil line; arm and wrist cable checked (Arturo).

## N04-007 (R0, L08): success; stopped with f, not a safety event
- First tube grasped (7.9-9.8 s), released into the back-left slot (about 12-14 s), upright, held to the end (about 28 s):
  S under C 1.4 (released, in a slot, <= 45 deg, held >= 2 s, before T0 + 60 s; also S28 and within 30 s). Second tube
  grasped and left lying across the rack top (flag `second_vial_attempt`); the third not reached. Live score S as saved.
- C: the operator stops at the first success (`s` after a slow count of 3, about 17 s here). The run went on, and the
  operator pressed `f` at 41.3 s with no contact: not a safety event (Arturo); only the end reason is affected.
- The preflight before it was a pre-start abort (I0): a changed region of 117 x 130 px at the bottom right (floor in front
  of the robot base, by the door), light 0.949, drift 1.09 px (WARN). Mat 0.27 px and rack 0.02 px in the same check, and
  drift 0.20 px two minutes later: no camera or box motion; the drift fit was pulled by the changed region. Most likely the
  door not yet back on its line after N04-006; not confirmed (the frame was overwritten by the passing attempt; from now
  on the runner keeps pre-start frames under their own names).
- Door (Arturo, our choice): no outside brace; `f` at the first touch, door re-seated on its pencil line with its 4 tabs
  before every trial.

## R0 reference re-taken before N04-008, 2026-11-07 05:1x UTC
- Pulling the seated tube out after N04-007 turned the rack. Three N04-008 preflights failed (I0, frames kept): rack 4.1 px /
  0.43 deg from the reference, which also pulled the drift fit to a false 10.7 px (camera unmoved: box wall line 0.40 px,
  0.07 deg; mat edges <= 0.88 px). Re-placed with rack_view: both faces within 1 mm of target N, but 2.6 px from the
  reference's pose. Reference re-taken with the rack as placed (Arturo's choice (a)): rack -1.28 / +0.32 mm from target N
  in the new reference (fit-test rule 2 mm); same lighting; previous copy kept. Fresh frame: all checks pass.
- Trials N04-001 to N04-007 were checked against the previous reference; N04-008 on against this one.
- 05:3x UTC: three more N04-008 preflights failed on one clean-view region at the top-right edge (x 620, y 43; 356-525 px):
  a pale wedge of light on the right wall's corner by the door, present in the reference and changing with each door
  re-seat. Not part of the task: rect x 590-640, y 0-80 added to the reference's ignore zones (old mask kept; for the next
  addendum entry). The three failed frames pass with it.

## Servo bus drops at connect (I0, not trials)
- 03:12 UTC, before N04-001 attempt 2: "Failed to sync read 'Present_Position' on ids 1-6 … no status packet"; fixed by
  re-seating the 12 V and the USB (Arturo).
- 05:28 UTC, before N04-008: "Failed to write 'Lock' on id_=5 (wrist_roll) … no status packet"; fixed by re-seating the
  wrist servo cables with the 12 V off (Arturo); it then connected and N04-008 ran.
- Read-only health check after N04-008 (05:34 UTC): all six servos PASS, 12.4-12.7 V, 33-36 C, status 0
  (results/robot/health_follower_2026-11-07T053404+0000.json). A drop during a trial would be I2.

## C3 lens calibration, set A: bottom-left image corner accepted as missing (Arturo's OK, Nov 7 ~02:20 PST)
- C3 set A, 2026-11-07 ~02:10 PST: image corner bottom-left not reached within 80 px (B 3.2 asks 40 px; the accepted
  band is 80 px). Best reached 81.5 px (view_031: board flat, edge against the back wall). That corner sees the floor
  3 cm in front of the back wall; the board's paper margin is 1.8 cm and a dot needs a full marker beyond it. Placement
  model (set A lens, box turned 8 deg to the camera; matches the real nearest dot within 1 px on 7 views): best flat
  81.5 px; leaning on the back wall 76-78 px only with mm-exact placement. Set A accepted with 3 of 4 image corners
  within 80 px (our choice); distortion toward that corner is extrapolated (k3 fixed). The same limit applies to set B.
- Tooling: calib/intrinsics_solve.py --missing-corner bottom-left leaves that corner out of the corner rule and writes
  this deviation (with each set's nearest-dot distance) into config/c920_intrinsics.json. calib/intrinsics_capture.py
  now shows each corner's nearest dot live and has --resume (set A's 72 views backed up first, with checksums, in
  media/calib/intrinsics_backup/A_20261107T100932Z).

## H4: image-matched cell not run (Arturo's choice (a), Nov 7 ~16:55 PST)
- v2 item 3: with the fx gap > 5 % (630.62 vs 514.7 px, +22.5 %), the placement waits for H4_c920_measured and
  H4_c920_image_matched. The image-matched pose (sim/image_matched_pose.py, results/h4/image_matched_pose.json; mask IoU
  0.417 -> 0.739) puts the lens 7.4 mm past the camera wall's inner face and 6.0 mm above the roof's inner face; the real
  camera cannot be placed there, and sim/make_h4_cells.py refuses it as not a valid level.
- Done instead: the image-matched pose is recorded as unreachable and its cell is not run; the real nominal placement is
  pose-matched by v1 section 6. H4_c920_measured ran in full: 148/200 (0.740, Wilson 0.675-0.796) against S0 124/200
  (0.620, 0.551-0.684), Fisher two-sided p 0.0135 (results/h4/h4_result.json, results/analysis/h4_inputs.json).
- The released analysis code prints "undecided" for the placement without the image-matched cell; it is unchanged, and
  addendum entry 2 (item 3) states the placement.

## Rack found turned after C3; its orientation is part of the placement (Nov 7, ~17:10-18:10 PST)
- After C3 (about 120 board placements on the mat, the rack used as a prop), the rack went back with plate N and
  calib/rack_view.py --ref N04-R0_R0. Camera and mat unmoved throughout (box wall line <= 0.35 px, mat edges <= 0.6 px).
- With the top face aligned to the reference (ECC +0.2 / -0.4 px) and the runner's rack check passing (1.0 px, -0.24 deg),
  the clean view still failed (blobs 1167 and 165 px): the rack's near top edge (toward the camera wall) showed a soft
  12 px gradient where the reference shows a sharp step, and the inner walls of the two holes nearest the robot differed.
  The rack has some rounded and some sharp top edges (Arturo): it had been turned to another side during C3.
- With a sharp top edge toward the camera wall: every rack_view line green (top face -0.6 / -0.6 px, rack check 1.1 px,
  turn -0.26 deg, clean view no blob, light 0.989). Fresh frame 02:10 UTC: rack 0.81 px / -0.23 deg, clean view pass,
  light 0.972, mat 0.35 px; drift 2.19 px (limit 1.5) from the rack's small residual offset and turn (0.42 px with the
  rack region left out; the N04-008 to N04-010 pre-trial frames read 0.25-0.38 px).
- From now on the rack's orientation is part of its placement (as B 5.1 asks for a print that is not 4-fold
  symmetric): a sharp top edge toward the camera wall, and a pencil arrow on the rack's bottom pointing to the camera
  wall (Arturo, at the next lift). No trial ran between C3 and this check.
- rack_view changed during this placement (182b364, 08539b6): the reference outline over the live one, a push arrow in
  mm that follows the top face (the mask centroid under-reads image y because the rack runs off the image's bottom
  edge), and the runner's clean-view and light checks in the window; the runner's checks and thresholds are unchanged.

## Sled measured to about +-1 mm, not B 4.2's +-0.25 mm (Nov 7, ~19:20-19:40 PST)
- B 4.2 asks for d_x at both grid ends and d_y and h_K by steel ruler (+-0.25 mm). Done instead (Arturo): d_x by the
  steel ruler beside the tongue on one side, read from a photo (103 +-1 mm); d_y and the end-face angle from two
  phone photos solved with the board's corners (90.2 mm at the key; 0.2-0.4 deg, counted as +-0.3 deg); h_K by eye
  with the ruler (10 +-1 mm). The phone photos' d_x (106 mm) was withdrawn: the tongue sat at the photo's edge.
- config/board_in_E.json gives d_x and d_y at the grid corner (the board origin), which is the point B's formula
  places; the template's "mean of both grid ends" would put the corner about 0.5 mm off with a 0.3 deg yaw.
- Effect: B 9 budgets the sled at 0.5 mm / 0.3 deg. With about +-1 mm in x, y and z and +-0.3 deg in yaw, the
  absolute camera pose in E carries about 1-2 mm and 0.3 deg more than budgeted. Deltas with the board untouched
  (bracketed changes, B 9) do not depend on board_in_E. Every pose record keeps the board-frame pose (C_K, R_K), so
  E poses can be recomputed if board_in_E.json is improved later.
- Paper test in the box: pass on both lobes.

## R0 PnP: mean over one seating state; x and y spread over B 4.2's 0.5 mm (Nov 7, ~20:10-20:50 PST)
- Seven sled placements, all RMS <= 0.197 px with 35 corners. In r0_p3 and r0_p4 the board sat in a second state: rocked
  0.55 deg about an axis across the tongue near the grid corner, tongue end about 1.0 mm lower and far end about 2.5 mm
  higher than in the others (the far end lifted off the mat; the tongue end held low at the lobes). Both were seated by
  pressing the middle of the tab's end toward the robot (Arturo). They stay on record (results/poses/r0_p3.json,
  r0_p4.json) and are left out of the mean. The first mean of p1-p5 (commit 74148e9) is superseded.
- Seating method from r0_p6 on: sled lowered flat about 1 cm short of the lobes; one fingertip on the tongue near the
  carrier pushes it horizontally until the end face stops on both lobes (never at the end or on the key, no downward
  push); one light tap straight down on the far-end margin; paper test on both lobes; hands out, 2 s; the printed roll
  must be positive (about +0.1 deg; the second state reads about -0.7).
- results/poses/r0.json = mean of r0_p1, r0_p2, r0_p5, r0_p6, r0_p7 (board tilt within 0.09 deg of r0_p1): lens C_E
  (0.1703, 0.3396, 0.4195) m, depression 49.38, heading -80.52, roll 0.12 deg; spread pos SD [1.28, 0.73, 0.16] mm,
  depression 0.03, heading 0.24, roll 0.02 deg. p1 and p2 were seated with light pressure on the tongue, p5 by pressing
  the tab's end (it landed in the resting state), p6 and p7 by the method above.
- B 4.2 accepts sigma_pos <= 0.5 mm and sigma_rot <= 0.3 deg (yaw): the angles pass, x and y do not. The x and y spread
  follows the heading (correlation -0.996 and 0.94; 5.3 and 2.9 mm per degree): the sled's in-plane yaw swings the lens
  about the lobes, the lever B 4.8 names (0.3 deg about 1 mm at the camera). With the heading-linked part removed, x and
  y spread 0.11 and 0.25 mm. Accepted on the yaw limit (Arturo, our choice); the position spread is reported.
- The E values still use board_in_E.json of commit 3a42a3e; when the sled datums are final, the placements are
  re-expressed with tools/rebase_poses.py and the mean is re-run (the board-frame poses do not change).

## N04-R0 ran with the mat, rack and tubes off their sim positions; R0 repeated as N04B-R0 (Nov 7, ~21:00-22:00 PST)
- Found by the deferred R0 tube check (0/11, targets about 16 px off in the same direction in every trial) and the
  projected mat, rack and aim mark. Arturo's ruler, from the robot's lobes: the mat's camera-side edge about 194 mm from
  the camera-side lobe's outer face (sim 174.6) and its front edge about 77-78 mm from the lobe tips (sim 68.7), +-5 mm
  from a photo; the robot-to-left-wall distance matches the sim (36.0 vs 36.1 cm). So in N04-R0 the mat, and the rack
  and tubes placed from it, sat about 18-19 mm toward the camera wall and about 9 mm farther from the robot than the
  sim (the camera view puts the rack about 27 mm toward the camera wall, the mat turned about 1 deg; to be settled
  against the re-placed mat). This is outside the sim's +-10 mm randomization of the rack and tubes in that direction.
- N04-R0 (10 scored: 1 S, 9 F, 8 F with wall/door contact) stays on record as "R0 with the scene offset", not pooled.
  R0 is repeated tonight as N04B-R0 (N04B-001 to N04B-010, same layouts in the same order) after the mat and rack are
  re-placed from the lobes and before the camera moves (Arturo). Schedule rows added to config/schedule.csv; addendum
  item listed for the next entry.
- The deferred tube-check results written into N04-R0's records (0/11, flagged for review) cannot separate the tube
  placement from the mat offset; no N04-R0 trial is re-labelled on them.

## Flag regrasp_n=3 added to N04B-001 attempt 1, 2026-11-08 UTC
- The operator entered only `wall_contact` in the form; the arm tried to grasp one tube 3 or 4 times (operator's report).
  Added `regrasp_n=3` at the operator's request (logged in the record under `flag_edits`; audit copy
  `trials.jsonl.pre-n04b001-*`). Outcome F / F5 unchanged.

## Judge recording for N04B-R0: one continuous recording, no slate (Arturo's choice, Nov 7 ~22:40 PST)
- C asks for one recording per block of at most 30 min with a UTC clock slate. For N04B-R0 the phone records the whole
  block without a slate and without splits. Clips are cut by the runner's UTC timestamps per trial, aligned on the
  video's own start time and checked against the arm's visible motion onset when the runner connects.

## N04B-002 attempt 1: record rebuilt from disk after Ctrl+C in the score form (Nov 7 ~22:45 PST)
- The trial ran (policy from about 06:43:03 UTC; `f` pressed at about 18.7 s when the arm reached the black door), the
  arm went home, then Ctrl+C was pressed by mistake in the score form. The runner writes the record only after the form,
  so none was written; the terminal was cleared, so the END line is lost. Not counted as a new trial and not re-run.
- Rebuilt with tools/recover_trial_record.py: pre-trial checks, tubes-present fields and the post-trial mat check
  recomputed with the runner's own functions from the saved frames (checked on N04B-001: identical values); chunk,
  action, latency and period figures from the step log (rounded there to 0.1 ms); freeze check from the lossless
  keyframes; hashes and settings unchanged since the run; gtc commit b63014b at run time. Score from the operator:
  F, F5, wall_contact, no grasp, with the operator's description as the note.
- Not recoverable (null in the record, listed under record_recovery): camera-lock readbacks (so I4 cannot be
  evaluated; the lock read back at the next trial's preflight), servo temperatures, start-pose reading, ping, and the
  exact t_enter, t_launch, t0, t_end, key time and run_s (file times recorded instead).
- After the block, the runner will save the trial before the score form, so an interrupted form cannot lose it.

## N04B-R0 deferred tube check: 0/10 by B 5.5, but the tubes sit on their targets; no re-labels (Nov 7 ~23:40 PST)
- `vialcheck-retro --pose r0`: 0/10 pass (union IoU 0.58-0.75; N04-R0 had 0.02-0.47). The overlays show the projected
  targets on the real tubes (centre errors mostly 2-7 px, at most 12 px; N04-R0 15-17 px in every trial).
- Two ways the check fails on well-placed tubes in this view: (1) where two tubes touch in the image (N04B-001, 005,
  007, 009) they form one changed patch, which is given whole to one target (about 10,000 px; the other tube gets 0);
  (2) the changed patch of a single tube is 20-40 % larger than its silhouette (shading on the mat), which caps the IoU
  near 0.75-0.8 even for an exact placement, so the 0.7 rule fails on small offsets.
- No N04B-R0 trial is re-labelled on these flags. The live check gates every R1-type trial (pose s1, `--checks block`),
  so it must be decided before R1: fix the check (split patches at the targets; judge position, not area) as an
  addendum item, or run with `--checks warn` (recorded). Arturo's decision.

## Judge video: seven recordings, one per trial from N04B-004 on; none found for N04-R0 or N04B-001 to N04B-003 (Nov 8 ~10:05 PST)
- Corrects "Judge recording for N04B-R0: one continuous recording, no slate" above. Arturo copied all phone recordings he
  found from the Nov 6 evening and Nov 7 night (original files by USB cable, unedited, not renamed): IMG_7452 to
  IMG_7458, now in media/real/judge/raw/20261108/. Their embedded recording times are Nov 8 07:03:38 to 07:31:45 UTC
  (69-290 s each). Each holds one trial, from the stencil placement to about 1 s after the trial's end: N04B-004 to
  N04B-010, in order.
- No recording covers N04-R0 (Nov 7 02:58-05:43 UTC) or N04B-001 to N04B-003 (Nov 8 06:33-06:56 UTC). The N04-R0
  entry above names recordings 1-3 with slates; those files are not among the seven. Arturo is checking the phone.
- Sync: each file's creation time (whole seconds), refined by the arm's rise at t_launch. The correction is +2.4 to
  +3.2 s on all seven, one phone-clock offset within the 1 s rounding.
- Five recordings stop 0.8-1.5 s after t_end, inside C 4.2's 3 s post-roll; those clips end with the recording
  (post_roll_s in the logs).
- Tool fix before the cut: tools/cut_judge_clips.py did not apply the phone's portrait rotation flag, so its motion scan
  found no onset. Logs: results/real/judge_clips_N04B-R0_IMG_7452.json to _IMG_7458.json; clips in
  media/real/judge/clips/.

## S1 not inside E row 22; accepted at its measured pose (Arturo, Nov 8 ~11:45 PST)
- S1 was set toward the sim's render point with the sled HUD (`calib/pose.py hud --target s1`, from ~11:00 PST with the
  new `--ghost` overlay). By hand through the roof hole it could not be brought inside E row 22 (3 mm, 0.5 deg).
  Arturo accepted it with the angles within about 1 deg and the positions about 13-15 mm off.
- X2 (5 sled seatings, new seating method): s1_p1 to s1_p5, RMS 0.153-0.177 px, 35 corners each; mean
  `results/poses/s1.json`: lens C_E (0.1526, 0.3437, 0.4757) m, depression 55.00, heading -81.58, roll 1.94 deg;
  spread pos SD [0.41, 0.14, 0.16] mm, depression 0.010, heading 0.085, roll 0.032 deg (inside B 4.2).
- S1 minus the sim render point (B 1.3): depth +15.0 mm (toward the back wall), lateral +14.0 mm (toward the camera
  wall), height -12.9 mm, tilt down +0.73, pan -0.38, roll +0.35 deg (24.2 mm and 1.01 deg in all).
- Everything downstream uses the measured S1 (`hud --base s1` for R4/R5, the rack and tube checks, E3's reference).
- Sim comparator: new cell S1_measured_c920 (the sim at the measured S1 with the C920 focal; `sim/make_s1_cell.py`,
  `results/h4/cells_s1.csv`), pre-registered in addendum entry 2 before R1; run after the last real trial of Nov 8.
- Earlier reads during the set-up (same code as the HUD): 10:26 x +25.9, y +23.2, z -42.9 mm, tilt -8.48, pan -0.78
  deg; 11:21 x +15.8, y +14.4, z -14.6 mm, tilt +0.08, pan -4.90, roll -5.81 deg (the camera turned while it was
  moved); then pan and roll corrected with the ghost overlay.

## Servo bus drop at connect, Nov 8 ~12:20 PST (home move before D01's retake; not a trial)
- `real/start_pose.sh` failed right after connecting: "Failed to sync read Present_Position ... Incorrect status packet",
  torque left on. Arturo unplugged the 12 V and the USB and plugged them back; health check PASS twice (20:20:40 and
  20:21:42 UTC: all six servos, 12.4-12.5 V, up to 36 C, status 0); the home move then worked.
- D01's clean photo was retaken with the arm at home (the first attempt had the folded arm turned left at the base; quit
  at the second prompt, nothing saved). D01's ground truth agrees with the X2 mean s1 within 0.33 mm / 0.06 deg.

## G1 reference N04-G1_R1 re-taken in the night trial lighting, Nov 8 ~23:12 PST (before any G1 trial)
- The reference taken at 13:25 PST (daytime) failed N04-011's pre-trial checks three times at 22:55, 22:59 and 23:00
  PST (prestart aborts, I0, not trials; results/real/prestart.jsonl): light ratio 0.90-0.94, clean view with large
  changed areas, drift 2.5-2.9 px, rack centroid 2.2-3.1 px (yellow area 28,594-31,513 px against 35,027).
- Cause: the light falls differently, not a moved scene. With the camera lock reading back 0 both times, the left of
  the image was 25-30 % darker than at 13:25 and the right floor and wall up to 1.5 times brighter. The daytime frames
  were steady from 12:29 to 13:25 (DEV D01-D04 and the reference, within 2-3 %); tonight's frames match the Nov 6-7
  night references (right side brighter than left). What differs in the daytime is not known; Nov 6 had the same
  difference (N04-R0_R0 re-taken in the trial lighting at 18:3x PST).
- Scene unchanged: the mat-edge check (independent of the light level) read 0.2-0.3 px; tools/scene_check.py --pose s1
  on the saved frames put the rack at +1.7 / -1.3 mm, turn +2.33 deg (13:25) and +2.0 / -1.5 mm, turn +2.08 deg
  (23:00). The 2.8 px drift and the rack centroid fail come from the brightness-based alignment and the yellow mask
  under the changed light.
- Re-take (Arturo): tubes out, live scene_check --pose s1 +2.0 / -2.3 mm, turn +2.58 deg (IoU 0.975); then
  `trial_runner.py reference --tag N04-G1_R1 --replace --ignore-from N04-G1_R1_1325_day_20261109T070521Z`: 20 frames,
  drift noise SD 0.009 px, pixel SD median 1.59, ignore 40.9 % (mask identical to the 13:25 one), rack 28,670 px;
  tube masks tubes_L00-L09 unchanged (same camera pose). The 13:25 copy is kept as
  media/real/refs/N04-G1_R1_1325_day_20261109T070521Z.
- Rack in the new reference (scene_check on its median): +2.0 / -2.0 mm, turn +2.33 deg, so up to 0.7 mm in E y from
  the 13:25 reference (the tubes were lifted out next to it); mat edges within 0.6 px of the 13:25 and 23:00 frames
  measured directly (scene_check's far-edge line, 11 points at S1, moved 4 mm at one end between reads and is not used).

## Mat check at S1: the far edge is not used (Nov 8 ~23:20 PST, before any G1 trial)
- Registered (entry 1, 8b): the three mat edges visible in the front view (back, front, far), each within 1.5 px of the
  reference; an edge that cannot be found fails.
- At S1 the far edge's search window (the R0 view's columns 430-496, rows 55-125) lies wholly inside the arm's ignore
  zone (rect 355,45,640,345) and does not contain the mat's far edge: the points it finds are on the wrist camera's
  black cable (rows 116-123 in the new reference, 15 of 23 lines; 9 in N04-011's frame at 23:15 PST, where the cable
  hangs slightly differently). The L04 tubes do not reach this window. With the 13:25 reference the cable lay below the
  window, so "reference: far edge not found" skipped the whole mat check, back and front included.
- N04-011 prestart abort 4 (23:15 PST, I0, not a trial): clean view, light 1.004, drift 0.40 px and rack 0.14 px pass;
  mat back (0.08, 0.06) px, front (-0.03, -0.07) px; far n 9 "edge covered or moved" -> fail.
- Change (Arturo: front and back only): real/trial_runner.py mat_check does not use an edge whose search window lies
  wholly inside the reference's ignore zones (recorded as used: false); the pre-trial check, the post-trial mat
  measure and tools/recover_trial_record.py pass the reference's ignore mask. At S1 this drops the far edge only (back
  window 56 %, front 26 % inside the ignore zones); at R0 the far window is 65 % inside, so R0 references keep all
  three edges (unit test). Thresholds unchanged. Tests: tests/test_trial_runner.py 69/69 (new: S1 far edge not used,
  back/front pass on N04-011's frame, a 2 px shift still fails; R0 with its ignore mask still uses the far edge).
- Runner sha256 from here on: 18aa8af2a3cced692ad91e0a5610ba9b324fd17454a76ba7f2c93bbb6fed8301 (in each trial record). To be reported in addendum entry 3.

## N04-011's start: tube placement aid and the door corner in the ignore zone (Nov 8 ~23:45 PST, before N04-012)
- N04-011 ran at 23:36 PST (F, F5, wall_contact) after 9 more prestart aborts (I0, not trials) after the mat fix:
  tube check 3 times (vial_3 along +8.2, +7.9, then +14.0 mm after a nudge away from the robot); clean view 4 times on
  the top-right corner (x 611-640, y 0-39, 188-234 px) after the door was re-seated; clean view once at the
  bottom-right (x 545-640, y 345-480): the wrist camera in view, arm not at home (a real catch; unchanged).
- Tubes: the stencil is registered on the mat (u from its front edge, v from its right edge; tools/make_stencils.py).
  At S1 the mat's front edge is +6.7 mm in E x at the right corner and turned 1.44 deg (scene_check), so a
  stencil-placed tube is off along its axis by about +6.7 - 0.025 v mm (v = mm from the mat's right edge): L04
  predicted +2.8 / +0.5 / +4.9 mm, observed +3.2 / -1.2 / +8.0 mm (the hand's scatter on top). Tube targets and the
  7.5 mm limits unchanged. New aid: calib/vial_view.py, the runner's own tube check (same code, reference and pose)
  on the live camera, per tube in mm and the slide that removes it; on N04-011's saved frames it gives the runner's
  numbers (e.g. vial_3 +14.0 mm -> slide 14.1 mm toward the robot).
- Door corner: the image's top-right corner shows the door edge and the t-shirt outside the box, which change at every
  door re-seat. Added to N04-G1_R1's ignore zone: rect x 600-640, y 0-45 (ignore 40.9 -> 41.5 %; previous mask kept as
  ignore_mask_before_20261109T074403Z.png; meta.json ignore_updates). N04-011 ran with the previous mask. Re-check
  with the new mask on N04-011's frames: the 4 corner aborts pass all checks; the arm-not-home frame still fails.
- Both apply from N04-012.

## Flags second_vial_attempt and rack_pushed_mm=3.5 added to N04-018 attempt 1, 2026-11-09 UTC
- The operator scored S and left the flags out of the form (trial note: tube 1 grasped and seated, the placement pushed
  the rack; tube 2 grasped, seating failed). Added at the operator's request, logged in the record under `flag_edits`;
  audit copy `trials.jsonl.pre-n04018-20261109T092436Z`; the record as first written is in gtc 2b6fcbd. Outcome S
  unchanged.
- rack_pushed_mm from the saved frames, pre_front.png against post_front.png, the rack's centre on the mat lifted at
  mid rack height with pose s1: 3.9 mm (the runner's yellow mask), 3.3 mm (filled outline), 2.9 mm (rack model fit,
  tools/scene_check.py), mostly toward the camera wall; turn 3.3-3.5 deg clockwise seen from above, so the corners
  nearest the robot moved up to about 8 mm. Recorded as 3.5 (C 1.4: an estimate). In post_front.png the seated tube
  and the tube leaning on the rack's left face cover parts of the rack, hence the spread between methods.

## Judge video for G1: ten recordings, one per trial; clips cut (Nov 9 ~02:00 PST)
- Ten phone recordings (IMG_7462 to IMG_7471, originals by USB, not renamed) filed by their embedded creation time
  under media/real/judge/raw/20261109/ (UTC date). One per trial, N04-011 to N04-020 in order; every G1 trial has video.
- Sync: creation time (whole seconds) refined by the arm's rise at t_launch. These recordings start 2-6 s before the
  launch, so the onset search uses 1 s of stillness and a +-6 s window (tools/cut_judge_clips.py --still-s 1 --scan-s 6;
  the default 4 s / +-20 s window, mostly policy motion in a short recording, put the threshold above the rise). The
  correction is +2.46 to +3.17 s on eight recordings (median +2.63; Nov 8: +2.4 to +3.2 with the same phone).
- N04-015 and N04-016 start too close to the launch for the onset search; their start is the creation time minus the
  median +2.63 s (consistent with the rise seen 1.1 s into IMG_7466 and already under way at the start of IMG_7467).
- Clamps (new in the tool: a recording that starts inside the 2 s lead or during the 3 s rise is cut from its start):
  N04-015 starts 1.12 s before t_launch, N04-016 0.23 s after it (the policy phase is whole in both). Four recordings
  stop inside the 3 s post-roll: N04-011 (1.88 s), N04-014 (1.32 s), N04-019 (2.38 s), N04-020 (1.09 s).
  Logs: results/real/judge_clips_N04-G1_IMG_7462.json to _IMG_7471.json; clips in media/real/judge/clips/.

## N05-C reference taken five times before N05-001; tubes in view in the early takes (Nov 9, 08:54-09:24 PST)
- `real/trial_runner.py reference --tag N05-C_R1` ran five times (results/real/checks.csv, clean_ref rows): 08:54:38,
  08:56:35, 09:17:58, 09:22:48 and 09:24:45 PST. Each take overwrote the one before, so only the last take's files
  remain (media/real/refs/N05-C_R1: meta.json utc 17:24:45Z, rack 29291 px). The operator recalled four takes.
- Operator's account (Arturo): the early takes had the tubes lying on the mat, in view; the take that first carried the
  note "tubes out of view" was wrong (tubes still in view) and was replaced. That note first appears on the 09:17:58
  take, which was replaced at 09:22:48, and that take again at 09:24:45. No image of the earlier takes is kept, so
  their tube state rests on the account. No runner check ran against the 09:17:58 or the 09:22:48 take.
- The tube check compares the pre-trial frame with the reference, so tubes in the reference lower the tube cover. The
  prestart aborts at 09:06:16, 09:08:26 and 09:10:33 PST (I0, not trials) ran against the 08:56:35 take and failed
  on cover: vial_2 0.83 / 0.83 / 0.83, vial_3 0.79 / 0.77 / 0.77 (limit 0.85).
- N05-001 to N05-003 ran against the 09:24:45 take, tubes out of view (each record's reference rack area is 29291 px,
  as in meta.json); their tube covers were 0.98-1.00.
- The other N05-C prestart aborts: 09:27:43 N05-001, robot connect failed ("Failed to write 'Lock' on id_=2 ... There
  is no status packet!"; N05-001 launched at 09:30:34 on the next try); 09:53:58 N05-003, tube check (vial_3 11.9 mm
  across).
- From now on every block reference is taken with the tubes out of view.

## Robot base turned 2.6 deg in N05-012 after a base clamp came off; put back before N05-013 (Nov 9, 11:08-13:18 PST)
- N05-012 (R2, L01; policy start 11:08:03.7 PST): the gripper opened over the rack between 11.8 and 12.4 s (steps log)
  and the tube was scored seated live (S, held 2 s). The arm then pushed the other two tubes away, turned right, knocked
  off one of the two clamps that hold the robot base and kept turning until it touched the black wall; the operator
  pressed f at 46.2 s (the record's note; flags wall_contact, second_vial_attempt). The clamp was put back before the
  check below.
- C has no rule for a base clamp. E G2: clamps are re-tightened each morning, never between trials of a block. A J1:
  the robot's position is checked again after any re-clamp. The check was one sled seating against s1, with limits set
  before it: each position 1.5 mm, pan 0.3 deg, tilt and roll 0.2 deg (9 single seatings at S1 on Nov 8 were within
  0.9 mm and 0.17 deg of s1).
- Sled checks (`calib/pose.py measure` + `diff s1`; results/poses/): 11:24:49 PST s1_check_n05012: pan -2.81 deg,
  lateral -9.6, depth +14.7, height -0.9 mm, tilt +0.01, roll -0.16 deg; 11:27:01 PST s1_check_n05012_b: pan -2.57 deg,
  lateral -10.5, depth +13.2, height -0.3 mm, tilt +0.09, roll -0.00 deg. As a base move (`calib/base_view.py`): turned
  +2.68 / +2.57 deg counter-clockwise seen from above; the pan axis moved 1.2 / 1.9 mm (a turn about a point near it).
- When (`tools/base_shift_frames.py`, saved frames only, each against N05-012's first frames;
  results/rig/base_shift_frames.json and .png):
  - wrist camera at the start pose (mat edges, after the start pan and wrist-roll readings): N04-011 to N05-012 within
    0.29 deg of base turn; the measured turn would show as 25 px;
  - front camera, arm at the start pose (camera drift and start-joint differences taken off): within 1.3 px (0.9 mm);
    the measured move would show as 2.9 px (2.0 mm);
  - front camera, the base's left flange (image rotation): -0.7 to +1.1 deg in the D01-D04 photos of Nov 8 (12:29-13:11
    PST, sled seated, base at s1), the block references and every trial's pre-trial and start frames up to N05-012's
    first frame. In N05-012 it steps from +0.46 deg at 24.1 s (chunk 37) to -2.30 deg at 28.7 s (chunk 44), pan 41 to
    54, and stays at -2.0 to -2.7 deg to the end; the measured move gives -2.08 deg. In the other 16 trials' keyframes
    with the arm turned right as far (pan >= 40), the same reading is -0.3 to +1.6 deg.
  - So the base turned in N05-012 between 24.1 and 28.7 s after the policy start (11:08:28-11:08:32 PST), about 12 s
    after the tube's release. No earlier trial is affected.
- The runner's drift check does not see the base (it lies in the references' arm zone), and the rack is placed against
  the camera image, so the pre-checks would not have stopped a trial after the move. No trial ran between the move and
  the re-placement below (no record or prestart abort after N05-012).
- Put back: the base was turned back with the sled seated and `calib/base_view.py` live (last reading 13:16:43 PST,
  within the limits; results/rig/base_view_last.json), and checked with both clamps re-tightened by two seatings:
  13:16:57 PST s1_check_n05012_c: pan +0.07 deg, lateral +1.3, depth -1.0, height -0.9 mm, tilt +0.01, roll +0.08 deg;
  13:18:02 PST s1_check_n05012_d: pan +0.00 deg, lateral +0.6, depth -0.7, height -0.8 mm, tilt +0.00, roll +0.08 deg.
  Both within the limits (as a base move: turned +0.00 / +0.06 deg, pan axis 1.5 / 1.1 mm from s1).
- N05-012's record and live score are not changed. The block references N05-RACK_R1 and N05-RACK_R2 are kept.
- Before N05-013 (rack set with plate Y3, then `calib/rack_ref_view.py --ref N05-RACK_R2`): door off, 13:34:54 PST: rack
  0.99 px PASS, drift 3.07 px FAIL, clean view FAIL, light 1.104; door on, 13:47 PST (operator's reading; that frame
  was not kept): rack 2.56 px FAIL (being nudged), drift 2.83 px FAIL, clean view FAIL, light 0.974, mat PASS.
  - Cause, from the 13:34:54 image (next bullet) against the reference (`calib/drift_check.compare`): since
    N05-012's f the arm rested in another pose, hanging at the right edge with the
    wrist camera below the reference's arm zone (x 112-640, y 0-345), where the drift and clean-view checks count it
    as fixed scene. With the robot and the rack left out of the fit, the drift reads 0.86 px, as at N05-012's
    pre-check (11:07 PST, 0.89 px), and the mat edges read 0.31 / 0.08 px: the camera had not moved. Clean-view blobs:
    the hanging arm (x 482-640, y 345-480) and, with the door off, surfaces 18-37 % brighter (the white area left of the
    mat, the rack's faces and holes, a strip by the door edge).
  - That image, results/rig/rack_ref_view_20261109T213453Z_frame.png, is not the original saved frame: it was restored
    from our analysis image. rack_ref_view keeps only the view on quit (results/rig/rack_ref_view_last.png and .json),
    and the 14:05 quit overwrote the 13:34:54 save. The analysis image (reference, view and difference side by side)
    was made from that save at 13:51 PST; the image was cut from it at 14:08 PST, after its reference panel was checked
    equal to N05-RACK_R2's reference pixel for pixel. It is the view's camera panel, so it carries the view's green and
    magenta rack outlines (1,307 px, all at the rack: x 106-324, y 249-471). It reads 3.13 px with the runner's mask
    (the view recorded 3.07 px for the frame itself; that .json, read at 13:51 PST, was overwritten too) and 0.86 px
    with the robot and the rack left out.
  - The arm was returned to its usual rest by the course home move (`real/hold_home.sh`: start pose, home pose, torque
    off, as at the end of every trial) and the rack re-placed to AIM, door on: 14:04 PST rack 0.56 px, turn -0.11 deg,
    drift 0.55 px, clean view PASS, light 1.007, mat PASS (last frame on quit, 14:05:13 PST: rack 0.49 px, drift
    0.54 px, light 1.009; results/rig/rack_ref_view_last.json). No retake: N05-RACK_R2 is kept for the rest of the
    block.

## Checkpoint after the last N05-RACK trial: the M1 cycles move to the end (Nov 9, 15:17-15:29 PST; entry 3)
- Rule (entry 3, "Protecting the camera blocks", decided 09:05 PST): pace = (the last N05-RACK launch - N05-001's
  launch) / (launches - 1); each later row is launched one pace after the one before it; each M1 cycle and each camera
  setup before a row adds 40 and 45 min; the meal time not yet taken is left out of the window. If a row of N06-CAM1,
  N06-CAM4 or N06-CAM5 would not start by 20:30 PST in the current order, N05-M1C1-E3 and N05-M1C2-E3 move as whole
  blocks to the end, after N06-M2C2-E3.
- Launches (`t_launch`, results/real/trials.jsonl): N05-001 09:30:34 PST, N05-024 (the last N05-RACK trial) 15:16:45
  PST; 15 launches (N05-C 3, N05-RACK 12), 14 intervals, 346.2 min: **pace 24.73 min**. The span includes the base
  incident (N05-012 launched 11:07:54, N05-013 14:14:35 PST: 186.7 min); the rule is applied as written.
- Current order (N05-M1C1-E3, N05-M1C2-E3, N06-C, N06-C2, then the camera blocks; 2 M1 cycles and 3 camera setups):
  the first N06-CAM1 row (N06-004) at 23:57 PST, the last N06-CAM5 row (N06-023) at 05:09 PST Nov 10; none of the 10
  camera-block rows starts by 20:30, with 0 or with all 60 min of meals still to take. **The move applies.**
- Applied: N05-M1C1-E3 and N05-M1C2-E3 moved as whole blocks to the end, after N06-M2C2-E3; rows unchanged, 80 rows
  (gtc cb83c80). `config/schedule.csv` SHA-256 **cd776ae4b5e0ddb16bee1005e15c573a1870f8461298424cb277c806699f4397**
  (was 2cf3bebc5b0bca11f4921fa506e0aed57e8588dd8a298dfb023df6cf01f1e65a). Run order: N06-C, N06-C2, N06-CAM1,
  N06-CAM4, N06-CAM5, N06-M2C1-E3, N06-M2C2-E3, N05-M1C1-E3, N05-M1C2-E3; the camera is returned to S1 before the M1
  cycles if they are reached. Next row: N06-001 (N06-C, R1, L02).
- For information only (not used for the decision):
  - Without the N05-012 to N05-013 interval the pace is 12.27 min (159.5 min over 13 intervals). In the old order the
    first N06-CAM1 row would start at 20:38 PST, so the move would apply at that pace too.
  - Moved order, projected the same way (a return to S1 before the M1 cycles counted as one camera setup): at 24.73 min,
    N06-CAM1 starts at 18:30 PST and 4 of the 10 camera-block rows start by 20:30 (3 with 60 min of meals still to
    take); at 12.27 min, 9 (8). The stop rule decides by the actual launches.

## Judge video for N05-C, N05-RACK, N06-C and N06-C2: one recording per trial; IMG_7481 and IMG_7486 not copied (Nov 9, 15:33 and 16:30 PST)
- Twenty phone recordings (IMG_7473 to IMG_7494 without IMG_7481 and IMG_7486; originals by USB, not renamed) filed by
  their embedded creation time (UTC date) as for G1: media/real/judge/raw/20261109/ (IMG_7473 to IMG_7491) and
  20261110/ (IMG_7492 to IMG_7494, made after 16:00 PST). Moved only: SHA-256, size, time stamp and inode checked equal
  before and after.
- One recording per trial; every trial of the day has video: N05-001 IMG_7473, -002 7474, -003 7475, -004 7476, -007
  7477, -010 7478, -011 7479, -012 7480, -013 7482, -015 7483, -016 7484, -018 7485, -022 7487, -023 7488, -024 7489;
  N06-001 7490, -002 7491, -003 7492, -016 7493, -017 7494. No recording is left over.
- Coverage, from the creation time less 2.63 s (G1's median; about +-0.5 s until the motion refinement when the clips
  are cut): every recording runs from before t_launch to after t_end. Starts inside the 2 s lead: N05-016 (0.3 s
  before t_launch), N06-002 (0.6 s). Stops inside the 3 s post-roll: N05-001 (1.3 s after t_end), N05-002 (0.7),
  N05-003 (2.6), N05-004 (1.5), N05-012 (1.3), N05-015 (2.4), N05-022 (0.6), N06-001 (1.4), N06-002 (0.7). Clips not
  cut yet.
- IMG_7481 and IMG_7486: numbers skipped in the copies; the operator cannot check them on the phone. IMG_7481 falls
  between IMG_7480 (N05-012, created 11:07:52 PST) and IMG_7482 (N05-013, 14:14:31 PST), the base-incident interval.
  IMG_7486 falls between IMG_7485 (N05-018, 14:36:53 PST) and IMG_7487 (N05-022, 14:58:08 PST); N05-022's prestart
  abort at 14:57:13 PST (connect failed; not a trial) lies in that span. What either holds, or whether it exists, is
  not known. No trial lacks a recording, so neither is needed for scoring: they are not sought further and are not
  part of the judge record. If they turn up, they are kept as they are and not used for scoring.

## N06-CAM1 camera setting (R4, tilt down 6.0 deg from s1): first setting 5.9 mm low (over the 5 mm I4 limit), re-set as cam1b; reference N06-CAM1_R4 (Nov 9, 16:34-18:38 PST)
- Before the move (N06-C2 done, arm at rest): the rack read at S1 with the door on and the tubes out
  (`tools/scene_check.py --pose s1 --target 1.2,-3.0,2.58`, 16:34:42 PST; results/rig/scene_check_s1_before_cam1.json):
  +2.4 / -2.5 mm, turn +1.91 deg (OK against N05-RACK_R1's reading). The rack was then taken out (the sled board
  covers its place).
- Sled seated; `calib/pose.py measure --tag cam1_before` (16:41:35 PST, RMS 0.173 px); camera set with
  `pose.py hud --base s1 --offset tilt_down_deg=6.0 --tol-mm 2 --tol-deg 0.3 --ghost`; `measure --tag cam1` (17:08:48
  PST, RMS 0.165 px); results/poses/cam1_before.json and cam1.json, 35 corners each.
  - cam1_before - s1: tilt_down +0.05, pan -0.06, roll +0.03 deg, lateral +0.9, depth -0.6, height -0.8 mm (within the
    Nov 9 sled limits: camera and base unchanged since S1).
  - cam1 - s1 (the level's ground truth, E section 3 and row 22): tilt_down +5.77, pan +0.17, roll -0.07 deg, lateral
    +2.1, depth -0.5, height -5.9 mm (total rotation 5.78 deg).
  - cam1 - cam1_before (bracketed, one seating): tilt_down +5.72, pan +0.22, roll -0.09 deg, lateral +1.2, depth +0.1,
    height -5.1 mm.
- Against the registered limits: the tilt is 0.23 deg under the level, inside +-0.3 deg (E row 22, v2 item 5); pan and
  roll are within 0.3 deg. Position: v2 item 5 and C D4 make a setting more than 1.0 deg or 5 mm off target invalid
  (I4). The HUD's target keeps the s1 lens position, and the lens is 5.9 mm below it, so this setting is outside that
  limit. The setting instructions for this step said the mm were logged and not judged (B 6 expects a few mm of lens
  shift from the hinge); that missed the 5 mm limit. No reference has been taken and no trial has run at this setting.
- Cross-check of cam1: the mat's front edge read through cam1 (17:16:30 PST) at +0.1 / +6.6 mm, turn -1.29 deg, and
  through s1 (16:34:42 PST) at -0.0 / +7.2 mm, turn -1.44 deg.
- Rack back at R1 with plate N, then `scene_check --pose cam1 --target 2.4,-2.5,1.91` (17:16:30 PST;
  results/rig/scene_check_cam1.json): +2.9 / -2.8 mm, turn +1.74 deg (against the S1 reading +0.5 / -0.3 mm,
  -0.17 deg; OK).
- `real/trial_runner.py reference --tag N06-CAM1_R4 --draw` (17:18 PST) stopped at the zone drawing: the .venv's
  OpenCV 4.10.0 is built without a GUI (cv2.selectROIs: "The function is not implemented"). It wrote nothing but an
  empty folder, media/real/refs/N06-CAM1_R4 (made before the drawing step), and no checks.csv row. The folder is kept;
  the next take writes into it with --replace.
- Ignore zones without drawing, built as at S1 (one arm rect, then all layouts' tubes grown by 12 px with
  `tools/ignore_zone_check.py --write-mask`): S1's arm rect (x 355-640, y 45-345) mapped into the cam1 view with the
  two measured poses, for points 0.25 m from the lens to infinity, is x 353-640, y 0-282; it is used as x 350-640,
  y 0-285. In the cam1 image (scene_check_cam1.png) it holds the arm at rest, the wrist camera and its cable with about
  35 px to spare, and the top-right corner (S1's door-corner rect maps out of view). The same rect holds with the lens
  at the s1 position or 6 mm higher (bottom edge 282 in both).
- Re-set, before any reference or trial at cam1: rack out, sled seated with the camera still at cam1, the same HUD
  (`--base s1 --offset tilt_down_deg=6.0`, per-axis aim 2 mm, required within 5 mm each and the angles within 0.3 deg),
  camera moved and tightened; `measure --tag cam1b` (18:31:29 PST, 20 frames, 35 corners, RMS 0.180 px;
  results/poses/cam1b.json).
  - cam1b - s1: tilt_down +5.74, pan -0.17, roll -0.27 deg, lateral +4.1, depth +4.2, height -4.1 mm (7.2 mm as a
    distance).
  - cam1b - cam1_before: tilt_down +5.69, pan -0.11, roll -0.29 deg, lateral +3.1, depth +4.8, height -3.4 mm (6.6 mm).
  - cam1b - cam1: tilt_down -0.03, pan -0.34, roll -0.20 deg, lateral +1.9, depth +4.7, height +1.8 mm.
  - Not bracketed: the sled was re-seated for the re-set and nothing was measured in that seating before the camera
    moved (the steps given did not ask for it), so cam1b has no one-seating delta. Between two seatings at the same
    camera setting the tilt read +0.05 deg (cam1_before - s1).
- cam1b against the registered limits:
  - Tilt 0.26 deg under the level against s1 (inside +-0.3 deg) and 0.31 deg under against cam1_before (0.01 deg
    outside); neither reading is from one seating. Pan and roll within 0.3 deg. All angles far inside the 1.0 deg I4
    limit.
  - Position: each axis within 5 mm (largest 4.2 mm against s1; 4.8 mm in depth against cam1_before), so not I4 with
    the 5 mm read per axis, as v2 item 5 states the 3 mm R1 limit ("per axis"). v2 does not say "per axis" on the I4
    line. As a distance the lens is 7.2 mm from the s1 position (cam1: 6.3 mm); recorded for information.
- Rack at R1 with plate N, then `scene_check --pose cam1b --target 2.4,-2.5,1.91` (18:36:02 PST;
  results/rig/scene_check_cam1b.json): +2.1 / -2.8 mm, turn +2.24 deg (against the S1 reading -0.3 / -0.3 mm,
  +0.33 deg; OK). The mat's front edge through cam1b: -0.1 / +6.2 mm, turn -1.26 deg (cam1: +0.1 / +6.6, -1.29).
- Reference N06-CAM1_R4 (18:37:15 PST) into the kept folder, ignore rect 350,0,640,285 from the command line: 20
  frames, drift noise SD 0.010 px, pixel SD median 1.55, ignore 26.9 %, rack 29,740 px (N06-C_R1 29,550; N06-C2_R1
  29,346); checks.csv line 19 (clean_ref, True). `tools/ignore_zone_check.py --ref N06-CAM1_R4 --pose cam1b
  --write-mask` (18:37:28 PST): 30 of 30 tube placements outside the zone before, ignore 26.9 % -> 38.0 % (the mask
  before kept as ignore_mask_before_20261110T023728Z.png); run again: 0 of 30 outside.
- The reference files, checked before the first trial: the median frame shows the rack, mat and arm at rest, with no
  tubes or hands. The rack's yellow mask covers the whole rack (ref_check.png). The arm rect holds the arm, the wrist
  camera, its cable and the wrist camera's shadow. The tube zone covers the mat beyond the rack up to the image's top
  edge and overlaps the rack's top back edge; the runner's rack check does not use the ignore mask, only the
  clean-view and mat checks do.

## N06-CAM1 closing reading over the 5 mm line in depth (the camera did not move; base or sled seating); N06-CAM4 setting (Nov 9, 18:47-19:28 PST)
- CAM1 trials, launches (PST): N06-004 18:47:01 (time cap, F1), N06-005 18:57:00, N06-006 19:01:08, N06-007 19:05:35
  (each F5: the arm turned right until it touched the black wall; operator pressed f). All live F.
- Closing reading (C, camera day: "PnP in and out"): sled seated, camera untouched since CAM1,
  `measure --tag cam4_before` (19:13:19 PST, 35 corners, RMS 0.151 px).
  - cam4_before - cam1b: tilt_down +0.01, pan -0.29, roll -0.15 deg (total rotation 0.17 deg), lateral -0.3,
    depth +2.1, height +0.3 mm.
  - cam4_before - s1: tilt_down +5.75, pan -0.46, roll -0.42 deg, lateral +3.8, depth +6.3, height -3.9 mm.
- Camera or base (saved frames only):
  - Camera: the runner's drift estimate (`drift_check.compare`, static region of N06-CAM1_R4) in every CAM1 trial's
    pre-trial frame is 0.21-0.59 px (limit 1.5 px) and in its post-trial frame 0.50-0.67 px, image rotation at most
    0.04 deg; the mat edges after each trial 0.35-0.40 px. The same 0.17 deg and 2.1 mm as a camera move would shift
    the walls and mat by 1.3-1.5 px (median) and up to 2.0-2.2 px. The camera did not move during the block.
  - Base: with the camera fixed, the change is a base turn of 0.16 deg counter-clockwise seen from above with the pan
    axis moved 0.7 mm (`calib/base_view.base_move`). In the front frames that moves the base by about 0.5 px (at most
    0.8 px), inside the scatter of the base flange reading (already 0.6 px off the reference in N06-004's pre-trial
    frame); not resolved there. Wrist camera at the start pose (`tools/base_shift_frames.py` series B with its N05 fit,
    residual SD 0.83 px = 0.09 deg), against N06-004: N06-005 +0.03, N06-006 -0.13, N06-007 -0.08 deg; a 0.16 deg
    counter-clockwise turn before N06-006 or N06-007 started would read about +0.16 (the 0.7 mm shift is not modelled).
  - Sled seating: X2's five seatings at S1 (s1_p1-p5) spread over pan 0.24 deg, roll 0.09 deg, depth 1.1 mm. The
    in-to-out change is a little larger.
  - So the change is in the sled and base frame, not the camera. A base turn of that size before N06-006 or N06-007
    started is not seen in the wrist frames, at about their resolution. A base move during N06-007's wall contact or
    at the 19:13 seating, and seating alone, cannot be told apart from the frames.
- Against the registered limits:
  - Per-trial drift (v2 item 5, max(1.5 px, 3 SD)): every CAM1 trial passes, before and after the trial.
  - I4 (C D4, v2 item 5: more than 1.0 deg or 5 mm off target; per axis): the opening reading (cam1b) passes (largest
    4.2 mm); the closing reading does not (depth 6.3 mm; the angles pass). C D4 re-labels "those trials" invalid I4
    when a PnP is over the line; the frames do not date the change, so read as written it covers N06-004 to N06-007.
    Whether they are re-labelled is Arturo's decision, pending; no trial record has been changed.
- CAM4 setting, as done by the operator: from where the camera was, loosened and adjusted (position, pan and roll)
  with `pose.py hud --base s1 --offset tilt_down_deg=6.0` until the angles were green and each mm under 5; it was not
  first tilted away (the steps given asked for tilting it up to about +3 first). `measure --tag cam4` (19:22:42 PST, 35
  corners, RMS 0.156 px; lens C_E (0.1559, 0.3460, 0.4721) m; depression 60.76, heading -81.77, roll 2.07 deg).
  - cam4 - s1: tilt_down +5.76, pan -0.20, roll +0.13 deg, lateral +2.3, depth +3.4, height -3.6 mm (5.5 mm as a
    distance). Tilt 0.24 deg under the level (inside +-0.3 deg); pan and roll within 0.3 deg; each axis within 5 mm.
  - cam4 - cam4_before (one seating, the re-set itself): tilt_down +0.01, pan +0.26, roll +0.55 deg, lateral -1.5,
    depth -2.9, height +0.3 mm.
- Fresh re-setup (C, camera day: "Every block starts with a fresh camera re-setup with the HUD, PnP in and out, and new
  references. Consecutive same-level blocks are also re-set, so each level gets 3 independent setups"): the camera was
  re-set with the HUD, with PnP in (cam4) and out (cam4_before) and a new reference, as those words ask. The tilt, the
  level itself, moved +0.01 deg in the re-set, so CAM4's tilt is CAM1's (5.76 and 5.75 deg against s1), not set
  independently; pan, roll and the lens position were re-set.
- Rack at R1 with plate N, `scene_check --pose cam4 --target 2.4,-2.5,1.91` (19:26:56 PST;
  results/rig/scene_check_cam4.json): +0.9 / -3.8 mm, turn +1.99 deg (against the S1 reading -1.5 / -1.3 mm,
  +0.08 deg; OK).
- Reference N06-CAM4_R4 (19:27:49 PST; ignore rect 350,0,640,285 as CAM1): 20 frames, drift noise SD 0.005 px, pixel
  SD median 1.55, ignore 26.9 %, rack 30,059 px; checks.csv clean_ref True. `ignore_zone_check --write-mask`
  (19:27:53 PST): ignore 26.9 % -> 38.2 %. The files, checked: no tubes or hands; the rack's yellow mask whole; the arm
  rect holds the arm, wrist camera, cable and shadow; the tube zone as at CAM1.

## N06-CAM1 trials re-labelled I4 on the block's closing reading (decision Nov 9, 19:38 PST)
- Decision (Arturo, Nov 9 19:38 PST; made after N06-018's live F, which it does not depend on): apply C D4 as written.
  N06-004, N06-005, N06-006 and N06-007 (attempt 1) are re-labelled from F (F1, F5, F5, F5) to invalid I4 on the
  closing reading (cam4_before - s1: depth +6.3 mm against the 5 mm line; entry above). R4 is reported with and without
  them: as invalid trials they are left out of the primary analysis, and an analysis with them is reported as well.
- Records (19:40:04 PST): each keeps its live score under `relabel` (from / to, reason, evidence, by), as for N04-001;
  now live_outcome I, live_fail_code empty, invalid_code I4; flags (wall_contact) unchanged. Audit copy
  results/real/trials.jsonl.pre-cam1-i4-20261110T034004Z (never deleted); trials.csv rewritten from trials.jsonl with
  the runner's write_csv; the records as first written are in gtc 344db6e. The runner's status lists the four as
  "invalid awaiting re-run" and still picks N06-019 next.
- Re-runs from the reserve (C D4): not part of this decision.

## N06-CAM4 closing check by the mean of two sled seatings; no re-runs of N06-004 to N06-007 (decisions Nov 9, before 19:59 PST)
- Decided by Arturo before the CAM4 closing readings were taken (N06-021 launched 19:54:19 PST; no cam5_before
  reading existed at 19:59:25 PST):
  1. CAM4's closing check uses the mean of two sled seatings, cam5_before and cam5_before_b (`pose.py mean`), against
     the registered limits (more than 1.0 deg or 5 mm off target, per axis: I4); both readings are reported. v2 item 5
     uses a mean of sled placements for S1 in the same way. CAM1's closing check had one seating.
  2. N06-004 to N06-007 are not re-run; they are reported as I4, not re-run.
- CAM5's closing check (decided by Arturo before any CAM5 reading; at 20:02:25 PST neither the cam5 setup reading nor
  a cam5_after reading existed): after N06-023, two sled seatings, cam5_after and cam5_after_b, and their mean against
  the registered limits (more than 1.0 deg or 5 mm off target, per axis: I4); both readings reported.

## N06-CAM4 closing check passes (mean of two seatings); the change during CAM4 is again in the sled/base frame (Nov 9, 19:35-20:04 PST)
- CAM4 trials, launches (PST): N06-018 19:35:04 (F5), N06-019 19:41:59 (F5, regrasp_n 3), N06-020 19:48:31 (F2),
  N06-021 19:54:19 (F5); each with wall_contact, ended by f. All live F.
- Closing readings, by the rule decided before them: sled seated, camera untouched since CAM4; `measure --tag
  cam5_before` (20:00:47 PST, RMS 0.173 px) and, after re-seating (operator: two seatings), `--tag cam5_before_b`
  (20:01:25 PST, RMS 0.176 px); `pose.py mean --tags cam5_before cam5_before_b --out cam4_out` (20:04:11 PST).
  - cam5_before - s1: tilt_down +5.76, pan +0.35, roll +0.60 deg, lateral +2.3, depth +1.1, height -3.3 mm.
  - cam5_before_b - s1: tilt_down +5.77, pan +0.35, roll +0.63 deg, lateral +2.3, depth +1.1, height -3.2 mm.
  - cam4_out - s1 (the check): tilt_down +5.77, pan +0.35, roll +0.62 deg, lateral +2.3, depth +1.1, height -3.3 mm.
  - The two readings differ by 0.06 mm and 0.03 deg (spread SD 0.003 / 0.001 / 0.029 mm), closer than any pair of S1's
    five seatings (0.22-1.21 mm).
- Against the registered limits (I4: more than 1.0 deg or 5 mm off target, per axis): passes. Tilt 0.23 deg under the
  level; pan +0.35 and roll +0.62 deg, over the 0.3 deg the setting aimed for and within 1.0 deg; largest position
  3.3 mm. N06-018 to N06-021 are not I4.
- Change during CAM4 (cam4_out - cam4): tilt_down +0.00, pan +0.55, roll +0.48 deg (total rotation 0.27 deg), lateral
  +0.0, depth -2.3, height +0.3 mm.
  - Camera: the drift estimate against N06-CAM4_R4 is 0.33-0.62 px in every CAM4 pre-trial and post-trial frame,
    rotation 0.02-0.03 deg; from N06-018's pre-trial frame to N06-021's post-trial frame its shift changed by
    (+0.04, -0.02) px and its rotation by 0.000 deg. The same change as a camera move would shift the walls and mat by
    about 0.5 px (median; mean vector about (+0.3 to +0.5, -0.2) px) and up to 1.6-1.75 px. The camera did not move.
  - As a base move with the camera fixed: turned -0.13 deg (clockwise seen from above), pan axis moved 0.6 mm (mostly
    up).
- The 19:13 seating (cam4_before, then cam4 in the same seating) against its neighbours, each pair with the camera
  unchanged: against 18:31 (cam1b) depth +2.1 mm and a base-equivalent turn of +0.16 deg; against 20:00 (cam5_before)
  depth +2.3 mm and +0.13 deg. The 18:31 and 20:00 seatings agree within 0.03 deg as a base turn. So the 19:13 seating
  reads about 2 mm deeper than the seatings before and after it. CAM1's closing reading (6.3 mm) and CAM4's opening
  reading (cam4) both come from that seating. The CAM1 re-label (entry above) was decided on the rule as written and
  is not changed here; this is reported with the analysis with and without N06-004 to N06-007.
- CAM5 is set from this state without first tilting the camera away (operator, for time).

## N06-CAM5 setting and closing check; the trials end; rows not run under the stop rule (Nov 9, 20:04-20:28 PST)
- CAM4's setting and closing check are recorded above (N06-CAM1 closing entry and N06-CAM4 closing entry).
- CAM5 setting: from the CAM4 end state, with the sled still seated after cam5_before_b, re-set with
  `pose.py hud --base s1 --offset tilt_down_deg=6.0`; not first tilted away (operator, for time). `measure --tag cam5`
  (20:07:04 PST, 35 corners, RMS 0.167 px).
  - cam5 - s1: tilt_down +5.91, pan -0.18, roll +0.09 deg, lateral +1.9, depth +1.4, height -3.4 mm. Tilt 0.09 deg
    under the level; pan and roll within 0.3 deg; each axis within 5 mm (largest 3.4 mm).
  - cam5 - cam5_before_b (one seating, the re-set itself): tilt_down +0.14, pan -0.54, roll -0.54 deg, lateral -0.4,
    depth +0.3, height -0.1 mm. Re-set with the HUD, PnP in and out and a new reference; the tilt moved 0.14 deg in
    the re-set (CAM4: 0.01 deg).
- Rack at R1 with plate N, `scene_check --pose cam5 --target 2.4,-2.5,1.91` (20:10:30 PST;
  results/rig/scene_check_cam5.json): +2.9 / -0.5 mm, turn +1.99 deg (against the S1 reading +0.5 / +2.0 mm,
  +0.08 deg; OK, at the edge of the 2 mm band).
- Reference N06-CAM5_R4 (20:11:31 PST; ignore rect 350,0,640,285 as CAM1 and CAM4): 20 frames, drift noise SD
  0.006 px, pixel SD median 1.56, rack 29,178 px; checks.csv clean_ref True. `ignore_zone_check --write-mask`
  (20:11:38 PST): ignore 26.9 % -> 38.2 %; run again: 0 of 30 tube placements outside (operator). The files, checked
  after the trials: no tubes or hands; the rack's yellow mask whole; the arm rect holds the arm, wrist camera and cable;
  the tube zone as at CAM1 and CAM4.
- CAM5 trials, launches (PST): N06-022 20:18:51 (F5, wall contact, ended by f), N06-023 20:23:28 (F1, time cap, no wall
  contact). Both live F.
  - Drift against N06-CAM5_R4 (limit 1.5 px): 0.92 px in N06-022's pre-trial frame (shift +0.69 / +0.45 px) and
    0.94-1.15 px in the later frames; from N06-022's pre-trial frame to N06-023's post-trial frame the shift changed by
    (-0.04, -0.13) px. Mat 0.86-1.22 px (limit 1.5). So the static scene moved about 0.8 px between the reference and
    N06-022's first frame (before the first CAM5 trial) and not during the trials. Both trials pass the drift check.
- Closing check, by the rule decided before any CAM5 reading: `measure --tag cam5_after` (20:27:03 PST, RMS 0.149 px),
  sled re-seated, `--tag cam5_after_b` (20:27:38 PST, RMS 0.146 px); `pose.py mean ... --out cam5_out` (20:27:44 PST).
  - cam5_after - s1: tilt_down +5.86, pan +0.13, roll +0.18 deg, lateral +2.7, depth +0.3, height -3.2 mm.
  - cam5_after_b - s1: tilt_down +5.85, pan +0.03, roll +0.25 deg, lateral +2.4, depth +1.1, height -3.4 mm.
  - cam5_out - s1 (the check): tilt_down +5.85, pan +0.08, roll +0.22 deg, lateral +2.5, depth +0.7, height -3.3 mm.
    The two seatings differ by 0.18 deg and 0.8 mm (spread SD 0.38 / 0.11 / 0.09 mm, heading 0.05 deg, roll
    0.04 deg).
  - Against the registered limits (I4: more than 1.0 deg or 5 mm off target, per axis): passes (tilt 0.15 deg under
    the level, largest position 3.3 mm). N06-022 and N06-023 are not I4.
  - Change during CAM5 (cam5_out - cam5): tilt_down -0.05, pan +0.26, roll +0.13 deg (total 0.17 deg), lateral +0.6,
    depth -0.7, height +0.1 mm. As a camera move it would shift the walls and mat by (+0.71, -0.34) px on average
    (median 0.81, up to 1.79 px); during the trials they moved by (-0.04, -0.13) px.
- Trials end: N06-023 was the last trial, launched 20:23:28 PST, ended 20:24:37 PST. Every trial that ran was
  launched before 20:30.
- Rows not run under the stop rule (entry 3; reported as not run, by row): 20 rows, all four E3 cycle blocks; neither
  M1 cycle was reached, so the camera was not returned to S1 for them.
  - N06-M2C1-E3 (R7): N06-034 (L08), N06-035 (L04), N06-036 (L02), N06-037 (L05), N07-005 (L00).
  - N06-M2C2-E3 (R7): N06-042 (L03), N06-043 (L07), N06-044 (L01), N06-045 (L09), N07-004 (L08).
  - N05-M1C1-E3 (R6): N05-030 (L07), N05-031 (L02), N05-032 (L09), N05-033 (L06), N07-018 (L04).
  - N05-M1C2-E3 (R6): N05-042 (L05), N05-043 (L01), N05-044 (L08), N05-045 (L00), N07-019 (L02).
  - So no closed-loop E3 trial ran (R6 0 of 10, R7 0 of 10). N06-004 to N06-007 ran and are I4, not re-run (entries
    above).
- Rows run (live scores, before blind scoring): R0 10 valid in N04B-R0, the R0 result (entry 2), and 10 valid in
  N04-R0, kept on record as "R0 with the scene offset" and not pooled (N04-001 attempt 1 I4 and re-run); R1 20, R2 10,
  R4 6 valid (N06-CAM4 4, N06-CAM5 2) plus the 4 I4 rows of N06-CAM1.

## Judge video for N06-CAM1, N06-CAM4 and N06-CAM5: one recording per trial, none for N06-004; set P not taken; every clip blind-scored (Nov 9, 22:27-22:35 PST)
- Nine phone recordings, IMG_7495 to IMG_7503 (consecutive numbers; originals by USB, not renamed), filed by their
  embedded creation time (UTC date) as before: media/real/judge/raw/20261110/. Moved only: SHA-256, size, time stamp
  and inode checked equal before and after.
- One recording per trial: N06-005 IMG_7495, N06-006 7496, N06-007 7497, N06-018 7498, N06-019 7499, N06-020 7500,
  N06-021 7501, N06-022 7502, N06-023 7503. No recording is left over and none spans two trials.
- N06-004 has no recording (recording not started; the record's note). It is blind-scored from the runner's saved front
  and wrist frames, under its blind code, marked "scored from robot frames" (Arturo; the rule entry 2 set for the R0
  trials without video).
- Coverage, from the creation time less 2.63 s (G1's median, about +-0.5 s): every recording runs from before t_launch
  to after t_end. Starts inside the 2 s lead: N06-020 (0.6 s before t_launch), N06-021 (1.3 s). Stops inside the 3 s
  post-roll: N06-005 (0.9 s after t_end), N06-006 (1.5 s), N06-019 (1.1 s). Several run on well after the trial
  (N06-021 by 492 s); the clips are cut to the trial. Clips not cut yet.
- Decisions (Arturo, Nov 9 22:30 PST, before any blind scoring):
  - Set P: not taken, for time (blind scoring starts Tuesday 07:00 PST and the poster is due Tuesday 17:00 PT). It is
    reported as not taken, and H3b as not tested. No registered cut covers set P; entry 3 had placed it after the last
    trial.
  - Blind scoring: every clip is blind-scored like every other, valid or invalid (N04-001 attempt 1 and N06-004 to
    N06-007 included), so the scorer cannot tell valid from invalid clips. The invalid code decides whether a trial
    enters the analysis, as registered.
  - Poster: no p-value on real data until the blind scores are in; live counts only, marked "live, pending blind
    scoring".

## Judge clips for every trial and the two blind batches (Nov 9, 22:40-22:41 PST, before any blind scoring)
- Phone clips (`tools/cut_judge_clips.py`, cut copies re-encoded; the 31 recordings of Nov 9 checked unchanged by
  SHA-256 after the cut): one run per recording for the 29 trials of N05-C, N05-RACK, N06-C, N06-C2, N06-CAM1,
  N06-CAM4 and N06-CAM5 with video, logs results/real/judge_clips_<block>_IMG_<n>.json. Sync as for G1: the creation
  time refined by the arm's rise (`--still-s 1 --scan-s 6`), accepted when the correction lies within 2.2-3.4 s (the
  Nov 8 and G1 range, +2.4 to +3.2 s, widened by 0.2 s; set before the cut). Accepted on 22 recordings: +2.24 to
  +3.25 s, median +2.69 s. The other 7 use the creation time less G1's median 2.63 s (`--no-motion --start-utc`), as
  for N04-015 and N04-016: no onset found for N05-016, N06-002, N06-020, N06-021 and N06-023 (each starts close to
  its launch); +2.18 s for N06-003 and +2.17 s for N06-022 (outside the window).
  - Cut from the recording's start (it starts inside the 2 s lead): N05-016 (0.25 s before t_launch), N06-002 (0.64),
    N06-020 (0.57), N06-021 (1.27). Cut to the recording's end (it stops inside the 3 s post-roll): N05-001 (1.32 s
    after t_end), N05-002 (0.80), N05-003 (2.06), N05-004 (1.69), N05-012 (1.42), N05-015 (2.56), N05-022 (0.97),
    N06-001 (1.35), N06-002 (0.68), N06-005 (0.64), N06-006 (1.41), N06-019 (0.76).
- Clips from the robot frames (entry 2; Arturo for N06-004): the 15 trial records without a phone recording (N04-R0's
  11: N04-001 attempts 1 and 2, N04-002 to N04-010; N04B-001 to N04B-003; N06-004) get their front keyframe video
  (kf_front.mp4) copied unchanged as the judge clip (SHA-256 checked equal); the wrist keyframe video is added as for
  every clip. Log results/real/judge_clips_robot_frames.json. The G1 and N04B-004 to N04B-010 clips were cut before.
  All 61 trial records have a clip.
- `tools/blind_rename.py` gains `--batch NAME` (our change, before any blind copy): each batch gets its own folder
  (media/real/judge/blind/<NAME>/), codes, sheet and sealed key (media/real/judge/sealed/, git-ignored). Without it
  the two batches would share one folder. The clips are given as `--keys`, so invalid trials are included (`--blocks`
  keeps S and F only); every clip is blind-scored (Arturo, Nov 9 22:30 PST).
- Batches (entry 3; the split by t_end before Nov 9 19:00 PST; N04B-002, whose rebuilt record has no times, is in A):
  - Batch A: 53 clips (all trials of Nov 6 to Nov 9 through N06-005), each with its wrist video; codes, sheet
    results/real/blind_scores_A_20261110T064043Z.csv; key SHA-256
    009edaf7bcbc2edbe12f27f9a46d94dd2d2ca1c0e23489d622dc7f4ad31e7547
    (results/real/blind_key_A_20261110T064043Z.sha256). Scoring from Tuesday 07:00 PST.
  - Batch B: 8 clips (N06-006, N06-007, N06-018 to N06-023), sheet results/real/blind_scores_B_20261110T064043Z.csv;
    key SHA-256 2d62a9bcd9b762736e2e454aeb70998a690eba29ef425308b998469a1ff3f683
    (results/real/blind_key_B_20261110T064043Z.sha256). Scoring from Tuesday 08:25 PST (12 h after N06-023 ended,
    20:24:37 PST), after batch A.
  - The keys were not printed or opened; they stay sealed until both batches are scored.
- Scoring convention for the blind sheets (our choice, before any blind scoring): `t_release_s` is entered as the
  clip time shown by the player (seconds from the clip's start) at release; after unblinding it is converted to time
  from the policy start with each clip's cut log (video_from_s) and the record's times. The 45-degree tilt rule
  (C 1.4) is applied by eye on borderline cases (`tilt_borderline` 1); if still unsure, F. No reference line is drawn
  on the clips.

## Addendum entry 4 released (Nov 9, 22:52 PST, before any blind scoring)
- After Arturo's review (22:45 PST), entry 4 was appended to PREREGISTRATION_v2_addendum.md in the public repo and
  pushed: commit 74a7833e9e91882ff1881536eb120aa9e3c9337b, pushed 22:52:30 PST, author and committer Arturo Morales
  Rangel. Checks as for entry 3: fetched, clean and in sync before; 123 lines added, 0 removed, one file; in sync
  after. The text is identical to gtc notes/addendum_entry4_draft.md (e7be379).

## Blind scoring of batches A and B (Nov 10, 07:38-12:06 PST); sheets committed before unblinding
- Sheets, under their issued names: results/real/blind_scores_A_20261110T064043Z.csv (53 rows; scored 15:38-19:14 UTC,
  07:38-11:14 PST) and results/real/blind_scores_B_20261110T064043Z.csv (8 rows; 19:41-20:06 UTC, 11:41-12:06 PST).
  Batch A started after Tuesday 07:00 PST and batch B after 08:25 PST and after batch A, as registered (12 h after
  each batch's last trial; entry 4).
- Checked before unblinding: the header is the registered column list (C 4.1 plus `tube_contact`, entry 2); each
  sheet's codes equal its batch folder's clips exactly, with no duplicates, in the issued order; every row has judge,
  scored_utc, outcome (S or F), hold_2s, hold_05s, grasp, tilt_borderline (0 or 1), confidence (1-3) and
  tube_contact (none, touched or closed); every F has a code F1-F7 and no S has one; t_release_s is a number where
  given, and every S has one. scored_utc is written "YYYY-MM-DD HH:MM" (UTC, to the minute).
- Process (Arturo): I (the judge, AMR) watched every clip and decided every score. Rows 18 to 54 of sheet A and all of
  sheet B were entered from the judge's descriptions of each clip; the judge confirmed every entry.
- Failure codes (Arturo) follow what the video shows: F5 only when the clip ends with the arm at the wall; when the arm
  goes home by itself, the code is for what happened before; when wall contact is not visible, no collision is scored.
  C 1.6 lists the operator's f under F5, and most live scores used F5 for trials ended by f at the wall; so the blind
  and live failure codes are not on the same rule and are reported side by side, not as an agreement measure.
  Success (S/F) is scored by C 1.4 in both.
- Clip 8726af (sheet A) shows no tubes in either view (rack and mat present); scored F with confidence 1. To be checked
  against its trial record after unblinding.

## Unblinding and the registered analysis on the blind scores (Nov 10, 12:13 PST)
- Keys: media/real/judge/sealed/blind_key_A_20261110T064043Z.json and _B_ (SHA-256 009edaf7… and 2d62a9bc…), each
  equal to its committed .sha256 file and to the value published in entry 4 (public 74a7833), checked before they were
  opened. Each key's codes equal its sheet's codes. Opened after the sheets were committed (725ab03).
- `analysis/blind_results.py` joins codes to trial records and calls the released analysis code unchanged
  (release/prereg_v2/analysis/real.py and stats.py, identical to the public repo's analysis/). With R3 and R5 cut (K8),
  the released h1_h3() computes no H1 test, so H1c and the first falsification check are computed with the same
  function and arguments (stats.adjusted_wald on R2 + R4 against R1, [1, -0.5], "less"; pooled outside at or above
  half of nominal). Results: results/analysis/real_blind_v1.json, .md and _rows.jsonl.
- Clip 8726af (sheet A, row 41) is N04-001 attempt 1 (N04-R0, R0), the trial run with no tubes on the mat (reset
  error; re-labelled I4 on Nov 6 and re-run as attempt 2). Its blind score (F, F1, confidence 1, tube_contact none,
  "NO TUBES VISIBLE in either video") matches its record; it is invalid and stays out of the analysis.
- Live and blind outcomes agree on every clip (61 of 61, invalid included; kappa 1.00 on the 56 valid trials).
