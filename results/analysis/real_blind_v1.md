# Real trials, blind scores: registered analysis (Nov 10, 2026)

`analysis/blind_results.py` (released analysis code: release/prereg_v2/analysis/real.py and stats.py, unchanged).
Keys checked against the SHA-256 in entry 4 (A 009edaf7…, B 2d62a9bc…). Full output: `real_blind_v1.json`;
one joined row per trial: `real_blind_v1_rows.jsonl`.

| Condition | Blind k/n | Wilson 95% | Clopper-Pearson 95% | Ratio to R1 |
|---|---|---|---|---|
| R0 (N04B-R0, the R0 result) | 1/10 | 0.018-0.404 | 0.003-0.445 | 0.33 |
| R0 with scene offset (N04-R0, not pooled) | 1/10 | 0.018-0.404 | 0.003-0.445 | |
| R1 nominal at S1 | 6/20 | 0.145-0.519 | 0.119-0.543 | 1 |
| R2 rack y+3 cm | 2/10 | 0.057-0.510 | 0.025-0.556 | 0.67 |
| R4 tilt +6°, primary (N06-004 to N06-007 I4) | 0/6 | 0.000-0.390 | 0.000-0.459 | 0 |
| R4 with N06-004 to N06-007 | 0/10 | 0.000-0.278 | 0.000-0.308 | 0 |

- Live vs blind: Cohen's kappa 1.00 (56 valid trials); no disagreement in any of the 61 clips (invalid included).
- H1c (adjusted Wald, one-sided, p_outside − 0.5 p_nominal < 0; R2 + R4 against R1): primary 2/16 against 6/20,
  L_hat −0.025, z 0.075, **p = 0.530**, not rejected; with N06-004 to N06-007, 2/20, z −0.257, **p = 0.399**, not rejected.
- First falsification check (pooled outside ≥ half of nominal): 0.125 against 0.15 (primary), 0.10 against 0.15
  (with): not falsified.
- H1: not supported (the registered rule needs H1a, which has no data after K8) and not falsified.
- Comparator: R1 6/20 = 0.300 against S1_measured_c920 99/200 = 0.495: difference −0.195 (Newcombe 95% −0.364 to
  +0.034); ratio 0.61.
- Decision checks: D1 gate 4/10 (not ≤ 3); D2 daily controls Nov 9 2/6 (no stop); D3 no effect: no for R2 and R4.
- Secondary (blind): grasp R0 1/10, R1 8/20, R2 3/10, R4 3/6; hold ≥ 0.5 s equals the primary in every condition;
  time to release (phone clips, from T0): R1 median 8.6 s, R2 8.3 s.
- Failure codes, blind (judge's rule) against live: R1 F1 12, F3 2 (live F5 12, F3 2); R2 F1 7, F3 1 (live F1 2,
  F5 6); R4 F1 3, F2 3 (live F1 1, F2 1, F5 4); R0 F1 8, F5 1 (live F5 9).
