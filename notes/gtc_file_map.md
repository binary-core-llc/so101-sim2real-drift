# Files copied from the private working repository

The study's working repository (`gtc`) is private, and its history is not published. The files below were copied from
it on November 10, 2026, after the poster was submitted, with gtc at commit `3a78356`. Each file is byte-identical to the
file at the gtc commit named (the commit that last changed it); none was edited for this copy.

| This repository | gtc path | gtc commit | Bytes | SHA-256 | What |
|---|---|---|---:|---|---|
| `poster/numbers.json` | `poster/draft/numbers.json` | 3a78356 | 60,834 | `2d1d779c63c902881b04d4761ee32a100b478526958fd3d293480ed874687278` | every number on the poster: value, k/n, interval, method, source, status |
| `results/real/trials.jsonl` | `results/real/trials.jsonl` | dfa96fe | 439,916 | `3416a93abfd9d36c1416f685a93149ceb7d03f21f2b69061b8829deb22ce6e7a` | the 61 real trial records (live scores, checks, edits) |
| `results/real/trials.csv` | `results/real/trials.csv` | dfa96fe | 165,104 | `9ade70c1921820698dc61e3a0a12ab45452a65e5034bd3a6c6dbcfaa68857e08` | the same records as a table, generated from trials.jsonl |
| `results/real/blind_scores_A_20261110T064043Z.csv` | `results/real/blind_scores_A_20261110T064043Z.csv` | 725ab03 | 8,908 | `58698183b486cb815bdced7b7ba0952dfbece02e22f95e00c24e784fb1fd7311` | blind score sheet, batch A (53 clips) |
| `results/real/blind_scores_B_20261110T064043Z.csv` | `results/real/blind_scores_B_20261110T064043Z.csv` | 725ab03 | 1,445 | `b85163253bb61d16489cab7aa8aacf33dcb94948912a12ebd04057a26a2e6883` | blind score sheet, batch B (8 clips) |
| `results/real/blind_key_A_20261110T064043Z.json` | `media/real/judge/sealed/blind_key_A_20261110T064043Z.json` | not tracked (sealed key; see below) | 1,431 | `009edaf7bcbc2edbe12f27f9a46d94dd2d2ca1c0e23489d622dc7f4ad31e7547` | blind key A: code -> trial |
| `results/real/blind_key_B_20261110T064043Z.json` | `media/real/judge/sealed/blind_key_B_20261110T064043Z.json` | not tracked (sealed key; see below) | 251 | `2d62a9bcd9b762736e2e454aeb70998a690eba29ef425308b998469a1ff3f683` | blind key B: code -> trial |
| `results/real/blind_key_A_20261110T064043Z.sha256` | `results/real/blind_key_A_20261110T064043Z.sha256` | 459293f | 124 | `a4f7c6132cc7d7a693723658491faf7064598cb0b32e978cd3928853e0d0d0a8` | SHA-256 of key A, committed before scoring |
| `results/real/blind_key_B_20261110T064043Z.sha256` | `results/real/blind_key_B_20261110T064043Z.sha256` | 459293f | 124 | `ad6810e6f8a8b7314be936ae75ce38df3858923cd2916e218efdabfbf595887f` | SHA-256 of key B, committed before scoring |
| `results/analysis/real_blind_v1.json` | `results/analysis/real_blind_v1.json` | 6f79f5e | 10,808 | `e84bc6a526107973c4399b172466690fc4c62b5e403158a27efbc0be695feec0` | registered real-trial analysis on the blind scores |
| `results/analysis/real_blind_v1.md` | `results/analysis/real_blind_v1.md` | 6f79f5e | 2,102 | `8d648dd811df0dd29fb67b1f21003830aa43e5073b88b301eba3096f21afcf73` | the same, as a short table |
| `results/analysis/real_blind_v1_rows.jsonl` | `results/analysis/real_blind_v1_rows.jsonl` | 6f79f5e | 47,806 | `78bf8854020ad236d9ee3fa418f885a64cd4a540c26de6190b7bce2cadf81d9f` | one unblinded row per trial (record joined to its blind score) |
| `results/analysis/h4_inputs.json` | `results/analysis/h4_inputs.json` | 9cc8872 | 105 | `3d13a2291603f1dc44ab3b2c5afed24e8d06125ba0cda7dd71f753826e3ee322` | H4 inputs (S0 and H4_c920_measured counts, measured fx) |
| `results/h4/h4_result.json` | `results/h4/h4_result.json` | 9cc8872 | 2,230 | `e3f769902e3574e8e7cca86003f0efb7c6ad9aa7542e6404997fbfbf7d85b0bb` | H4 test result |
| `results/h4/s1_result.json` | `results/h4/s1_result.json` | 60a4bb2 | 2,130 | `21cb929e336ed382e6081875e8fceac66796a68e12ba1674b4de379aeacf8e88` | S1_measured_c920 result against H4_c920_measured and S0 |
| `results/real/deviations.md` | `results/real/deviations.md` | 45e3fde | 75,639 | `025b8637aeed93480b23f3d63653f3e068a1271739f1239945bd36724b4a8e63` | the deviations log of the real trials |

## Simulation episode files (`results/sim/`)

65 files, 11,722,231 bytes, one JSON line per episode; same path in gtc. 50 are the sweep v1 cells
(`config/cells_sweep_v1.csv`), 2 are the registered H4 and S1 cells, and 13 are pilot or test runs from before the sweep,
which enter no registered analysis and no poster number. Each SHA-256 below was computed from the file here. 33 files are listed
in `results/analysis/thresholds_v1.json` (`source_sha256`, published with prereg-v2) and 3 in
`results/h4/s1_result.json` (`sha256`); every listed hash matches.

| File | What | gtc commit | Bytes | SHA-256 | Hash also listed in |
|---|---|---|---:|---|---|
| `results/sim/H4_c920_measured.jsonl` | registered H4 / S1 cell | 9cc8872 | 877,316 | `00b1d493a073163c81027a607d66daf11799fc3f2a6c01ae6462c5ca1482c86c` | s1_result.json |
| `results/sim/S0_nominal.jsonl` | sweep v1 cell | 8041260 | 830,637 | `209ef52e7b2e8d7de7fbac5471624ae01c7daf817c1305ea0e04d0786cd3ddbc` | s1_result.json |
| `results/sim/S1_measured_c920.jsonl` | registered H4 / S1 cell | 60a4bb2 | 902,282 | `e71ffb203b8c883948c4ffec37b7beefc6531557845637557b38598413c5b11f` | s1_result.json |
| `results/sim/S1_tilt_down_1p43.jsonl` | sweep v1 cell | 8041260 | 167,023 | `306cbea9c26d6bdf3db84f6df29fe32f75823e11a5ca4a35859faa6c0bf52c71` | thresholds_v1.json |
| `results/sim/S1_tilt_down_1p5.jsonl` | sweep v1 cell | 8041260 | 167,039 | `6b0e460a13976b9401637c5beaeb519f887a1070ac2ca46ead22a8a254ef53ec` | thresholds_v1.json |
| `results/sim/S1_tilt_down_2p87.jsonl` | sweep v1 cell | 8041260 | 166,975 | `25d68557bdbc13432a2f9c6ae767b9f5a0d80fa140f733b22af93b8f7297ffeb` | thresholds_v1.json |
| `results/sim/S1_tilt_down_3p58.jsonl` | sweep v1 cell | 8041260 | 167,137 | `71ebb6e10e134daf8e02bd166a718f4e143c04176c8aa5aa2eeefa13b1896821` | thresholds_v1.json |
| `results/sim/S1_tilt_down_4p3.jsonl` | sweep v1 cell | 8041260 | 166,998 | `0a8b3118e734b9544651cc84d4cbfe42818d91f0481b509d1a4fbd2a8d7ffd5e` | thresholds_v1.json |
| `results/sim/S1_tilt_down_5p73.jsonl` | sweep v1 cell | 8041260 | 167,132 | `900d3cd3d2da189b3f34ae9b06e7ddec0e053ba0e8aba46947e287f20f07d3f4` | thresholds_v1.json |
| `results/sim/S1_tilt_down_6p0.jsonl` | sweep v1 cell | 8041260 | 166,944 | `845b6bcf671d82d4fe6e26e0118191fb11234646dc62ea34a841c5996c48533d` | thresholds_v1.json |
| `results/sim/S1_tilt_down_8p6.jsonl` | sweep v1 cell | 8041260 | 166,981 | `e5b3f084c943a6fcf658fd35b9367bdac2f89daa2316d579ade1216b20a931fb` | thresholds_v1.json |
| `results/sim/S2_rack_y_0p5.jsonl` | sweep v1 cell | 8041260 | 166,168 | `b9f81383453d2a86c8ae81f2af4e75c1a7b969469b345a6ee89e78aff743c558` | thresholds_v1.json |
| `results/sim/S2_rack_y_1p0.jsonl` | sweep v1 cell | 8041260 | 166,081 | `99665b7e355151bd236f0c5c0caf6b3134f282bc7578afe41aab457f1bfeff6f` | thresholds_v1.json |
| `results/sim/S2_rack_y_1p25.jsonl` | sweep v1 cell | 8041260 | 165,990 | `2d18379bd1371f2270e218421f099aed2a96dcc814b5613e808c1f69a448c20a` | thresholds_v1.json |
| `results/sim/S2_rack_y_1p5.jsonl` | sweep v1 cell | 8041260 | 165,991 | `cfab3fd6f676f16790db3ffd6877e39081da5538c66d98926647462f4db687d0` | thresholds_v1.json |
| `results/sim/S2_rack_y_2p0.jsonl` | sweep v1 cell | 8041260 | 166,205 | `e01d37a6057b9089ac5e5bc970f63bf11ddb17c0481271d79a58cc5de3e649f5` | thresholds_v1.json |
| `results/sim/S2_rack_y_3p0.jsonl` | sweep v1 cell | 8041260 | 166,056 | `10e3f356f4d97c56c04e4f0a723006ef4df4540e74234b42f3f7ce7ca521b43b` | thresholds_v1.json |
| `results/sim/S2_rack_y_4p0.jsonl` | sweep v1 cell | 8041260 | 166,447 | `db2a871f6d8a298e84932b9415327d062a733b490d3b3494a62cb203726b3849` | thresholds_v1.json |
| `results/sim/S3_rack_x_2p0.jsonl` | sweep v1 cell | 8041260 | 166,292 | `af9d3958f913c2deac5b00527cb910e4cc529753969e958c699d71e8e6970abf` | thresholds_v1.json |
| `results/sim/S3_rack_x_3p0.jsonl` | sweep v1 cell | 8041260 | 166,138 | `bb59a4badff46a57b122410ce0129394ce95226080b73547a31a4c1fb73ce802` | thresholds_v1.json |
| `results/sim/S3_rack_x_4p0.jsonl` | sweep v1 cell | 8041260 | 166,035 | `abf36a4015477d187524f34a226771b2e2eae47f7e8da078cdddc8471e7ace0a` | thresholds_v1.json |
| `results/sim/S3_rack_x_5p0.jsonl` | sweep v1 cell | 8041260 | 166,234 | `89af85e7ce3694acf6fc23a46c785321d09c11822322b6022ac811bfb1fc4381` | thresholds_v1.json |
| `results/sim/S3_rack_x_6p0.jsonl` | sweep v1 cell | 8041260 | 166,355 | `9aa52ec8f99e03dcd1df2d3d3b523e8fe92375ddc28a503a0fd2213c7abc8976` | thresholds_v1.json |
| `results/sim/S3_rack_x_8p0.jsonl` | sweep v1 cell | 8041260 | 166,565 | `a0592562a7d725f0ce20e9683f924981f583dbb751821176d166f4141fe25518` | thresholds_v1.json |
| `results/sim/S4_light_darker_m2p0.jsonl` | sweep v1 cell | 8041260 | 166,457 | `da0cca2aaec424d03890017c8955acc9717d3da18c9d88cf28d60132e964da72` | - |
| `results/sim/S4_light_darker_m3p0.jsonl` | sweep v1 cell | 8041260 | 166,538 | `597cc7363b28b605df4b9961c60e2b227f0f42556bdc2f1d31da16051e4c0136` | - |
| `results/sim/S4_light_darker_m3p5.jsonl` | sweep v1 cell | 8041260 | 166,565 | `40c48905231b66fdf5c9af7f01bbc91b79ea0a35869fa34ae956826f8e697fbc` | - |
| `results/sim/S4_light_darker_m4p0.jsonl` | sweep v1 cell | 8041260 | 166,491 | `94535ed6dea7ef7b068bc60b74474094fa0eb297693a0b1163973dc304a466a7` | - |
| `results/sim/S4_light_darker_m5p0.jsonl` | sweep v1 cell | 8041260 | 166,578 | `d2eaace00c9db4c64817e31766838414919438a9d47a1efd5366d29a8bd30fbd` | - |
| `results/sim/S4_light_darker_m7p0.jsonl` | sweep v1 cell | 8041260 | 166,560 | `f35a1e7afae36afce27c07df0a657da1a3b9e8d55ca6f24c4eb3982605a02cd3` | - |
| `results/sim/S5_light_brighter_1p0.jsonl` | sweep v1 cell | 8041260 | 166,357 | `e6a75dbf9bd5507d7c9d8d2157e1a4ce2e012887b2f7c5cde4afc827248d511d` | - |
| `results/sim/S5_light_brighter_2p0.jsonl` | sweep v1 cell | 8041260 | 166,332 | `1bb0005918fd83b6acb4d0be19e0d34b95406ec587b4f7a6670d2f804cd59518` | - |
| `results/sim/S5_light_brighter_3p0.jsonl` | sweep v1 cell | 8041260 | 166,450 | `6410c8806cc3665edae86d4dfdd70433443a8030e1a9abff290b671f93bba9e7` | - |
| `results/sim/S6_ext_hfov_55p8.jsonl` | sweep v1 cell | 8041260 | 166,400 | `aa922d44676e7b50ee59f986b94911bb3ee688e7fdac84fc11e1c12c125ff711` | - |
| `results/sim/S6_ext_hfov_60p0.jsonl` | sweep v1 cell | 8041260 | 166,360 | `022635362418207b7d5500e61d49242e328e514447f92ac078002fd4cb969068` | - |
| `results/sim/S6_ext_hfov_65p9.jsonl` | sweep v1 cell | 8041260 | 166,392 | `e48178e1797d5265342050b756ab638cc56ab288fa4c953c01d50817d33d7a47` | - |
| `results/sim/S6_ext_hfov_70p4.jsonl` | sweep v1 cell | 8041260 | 166,505 | `82f6a38cd571abdf38cd28d2cd10440f394b7f10498c911ae0b6833b4c73845c` | - |
| `results/sim/S7_cam_yaw_1p43.jsonl` | sweep v1 cell | 8041260 | 166,871 | `eaac966b0365f228f8738cd15366b21dc7489c990850aa23046241e5b189a192` | thresholds_v1.json |
| `results/sim/S7_cam_yaw_2p87.jsonl` | sweep v1 cell | 8041260 | 166,852 | `6439f2b837cced402d484476ec85af4670feef9c496d0cce2aeb6f3c765934a6` | thresholds_v1.json |
| `results/sim/S7_cam_yaw_3p58.jsonl` | sweep v1 cell | 8041260 | 166,928 | `5315246a36384ca1611bc868c976684e0c22f5f5c2d0b5d38997ce8db343c05e` | thresholds_v1.json |
| `results/sim/S7_cam_yaw_4p3.jsonl` | sweep v1 cell | 8041260 | 166,775 | `f8ebc409f461dce3db70c660cebaccfac8058ff89a8b467b4633dafebc68efd7` | thresholds_v1.json |
| `results/sim/S7_cam_yaw_5p73.jsonl` | sweep v1 cell | 8041260 | 166,989 | `e70943489d38c0ffdb7a70df1c4194044d3a0370b95c42e2076e8e383fa236d0` | thresholds_v1.json |
| `results/sim/S7_cam_yaw_8p6.jsonl` | sweep v1 cell | 8041260 | 166,858 | `b659118d5b411828132f0029cedcdea7d4d110d74682e491fb2de4b0da81f362` | thresholds_v1.json |
| `results/sim/S8_cam_up_0p5.jsonl` | sweep v1 cell | 8041260 | 166,913 | `c552116f1ee49c07b54d07eb3da41cd11d72e07c7693d2368ec95106b9e285e6` | thresholds_v1.json |
| `results/sim/S8_cam_up_1p0.jsonl` | sweep v1 cell | 8041260 | 167,043 | `dfb14157e0a86dc50237e4dbb5ebb22c5b8b263b7a406a35a9aac17edc05e852` | thresholds_v1.json |
| `results/sim/S8_cam_up_1p25.jsonl` | sweep v1 cell | 8041260 | 167,121 | `8b51b621f184f0f13e0fb155c55c34606e2400d2b48d18608c7ae7e4fe3ddc6d` | thresholds_v1.json |
| `results/sim/S8_cam_up_1p5.jsonl` | sweep v1 cell | 8041260 | 167,007 | `f6279c3446bd273897bf7d50b009fd2fdaf163a2a89c4369e828f166cb44fd21` | thresholds_v1.json |
| `results/sim/S8_cam_up_2p0.jsonl` | sweep v1 cell | 8041260 | 166,898 | `3a89b3ccd5fe23cd50a42896a1c7d403fca46aa81a442a70112c7452fb270292` | thresholds_v1.json |
| `results/sim/S8_cam_up_3p0.jsonl` | sweep v1 cell | 8041260 | 166,952 | `a8091a604244482fa95600a2fa07cb3e2296475227ebfc6d062ffd420b443a23` | thresholds_v1.json |
| `results/sim/S9_tilt_up_m2p87.jsonl` | sweep v1 cell | 8041260 | 167,029 | `b4d6ab478f5a68caf9ffa53e19b6e3193aec03010b14acf963b81912788c8fbe` | - |
| `results/sim/S9_tilt_up_m5p73.jsonl` | sweep v1 cell | 8041260 | 166,906 | `142fab74b85a8707201857544e74d84eddfbb915eae2a5f18821ab3cf39e5f0b` | - |
| `results/sim/S_course.jsonl` | sweep v1 cell | 8041260 | 415,973 | `db311dbc874727b5f23f04e149f9f4c047ed407f11e4897223aafcef94a9c818` | - |
| `results/sim/pilot_cam_tilt_down_m4.jsonl` | pilot or test run (no analysis) | 58477c6 | 41,392 | `40292b8511635e96051b9477c8a463fd4d18298580576454960a99f290ae9aca` | - |
| `results/sim/pilot_cam_tilt_down_p8.jsonl` | pilot or test run (no analysis) | 58477c6 | 41,475 | `b61b9fc428743f1fae014c801d682d40828cb460bda05120e8baa121c0848efa` | - |
| `results/sim/pilot_fov_hfov70p4.jsonl` | pilot or test run (no analysis) | 58477c6 | 41,324 | `ddf414a64894cbb63466cecf8cda94ae63ca83793d29dedb4099ee711c0d6445` | - |
| `results/sim/pilot_light_p2ev.jsonl` | pilot or test run (no analysis) | 58477c6 | 41,256 | `294f9470219012facf9d5d4b4cccfa0f7eab5c1e43e7f6736100bcb523daa766` | - |
| `results/sim/pilot_nominal.jsonl` | pilot or test run (no analysis) | 58477c6 | 205,916 | `2e23791e851c43e0e88434e2fe15ce9c39b3160efdc4d72bfde0081faca29a55` | - |
| `results/sim/pilot_rack_x_p6.jsonl` | pilot or test run (no analysis) | 58477c6 | 41,302 | `22f3a7a1d52237df48bcb494140b41c46dd463e948222f640d3efc3c3f5aca7a` | - |
| `results/sim/pilot_rack_y_p4.jsonl` | pilot or test run (no analysis) | 58477c6 | 41,298 | `f2779b4cebe498d84fb51988ad4763407eb3523072b5ab8a24e3feb03c3abdce` | - |
| `results/sim/smoke_nominal.jsonl` | pilot or test run (no analysis) | 3354c6f | 8,245 | `a0afb5694e3f7a8cce5b5e46ee94e020ee12adb2ec604c0d64d6876cdb7398fe` | - |
| `results/sim/stoptest.jsonl` | pilot or test run (no analysis) | 58477c6 | 8,223 | `004398db1ec6e6e8de8417a415e479e6bd4966bd1ff2cebf69c90411a639ed3f` | - |
| `results/sim/t06_probe.jsonl` | pilot or test run (no analysis) | 32d3055 | 92,134 | `65348db0f4f4fb5bce721573e7da969c9c031a9f1a8da151dcfe2110aaae521d` | - |
| `results/sim/t07_b.jsonl` | pilot or test run (no analysis) | 46d5d86 | 18,707 | `c16931e9965d978bf5506fd9ad14e47b31f0f23f7356ccfbe061c16c95b1aae3` | - |
| `results/sim/v05_t07_a.jsonl` | pilot or test run (no analysis) | 46d5d86 | 108,964 | `4fe3e77743f130e12e8f14e806d026c1dbe047335bce5d391d4072ae61f9f7a0` | - |
| `results/sim/v10_test.jsonl` | pilot or test run (no analysis) | 58477c6 | 7,874 | `31a0aedc35c7831efefd398a6590fb71eca2d81474d5c4d629905462f87df272` | - |

## Notes

- **Blind keys.** Written November 9, 2026, 22:40 PST, with the clips and the blank sheets
  (`tools/blind_rename.py --batch`). They were kept out of gtc's git history (git-ignored) and sealed until both
  batches were scored on November 10. Their SHA-256 were committed in gtc `459293f` and published in addendum entry 4
  (commit `74a7833`) before scoring started. Each `.sha256` file names the key's gtc path; to check a key here, run
  `sha256sum results/real/blind_key_A_20261110T064043Z.json` and compare it with the value in its `.sha256` file.
- **numbers.json.** The numbers are those of the build that made the submitted poster PDF (SHA-256
  `e0d3f6747c919f8b390647467e44a83b7b0ec9f489f96928716c7316673cd50b`, November 10, 13:16 PST). After submission its
  header was marked final in gtc `3a78356` (the `draft` field, "DRAFT for review", became `version`, "final"); all
  214 entries are unchanged. Each entry's `status` field gives its status (26 entries are "blind-scored (final)"). Its
  `source` paths are relative to the working folder: `prereg_repo/...` is this repository, and `gtc/...` is the private
  repository. A `gtc/` source copied here is at the same path without the `gtc/` prefix, except numbers.json and the
  two keys (table above).
- **Edits to trial records.** Changes made after a record was written are logged in the record itself (`relabel`,
  `flag_edits`, `note_edits`, `record_recovery`), with the time, the reason and any earlier value. The trial-level
  deviations are in deviations.md.
- **Not copied:** the phone recordings, judge clips and trial frames; the clip-cutting logs (their video metadata
  includes the phone's location); the per-step logs (`results/real/steps/`); the audit copies of trials.jsonl made
  before each edit; the exploratory simulation runs (`results/explore_v1/`, `results/explore_v2/`); the E3 code.
