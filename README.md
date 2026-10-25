# SO-101 sim-to-real drift tolerance: pre-registration and simulation sweep

Pre-registration and simulation-sweep code for a study by Arturo Morales Rangel (Binary Core LLC), prepared for a GTC 2027 poster submission.

The study measures how much a real SO-101 workspace can differ from the simulation in NVIDIA’s course “Train an SO-101 Robot From Sim-to-Real With NVIDIA Isaac” while the course’s sim-trained GR00T N1.6 policy still succeeds. Examples of such differences: the camera tilted a few degrees, the rack moved a few centimeters, or brighter or darker lighting. It also tests whether one photo of the real setup is enough to correct it.

Status (October 2026): the simulation sweep is complete (2,220 episodes). Its analysis will be published with pre-registration v2, before the first scored real-robot trial. The sweep ran from a working copy whose code and configuration files are byte-identical to prereg-v1 (verified by git blob hash).

**The date of record is the GitHub release `prereg-v1`.** That release pins:

| File | What |
|---|---|
| `PREREGISTRATION_v1.md` | hypotheses, designs, analysis plan |
| `sweep_cells_v1.csv` | the simulation sweep cells (md5 `c8d81d681277c9119c4c3f2e96b075ae`; `.gitattributes` keeps it byte-exact) |
| `sim/overrides.py` | how a cell's factor level is applied while every other randomization stays at its center |
| `sim/sweep_eval.py` | the evaluation loop, derived from the course's `scripts/lerobot_eval.py` |
| `config/sign_table.json`, `notes/sign_table_V07.md` | the measured mapping from code axes to physical directions |
| `tools/map_sweep_cells.py`, `config/cells_sweep_v1.csv`, `config/cells_sweep_v1_mapping.json` | how each row of `sweep_cells_v1.csv` becomes a run: the exact overrides, seeds and episode counts |
| `sim/run_queue.py`, `sim/run_sim.sh`, `sim/run_server.sh`, `sim/server_ping.py` | the unattended queue, container wrappers and server checks |
| `assets/local/`, `tools/mirror_remote_assets.py`, `tools/make_local_wrappers.py` | offline copies of the scene's remote assets (wrapper layers over the unmodified course USDs) |
| `docker/sim/` | the course's simulation Dockerfile with two pinned-dependency patches, and an offline entrypoint (diffs included) |
| `config/layouts.json`, `sim/layouts.py` | the vial start layouts L00-L09 used in simulation and on the real robot |

## Pinned stack
- Course repository `isaac-sim/Sim-to-Real-SO-101-Workshop` at commit `ce807d9` (not included here; the code above imports it).
- Simulation image built from `nvcr.io/nvidia/isaac-lab:2.3.2` with `docker/sim/Dockerfile`.
- GR00T policy server: Isaac-GR00T `ead52833`.
- Checkpoint `aravindhs-NV/grootn16-finetune_sreetz-so101_teleop_vials_rack_left`, `checkpoint-10000`, Hugging Face revision `7efab50d`.
- NVIDIA RTX A4500, driver 580.65.06.

Deviations from the course setup are listed in section 7 of the pre-registration.

## License
Apache-2.0 (see LICENSE), Copyright 2026 Binary Core LLC. Files derived from the course (sim/sweep_eval.py, docker/sim/*) keep NVIDIA’s Apache-2.0 header; see NOTICE.
