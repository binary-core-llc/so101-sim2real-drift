# Provenance of the README figures and clips

Every file the README shows from `docs/figures/` and `docs/videos/`, with its sources, SHA-256 and the command or script that made it. Private sources are given relative to the study's working folder (`gtc/...` is the private working repository, as in `poster/numbers.json`); public sources are paths in this repository. Tools: Python 3.12.13 with Pillow 13.0.0 (figures); ffmpeg 4.4.2 with libx264 (Ubuntu 22.04 build) and the DejaVu Sans font (`/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf`) (clips). Re-running the commands on that ffmpeg build gives byte-identical files.

## Figure inputs copied from the private working repository

Byte-identical copies (`cp`) of two simulation frames: the first front-camera frame of episode 0 (seed 0) of the sweep cells `H4_c920_measured` and `S1_measured_c920`.

| File here | Source | Source SHA-256 | SHA-256 here |
|---|---|---|---|
| `docs/figures/h4_c920_measured_ep0000_step0_front.png` | `gtc/media/sim/H4_c920_measured/ep0000_step0_front.png` | `fa3278546bcb867226e260ef5e29c918f6d1ca23604ee51cb452129c4d332c30` | `fa3278546bcb867226e260ef5e29c918f6d1ca23604ee51cb452129c4d332c30` |
| `docs/figures/s1_measured_c920_ep0000_step0_front.png` | `gtc/media/sim/S1_measured_c920/ep0000_step0_front.png` | `c74a98285a491961188d33d8adfaa3630b1b1674e2b8b5e3cafda4046125e943` | `c74a98285a491961188d33d8adfaa3630b1b1674e2b8b5e3cafda4046125e943` |

## Figure copied unchanged from the private working repository

E3 in camera mode on the N04B-R0 reference photo (the per-pixel median of the reference frames, front camera), with the mat and rack outlines rendered by E3 from the course's scene geometry (`e3/cache/scene.npz`) at E3's estimated camera pose. The record beside it holds the estimate and the fit scores quoted in the README caption; its `version_hash` is E3's code at e3 commit `578f043`, which differs from the frozen `399025f` only in `validate_real.py`.

| File here | Source | Source SHA-256 | SHA-256 here |
|---|---|---|---|
| `docs/figures/e3_one_photo_camera.png` | `gtc/results/e3/gpu_cam_abs_N04B-R0_R0_seg2.png` | `f81a1d3cd3310b050d750a4c885473c77032199017c9cdca35cafb5fc41deacf` | `f81a1d3cd3310b050d750a4c885473c77032199017c9cdca35cafb5fc41deacf` |
| (record) | `gtc/results/e3/gpu_cam_abs_N04B-R0_R0_seg2.json` | `0a0e16f55149c935223ca829d4b181c479a93e7c334d6276c52b343902136ec6` | not copied |

```bash
cp gtc/results/e3/gpu_cam_abs_N04B-R0_R0_seg2.png docs/figures/e3_one_photo_camera.png
```

## Figures

Made by `python3 -I docs/figures/make_figures.py` from files in this repository (byte-identical on every run).

| File | Inputs (SHA-256) | SHA-256 |
|---|---|---|
| `docs/figures/pose_offset.png` | `docs/figures/h4_c920_measured_ep0000_step0_front.png` (fa3278546bcb8672…)<br>`docs/figures/s1_measured_c920_ep0000_step0_front.png` (c74a98285a491961…)<br>`poster/numbers.json` (2d1d779c63c90288…)<br>`results/h4/s1_result.json` (21cb929e336ed382…)<br>`results/sim/H4_c920_measured.jsonl` (00b1d493a073163c…)<br>`results/sim/S1_measured_c920.jsonl` (e71ffb203b8c8839…) | `7bff7f5ee5cac20773474dcf7bda5e55f34908e9aa835c6ba5eacb2d2c53e8ff` |
| `docs/figures/results_chain.svg` | `poster/numbers.json` (2d1d779c63c90288…)<br>`results/h4/h4_result.json` (e3f769902e3574e8…)<br>`results/h4/s1_result.json` (21cb929e336ed382…)<br>`README.md` (the result sentence and step 2) | `901a133ff1418f77ccbed2ab65eaeef6b053650a2b78d39ed0511e6287cf9358` |
| `docs/figures/sled.svg` | `README.md` (the result sentence and step 2)<br>`docs/charuco_board.json` (07a887cc4401fc2d…)<br>`docs/ChArUco_GTC_SO101_letter.pdf` (d25d5604da35890b…) | `4bc4628b17c1c07fbad4f78d2381805ae76beaee4e4c71e7b86ea9fe361e46e6` |

The `README.md` inputs are text the script parses (condition wording, sled dimensions); the figures do not change when other README text changes.

## Clips

Keyframe recordings from the robot's front and wrist cameras (one frame per policy step, 2 frames per second in the source files), side by side. Video only, all metadata removed; the last frame is held for 1 s. Each clip's ffprobe tags hold only the container brand, `language=und` and `handler_name=VideoHandler`; the MP4 header times are 0; the GIFs hold only the loop marker and frame timings. Every distinct frame was reviewed for anything that could show a location or a person; nothing was blurred or cropped. The real trial length in each README caption is the time from the first policy query to the safety key (`key_t_s` in `results/real/trials.jsonl`) or to the 60 s cap (the last action sent, `results/real/steps/<uid>.jsonl`), and the playback factor is that length divided by the keyframes' playback time. All three clips play at the R1 clip's factor (its 92 keyframes at 5 per second, about 3.3x real time): the `setpts` multiplier of the R0 and R4 clips sets their keyframe rate (about 5.04 and 5.08 per second) to match it, and their GIFs keep every 10 fps frame so that no keyframe is skipped. Only the recorded keyframes are shown; frames are repeated, never interpolated or blended.

### `r1_success_N04-012_a1` (R1, blind-scored success; 92 keyframes)

| File | SHA-256 |
|---|---|
| source `gtc/media/real/trials/N04-012_a1/kf_front.mp4` | `637a9601f426e77085b413daa13e42e1203339cb495b2b0f8d7c9b82f2b7cef3` |
| source `gtc/media/real/trials/N04-012_a1/kf_wrist.mp4` | `240ec0b54e69edbfd256abd0c59d4455eb6d6be5fe1b5b7abb198ab96466d5ff` |
| `docs/videos/r1_success_N04-012_a1.mp4` | `1db46d93b4a5823dd65b07d64a6d2ca9d27d71c7726f060f2799decd437c0ae4` |
| `docs/videos/r1_success_N04-012_a1.gif` (from the MP4) | `928d6cb28c04d28981055f10b936b18ee3b17b994a3ec436f5d17a49997b64c7` |

```bash
ffmpeg -i gtc/media/real/trials/N04-012_a1/kf_front.mp4 -i gtc/media/real/trials/N04-012_a1/kf_wrist.mp4 \
  -filter_complex "[0:v][1:v]hstack=inputs=2,setpts=PTS*2/5,tpad=stop_mode=clone:stop_duration=1,fps=10,drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='front camera':x=10:y=10:fontsize=20:fontcolor=white:box=1:boxcolor=black@0.55:boxborderw=5,drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='wrist camera':x=650:y=10:fontsize=20:fontcolor=white:box=1:boxcolor=black@0.55:boxborderw=5,format=yuv420p[v]" \
  -map "[v]" -an -sn -dn -map_metadata -1 -map_chapters -1 -c:v libx264 -preset slow -crf 20 \
  -movflags +faststart -fflags +bitexact -flags:v +bitexact docs/videos/r1_success_N04-012_a1.mp4
ffmpeg -i docs/videos/r1_success_N04-012_a1.mp4 -vf "fps=5,scale=640:-2:flags=lanczos,split[s0][s1];[s0]palettegen=stats_mode=diff[p];[s1][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle" \
  -an -map_metadata -1 -loop 0 -fflags +bitexact docs/videos/r1_success_N04-012_a1.gif
```

### `r0_failure_N04B-007_a1` (R0, blind-scored failure; 25 keyframes)

| File | SHA-256 |
|---|---|
| source `gtc/media/real/trials/N04B-007_a1/kf_front.mp4` | `e459ce2960e865e0045f5a2076547a3093a5581a82617f74861afc7c6bdec004` |
| source `gtc/media/real/trials/N04B-007_a1/kf_wrist.mp4` | `85898c8d2d3051e1b70f29b9a4d7546f0cb8ac35bbe08944fe9d56409ce8b9c6` |
| `docs/videos/r0_failure_N04B-007_a1.mp4` | `0c09f6b063972196e5a641dde36b2c05c04419bf6220e490df20aff8113cc880` |
| `docs/videos/r0_failure_N04B-007_a1.gif` (from the MP4) | `10182b86374516f63a979cd9345c810c7cadbdfcf86d4cecc34150cbd8212d9a` |

```bash
ffmpeg -i gtc/media/real/trials/N04B-007_a1/kf_front.mp4 -i gtc/media/real/trials/N04B-007_a1/kf_wrist.mp4 \
  -filter_complex "[0:v][1:v]hstack=inputs=2,setpts=PTS*0.396654,tpad=stop_mode=clone:stop_duration=1,fps=10,drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='front camera':x=10:y=10:fontsize=20:fontcolor=white:box=1:boxcolor=black@0.55:boxborderw=5,drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='wrist camera':x=650:y=10:fontsize=20:fontcolor=white:box=1:boxcolor=black@0.55:boxborderw=5,format=yuv420p[v]" \
  -map "[v]" -an -sn -dn -map_metadata -1 -map_chapters -1 -c:v libx264 -preset slow -crf 20 \
  -movflags +faststart -fflags +bitexact -flags:v +bitexact docs/videos/r0_failure_N04B-007_a1.mp4
ffmpeg -i docs/videos/r0_failure_N04B-007_a1.mp4 -vf "fps=10,scale=800:-2:flags=lanczos,split[s0][s1];[s0]palettegen=stats_mode=diff[p];[s1][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle" \
  -an -map_metadata -1 -loop 0 -fflags +bitexact docs/videos/r0_failure_N04B-007_a1.gif
```

### `r4_failure_N06-018_a1` (R4, blind-scored failure; 31 keyframes)

| File | SHA-256 |
|---|---|
| source `gtc/media/real/trials/N06-018_a1/kf_front.mp4` | `cc2f7f2425ea4d0bb2c47403cae2331a98aefd7f07a31e53317f2398369058fa` |
| source `gtc/media/real/trials/N06-018_a1/kf_wrist.mp4` | `aaf7d545c80e69a97ba8276083e425731a2c6ae2fb3df30df14d2fa0c2f36c31` |
| `docs/videos/r4_failure_N06-018_a1.mp4` | `eb77e187b13d04a9765a7be2571182a0292da4226241a805ac184d732d65cbc0` |
| `docs/videos/r4_failure_N06-018_a1.gif` (from the MP4) | `8352e6811d25b4f26a9420427d520efe76a239c5936faade42f0a9ab28518e95` |

```bash
ffmpeg -i gtc/media/real/trials/N06-018_a1/kf_front.mp4 -i gtc/media/real/trials/N06-018_a1/kf_wrist.mp4 \
  -filter_complex "[0:v][1:v]hstack=inputs=2,setpts=PTS*0.393519,tpad=stop_mode=clone:stop_duration=1,fps=10,drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='front camera':x=10:y=10:fontsize=20:fontcolor=white:box=1:boxcolor=black@0.55:boxborderw=5,drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='wrist camera':x=650:y=10:fontsize=20:fontcolor=white:box=1:boxcolor=black@0.55:boxborderw=5,format=yuv420p[v]" \
  -map "[v]" -an -sn -dn -map_metadata -1 -map_chapters -1 -c:v libx264 -preset slow -crf 20 \
  -movflags +faststart -fflags +bitexact -flags:v +bitexact docs/videos/r4_failure_N06-018_a1.mp4
ffmpeg -i docs/videos/r4_failure_N06-018_a1.mp4 -vf "fps=10,scale=800:-2:flags=lanczos,split[s0][s1];[s0]palettegen=stats_mode=diff[p];[s1][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle" \
  -an -map_metadata -1 -loop 0 -fflags +bitexact docs/videos/r4_failure_N06-018_a1.gif
```
