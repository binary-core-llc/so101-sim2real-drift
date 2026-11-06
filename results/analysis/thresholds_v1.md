# Simulated thresholds, sweep v1 (PREREGISTRATION_v1.md §4)

S0: 124/200 = 0.620; half of nominal = 0.310. Bootstrap: 2000 resamples by vial seed, numpy default_rng(20261103). Code: `analysis/thresholds.py`.

| Factor | Levels | Lowest level rate | Threshold | 95 % CI | Training half-range h | Prediction [h, 2h] |
|---|---|---|---|---|---|---|
| S1 camera tilt down (deg) | 1.43, 1.5, 2.87, 3.58, 4.3, 5.73, 6, 8.6 | 0.500 | censored (> 8.6) | above the range (99.35% of resamples censored) | 2.865 | not met |
| S2 rack toward the camera wall (cm) | 0.5, 1, 1.25, 1.5, 2, 3, 4 | 0.525 | censored (> 4) | above the range (100.00% of resamples censored) | 1.000 | not met |
| S3 rack toward the back wall (cm) | 2, 3, 4, 5, 6, 8 | 0.550 | censored (> 8) | above the range (100.00% of resamples censored) | 4.000 | not met |
| S7 camera yaw (deg code) | 1.43, 2.87, 3.58, 4.3, 5.73, 8.6 | 0.600 | censored (> 8.6) | above the range (100.00% of resamples censored) | 2.865 | not met |
| S8 camera raised (cm) | 0.5, 1, 1.25, 1.5, 2, 3 | 0.550 | censored (> 3) | above the range (99.95% of resamples censored) | 1.000 | not met |

Censored: success never falls to half of S0 within the tested levels; v1 counts a censored threshold as a prediction not met. S7 is in code units (v1: +10 deg code = 16.7 deg physical pan).
