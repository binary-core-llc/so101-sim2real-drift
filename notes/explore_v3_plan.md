# explore-v3 plan (fixed before running)

_explore-v3: added after explore-v2, not part of prereg-v1._ Committed before the first episode.

**Question.** At camera tilt down 13° and 15°, most explore-v1/v2 failures ran to the 450-step limit with the vial still held, often upright at a rack slot. With a longer episode, how many succeed, and when?

**Code.** `explore/sweep_eval_long.py` is `sim/sweep_eval.py` with only the episode length changed: L = 10 + 1740 + 25 = **1775 steps**. That is 10 warm-up steps, plus 108.75 chunks × 16 actions (58 s at the real robot's 30 Hz with zero latency), plus the 25-step success hold. The script asserts `max_steps == 1775`. Cells run through the registered queue with `--runner explore/run_cell_long.py` and `GTC_Q_DEFAULT_EP_S=200`. The registered code is untouched.

**Cells.** Z_nominal_long, Z_tilt_down_13_long, Z_tilt_down_15_long: 40 episodes each, seeds 0-39. Everything else is as in explore-v1: all randomization at its centre, instruction "Pick up the vial and place it in the yellow rack".

**Per success.** Success step s (the episode terminates after the 25-step hold). Release step r = s − 25. Chunk = ceil((r − 10) / 16).

**Cutoffs, applied afterwards to the same episodes:**
- **(a) sim budget:** success with s ≤ 450. This is an independent replicate of the earlier runs, because the policy server's sampling isn't seeded. Compare with S0 nominal (seeds 0-39 × 5: 124/200), explore-v2 tilt 13° (6/40) and explore-v1 tilt 15° (5/40). No exact match is expected.
- **(b) 28 chunks:** release chunk ≤ 28.
- **(c) 58 s at the real robot's pace:** release chunk ≤ 58 / (16/30 + latency).
  - With the explore-v1 median policy latency, 112.8 ms per query (320 episodes; p10-p90 92-118 ms), the limit is 89.76 chunks.
  - It is recomputed later with the latency measured in Monday's pilot.

**Rule (fixed now).** A tilt level qualifies as the H3a correction mis-setup if, at cutoff (c), its success is **at most 25 %** while nominal stays at **50 % or more**.

**Timing.** Start only if the estimated finish is before 06:00 PT on Oct 26; otherwise wait until after Monday's drift reference. A timer at 06:00 PT STOPs (not PAUSEs) whatever is still running and logs `nvidia-smi`. Only the GR00T server may stay on the GPU. Nothing loads the GPU during Monday's rig work.

**Real-robot loop used for "30 Hz, 16 actions"** (course `docker/real/scripts/so101_eval.py` @ ce807d9; `real/pilot.py` keeps the same lines):
- `:221` `action_horizon: int = 16`
- `:257` `actions = policy.get_action(obs)`
- `:259` `for i, action_dict in enumerate(actions[: cfg.action_horizon]):`
- `:261` `so101_control.send_action(action_dict)`
- `:270-271` `if toc - tic < 1.0 / 30: time.sleep(1.0 / 30 - (toc - tic))`

So one chunk lasts the policy latency plus 16 × 1/30 s.
