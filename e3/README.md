# E3: render-and-compare correction from one photo

Written on November 8, before the freeze. Segmentation fixed Nov 8 (rack = yellow core + attached warm pixels, convex hull).

- `render_gpu.py`: the same rasteriser in CUDA PyTorch. It runs in our Isaac container's python (no Isaac Sim app),
  reading the scene from `cache/scene.npz` (`render.py cache`). Class images are identical to render.py's (pixel
  agreement 1.000000 on 64 camera and 64 rack poses at both resolutions). Speed on the A4500, one pose at a time:
  4.1x (camera) and 4.0x (rack) at 160 x 120; 16.0x and 12.6x at 320 x 240 (`bench.py`, `bench_render.json`).
  `estimate.py --backend torch --scene-cache cache/scene.npz`.
- `render.py`: class images of the course scene (lightbox panels, mat, rack from the C1 dump) at any camera pose; the
  rack movable about its corner O. Renderer copied from gtc `sim/image_matched_pose.py` (gtc commit 58ffd9f). The robot
  and the tubes are not rendered (don't care in photos). Runs on the CPU (numpy z-buffer).
- `segment.py`: photo -> white / mat / rack (robot, tube caps, transitions: don't care), on the renderer's ideal
  pinhole (undistorted with the measured C920 intrinsics). The rack is the largest yellow component plus the warm
  saturated pixels joined to it (hole interiors, a shaded face), filled to its convex hull. Before Nov 8 the hole
  interiors went to robot (then grown into don't care) and, on sim renders, the shaded front face to mat.
- `eval_simset.py`: E3 on a simulated scene set (the 25 E1 selection renders, C920 focal); `results/e3/simset_e3.json`
  in gtc.
- `estimate.py camera|rack`: the Appendix C estimate. The objective is class-weighted soft IoU plus edge chamfer,
  searched coarse to fine (160 x 120, then 320 x 240) by D C12's registered search: the cross-entropy method,
  population 64, 15 iterations per level, full covariance, deterministic seed. `--search nm` keeps the Nelder-Mead
  multi-start for comparison. Camera mode takes `--reference-photo` (the nominal photo) for a differential delta.
- `validate.py`: synthetic accuracy (`validation_synthetic.json`).

Results so far:

| Test | Result |
|---|---|
| Synthetic (exact scene), camera, 5 cases incl. 6° tilt, CEM | errors ≤ 0.11° and ≤ 0.6 mm (55-62 s on the CPU; `validation_synthetic_cem.json`) |
| The same, Nelder-Mead | errors ≤ 0.12° and ≤ 0.8 mm (21-25 s) |
| Synthetic, rack, 6 cases up to ±30 mm and 15° | errors ≤ 0.4 mm and ≤ 0.08° (about 33 s; yaw grid ±24°) |
| (before the fix) Real, rack mode, CEM (16 s): N04B-R0_R0 (-0.46, +0.36) mm, 1.16°; N04-R0_R0 (-1.05, +24.61) mm, 0.99° | as Nelder-Mead below within 0.2° and 0.1 mm |
| Real, rack mode on the R0 references (camera = r0 PnP), Nelder-Mead | N04B-R0_R0 (-0.5, +0.3) mm, 0.98°; N04-R0_R0 (-1.1, +24.7) mm, 1.04°. gtc tools/scene_check.py gives (-1.0, +1.7) and (-1.8, +27.2). Soft IoU 0.94-0.98 |
| Real, camera mode on N04B-R0_R0 from 5 starts (6° tilt, pan 3° + height 15 mm, mixed) | all converge within 0.3°. The constant offset from the PnP r0 is tilt -0.6°, pan -2.2°, roll -1.1°, depth +11 mm, lateral +3.6, height -3.3 mm: the scene model's mismatch (the real mat is turned against the simulation). Hence the differential mode for camera cycles |

| **After the segmentation fix (Nov 8), GPU:** | |
| Sim set, 25 scenes (E1 selection renders), camera differential vs the nominal render | 12 camera scenes: errors ≤ 0.48° and ≤ 1.7 mm |
| The same, rack mode | 11 of 12 within 0.5 mm and 0.14°; rack x+20/y+20: y 15.6 mm for 20 (the sim render's shaded rack face falls under the saturation limit). Before the fix: rack y off by 10-24 mm |
| Real, rack mode on the R0 references (camera = r0 PnP) | N04B-R0_R0 (-0.0, +2.4) mm, +0.47°; N04-R0_R0 (-0.3, +25.7) mm, -0.98°. Rack soft IoU 0.959 -> 0.971 |
| Real, camera mode on N04B-R0_R0, absolute vs r0 | tilt -0.84°, pan -1.19°, roll +0.04°, lateral +2.1, depth +4.7, height -7.1 mm (before the fix: pan -2.2°, roll -1.1°, depth +11 mm) |
| GPU vs CPU, the same E3 runs | identical estimates and fits; rack 4.4-5.7 s on the GPU vs 16 s; camera search 7.3 s vs 81 s |

The code was then frozen at e3 commit 399025f (tar + SHA-256, addendum entry 3), before the first scored photo.
