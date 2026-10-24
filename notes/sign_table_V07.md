# V07 sign table (T06), from `results/sim/t06_probe.jsonl`

Measured on the live stage (camera prim world pose, rack pose) and in the rendered front image, relative to nominal.
Env frame: +x = toward the back wall, +y = toward the camera wall (the 'Left' panel), +z = up; open front at -x.
Answers to V07: **tilt down = code pitch +**; **toward the camera wall = camera code x +**; **toward the back wall = camera code y -**; up = camera code z +. Rack: code x + = toward the back wall, code y + = toward the camera wall. Code yaw is not a pure pan (the mount z axis is tilted ~36 deg): +10 deg code yaw = 16.7 deg pan + ~1.5 deg tilt.
Wall limits from the nominal lens position (0.138, 0.330, 0.489): camera wall +5.1 cm (inner face y 0.381), ceiling +4.1 cm (z 0.530); the 6 cm probes beyond them are invalid levels.

| code override | physical result | camera Δpos (cm, env xyz) | Δtilt down (°) | Δpan (°) | image roll (°) | rack mask shift (px) |
|---|---|---|---|---|---|---|
| `{"camera": {"roll": 0.17453292519943295}}` | camera image rolls CCW 10.00 deg | [-0.01, 0.67, -0.48] | -0.0 | 0.0 | 10.0 | [16.4, 3.9] |
| `{"camera": {"roll": -0.17453292519943295}}` | camera image rolls CW 10.00 deg | [0.15, -0.66, 0.48] | -0.0 | -0.0 | -10.0 | [-15.4, -6.8] |
| `{"camera": {"pitch": 0.17453292519943295}}` | camera tilts down 9.99 deg | [-0.0, 0.0, -0.0] | 9.995 | 0.633 | 0.0 | [1.4, -93.4] |
| `{"camera": {"pitch": -0.17453292519943295}}` | camera tilts up 10.00 deg | [0.0, -0.0, 0.0] | -9.997 | -0.384 | -0.0 | [-4.3, 82.0] |
| `{"camera": {"yaw": 0.17453292519943295}}` | camera tilts up 1.46 deg, pans left (CCW from above) 16.69 deg | [0.15, -0.47, -0.67] | -1.459 | 16.687 | -0.0 | [92.4, 0.4] |
| `{"camera": {"yaw": -0.17453292519943295}}` | camera pans right (CW from above) 16.90 deg | [-0.0, 0.49, 0.67] | -0.925 | -16.902 | 0.0 | [-96.3, 2.6] |
| `{"camera": {"x": 0.06}}` | camera moves toward the camera wall (+6.0 cm env y) -- LENS OUTSIDE THE BOX (behind a wall/ceiling): not a valid level | [0.0, 6.0, 0.0] | 0.0 | 0.0 | 0.0 | None |
| `{"camera": {"x": -0.06}}` | camera moves toward the right wall (-6.0 cm env y) | [-0.0, -6.0, 0.0] | 0.0 | 0.0 | 0.0 | [-18.3, 64.5] |
| `{"camera": {"y": 0.06}}` | camera moves toward the open front (-6.0 cm env x) | [-6.0, 0.0, 0.0] | 0.0 | 0.0 | 0.0 | [-66.2, -7.6] |
| `{"camera": {"y": -0.06}}` | camera moves toward the back wall (+6.0 cm env x) | [6.0, 0.0, 0.0] | 0.0 | 0.0 | 0.0 | [69.3, 8.0] |
| `{"camera": {"z": 0.06}}` | camera moves up (+6.0 cm env z) -- LENS OUTSIDE THE BOX (behind a wall/ceiling): not a valid level | [0.0, 0.0, 6.0] | 0.0 | 0.0 | 0.0 | None |
| `{"camera": {"z": -0.06}}` | camera moves down (-6.0 cm env z) | [0.0, 0.0, -6.0] | 0.0 | 0.0 | 0.0 | [-12.4, -33.3] |
| `{"rack": {"x": 0.04}}` | rack moves toward the back wall (+4.0 cm env x) | [0.0, 0.0, 0.0] | 0.0 | 0.0 | 0.0 | [-44.3, -5.1] |
| `{"rack": {"x": -0.04}}` | rack moves toward the open front (-4.0 cm env x) | [0.0, 0.0, 0.0] | 0.0 | 0.0 | 0.0 | [45.0, 5.2] |
| `{"rack": {"y": 0.04}}` | rack moves toward the camera wall (+4.0 cm env y) | [0.0, 0.0, 0.0] | 0.0 | 0.0 | 0.0 | [-11.1, 43.4] |
| `{"rack": {"y": -0.04}}` | rack moves toward the right wall (-4.0 cm env y) | [0.0, 0.0, 0.0] | 0.0 | 0.0 | 0.0 | [10.0, -39.3] |
| `{"rack": {"yaw": 0.5}}` | rack turns CCW (from above) 28.6 deg about its corner origin | [0.0, 0.0, 0.0] | 0.0 | 0.0 | 0.0 | [41.6, 27.8] |
| `{"rack": {"yaw": -0.5}}` | rack turns CW (from above) 28.6 deg about its corner origin | [0.0, 0.0, 0.0] | 0.0 | 0.0 | 0.0 | [-10.4, -40.0] |
| `{"exposure_ev": -4.0}` | box light -4 EV (centre -1): image brightness x0.811 | [0.0, 0.0, 0.0] | 0.0 | 0.0 | 0.0 | [0.0, 0.0] |
| `{"exposure_ev": 2.0}` | box light +2 EV (centre -1): image brightness x1.548 | [0.0, 0.0, 0.0] | 0.0 | 0.0 | 0.0 | [0.0, 0.0] |
| `{"mat_yaw_rad": 0.1}` | mat yaw +5.7 deg | [0.0, 0.0, 0.0] | 0.0 | 0.0 | 0.0 | [0.0, 0.0] |
| `{"wrist_focal_mm": 12.0}` | wrist focal 12.0 mm (centre 13.5) | [0.0, 0.0, 0.0] | 0.0 | 0.0 | 0.0 | [0.0, 0.0] |
| `{"camera_focal_mm": 1.697}` | external camera HFOV 70.53 deg (nominal 63.74): rack area x0.773 | [0.0, 0.0, 0.0] | 0.0 | 0.0 | 0.0 | [10.2, -11.1] |

T05 readback: ALL PASS (25 sets, tolerance 1e-4).
Nominal repeated at the end: camera pos diff 0.00e+00 m, vial after-reset diff 0.00e+00 m.
