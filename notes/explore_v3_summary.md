# explore-v3 summary

_explore-v3: added after explore-v2, not part of prereg-v1._ Episode length 1775 steps; seeds 0-39; cutoffs fixed in notes/explore_v3_plan.md.
Cutoff (c) = 58 / (16/30 + 112.8 ms) = 89.76 chunks (explore-v1 median policy latency over 320 episodes).

| cell | (a) step <= 450 | earlier at 450 (Fisher p vs a) | (b) chunk <= 28 | (c) chunk <= 89.76 | full 1775 |
|---|---|---|---|---|---|
| Z_nominal_long | 23/40 (0.422-0.715) | S0 nominal, seeds 0-39 x 5: 124/200 (p 0.5985) | 24/40 (0.446-0.737) | 27/40 (0.52-0.799) | 27/40 (0.52-0.799) |
| Z_tilt_down_13_long | 8/40 (0.105-0.348) | explore-v2 tilt 13: 6/40 (p 0.7695) | 13/40 (0.201-0.48) | 28/40 (0.546-0.819) | 30/40 (0.598-0.858) |
| Z_tilt_down_15_long | 7/40 (0.087-0.319) | explore-v1 tilt 15: 5/40 (p 0.7555) | 14/40 (0.221-0.505) | 29/40 (0.572-0.839) | 29/40 (0.572-0.839) |

Rule (fixed before running): a tilt level qualifies as the H3a correction mis-setup if at (c) its success is <= 25 % while nominal is >= 50 %.
- Z_tilt_down_13_long: tilt 0.700, nominal 0.675 -> does not qualify
- Z_tilt_down_15_long: tilt 0.725, nominal 0.675 -> does not qualify

Release chunk of every success (sorted):
- Z_nominal_long: [14, 15, 15, 15, 16, 16, 17, 17, 19, 19, 19, 19, 19, 19, 20, 20, 20, 22, 23, 23, 24, 24, 26, 27, 38, 43, 49]
- Z_tilt_down_13_long: [18, 20, 21, 21, 23, 24, 25, 26, 27, 27, 27, 28, 28, 29, 29, 29, 29, 31, 33, 34, 37, 37, 41, 44, 57, 58, 61, 65, 90, 101]
- Z_tilt_down_15_long: [19, 20, 20, 21, 21, 26, 26, 27, 27, 27, 27, 27, 27, 28, 29, 30, 30, 31, 31, 31, 31, 32, 32, 32, 33, 33, 33, 39, 54]
