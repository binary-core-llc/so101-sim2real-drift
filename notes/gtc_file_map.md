# Files copied from the private working repository

The study's working repository (`gtc`) is private, and its history is not published. The files below were copied from
it on November 10, 2026, after the poster was submitted, with gtc at commit `1a753d7`. Each file is byte-identical to the
file at the gtc commit named (the commit that last changed it); none was edited for this copy, except the files listed under *Edited for this copy*.

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
| `notes/sweep_v1_summary.md` | `notes/sweep_v1_summary.md` | eab4b75 | 5,675 | `25be53727c597bb10b23c403c6da5c0ce469d4c357bd1b2899078933b8b23aa9` | sweep v1 results per cell (k/n, Wilson interval, Fisher test against S0) |
| `results/poses/r0.json` | `results/poses/r0.json` | 622d273 | 1,090 | `f5dacfb9912e3e6edfe870c9d8d9fef48298806f37614de5a5c514f69e400212` | R0 camera pose from the ChArUco board (PnP), mean of 5 photos |
| `results/c1/nominal_front_rgb.png` | `results/c1/nominal_front_rgb.png` | b915482 | 210,355 | `e02d499eb05978337e82a79eb0a49b2f92b6def44b49d0a5a0b5c8cec12a64c2` | nominal front-camera image of the simulation (640 x 480 render) |

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

## Exploratory simulation runs (`results/explore_v1/` to `results/explore_v3/`, `notes/explore_v*_summary.md` and the explore-v3 plan)

34 files, 11,606,678 bytes; same paths in gtc. All are exploratory, not pre-registered. The cells were added
after sweep v1 finished: explore-v1 and explore-v2 ran on October 24-25, 2026, and explore-v3 (1775-step episodes) on
October 25 (Pacific time). Every simulation result numbers.json takes from them is marked "final sim (exploratory, not
pre-registered)"; the protocol value `real.cap_chunks` also cites `notes/explore_v3_summary.md`. No earlier file records
their hashes; each SHA-256 below was computed from the file here.

| File | What | Status | gtc commit | Bytes | SHA-256 |
|---|---|---|---|---:|---|
| `results/explore_v1/X_bump_mild.jsonl` | exploratory cell, 40 episodes | exploratory, not pre-registered | eb2ccaa | 168,204 | `7f25d150b387c19651669af9eaf30135422a1dc0da6ef8d13f74b679d57cd83f` |
| `results/explore_v1/X_bump_strong.jsonl` | exploratory cell, 40 episodes | exploratory, not pre-registered | eb2ccaa | 168,263 | `790aed08c437233e69099761d14aa6a662f69a3d15ae0d9ac9f5e93f1cf1957b` |
| `results/explore_v1/X_rack_y3_tilt_down_6.jsonl` | exploratory cell, 40 episodes | exploratory, not pre-registered | eb2ccaa | 166,967 | `26090a2221442e3c78ee412f17f9355af8a063befe49cb6f64e12a43726922ab` |
| `results/explore_v1/X_roll_10.jsonl` | exploratory cell, 40 episodes | exploratory, not pre-registered | eb2ccaa | 166,427 | `75ea3bfeb89172936e6be05de2b09ef290f180ce8d27c7b8c10fa559e208b755` |
| `results/explore_v1/X_roll_5.jsonl` | exploratory cell, 40 episodes | exploratory, not pre-registered | eb2ccaa | 166,692 | `c5d1ae67694ce5a7896b139d34fb3b507cde67d8fac2c3a94afb28e51cc97450` |
| `results/explore_v1/X_tilt_down_10.jsonl` | exploratory cell, 40 episodes | exploratory, not pre-registered | eb2ccaa | 166,886 | `9288a290ac0a637bb01b77fdbf8b55dacf9dc7346b947fe3a23f9e9d7b12ba33` |
| `results/explore_v1/X_tilt_down_12.jsonl` | exploratory cell, 40 episodes | exploratory, not pre-registered | eb2ccaa | 166,856 | `aa32c7431e68e72a500d1e62311ae8d408751e0d73b3f0c97d52e8024e156981` |
| `results/explore_v1/X_tilt_down_15.jsonl` | exploratory cell, 40 episodes | exploratory, not pre-registered | eb2ccaa | 167,105 | `f9a3fb4fd19d8607656c9bd0fdeb5b9c29a07f3e67f39617ca3e550aaa97732e` |
| `results/explore_v1/contact_sheet_explore_v1.png` | first front-camera frame of each cell (simulation render), labelled | exploratory, not pre-registered | 469435b | 2,987,770 | `8cb7e9a6a8afa16ca5e3b03fdf96e09b52496a001a336c309b1dc27ea8382a5a` |
| `results/explore_v1/explore_v1_summary.json` | summary of the cells | exploratory, not pre-registered | eb2ccaa | 7,566 | `359940bcdf9c364950e5335a5245670cdc5e8ab7b3a479da3693b3d1c44a5cc9` |
| `results/explore_v1/framing_explore_v1.json` | framing check per seed: which objects are fully in frame | exploratory, not pre-registered | 469435b | 292,598 | `5a2f5e946d1e9eed4cc1028a44071c13ef853b047939896f43892b7c5fa27333` |
| `results/explore_v1/framing_sweep_v1_top.json` | framing check per seed: which objects are fully in frame | exploratory, not pre-registered | 469435b | 229,923 | `122f42af0a70e69f1c480708318096ddc184fb07997f8cfda86e56c05354d194` |
| `results/explore_v1/probe_explore_v1.jsonl` | probe frames: camera and object poses after reset and 10 warm-up steps, no policy | exploratory, not pre-registered | 469435b | 33,421 | `3ffaa623a2d3b62943100d473ae666067971e463ce8f84c67da789c4812c2f7c` |
| `results/explore_v1/probe_explore_v1_framing.jsonl` | probe frames: camera and object poses after reset and 10 warm-up steps, no policy | exploratory, not pre-registered | 469435b | 1,339,964 | `c4a25ab01b6d94130306f6b0991077d6243059fa7c93ef780d9797711bb5672f` |
| `results/explore_v1/probe_explore_v1_tilt15.jsonl` | probe frames: camera and object poses after reset and 10 warm-up steps, no policy | exploratory, not pre-registered | 469435b | 148,372 | `62f86123623120738f2f4891ebe16665832d3b4c2f76fd8d792196c2658e5e50` |
| `results/explore_v1/probe_sweep_v1_top_framing.jsonl` | probe frames: camera and object poses after reset and 10 warm-up steps, no policy | exploratory, not pre-registered | 469435b | 1,034,586 | `554f2f36282e1b8b06a720fc77a16699e0d04411f7f5f9790795b8e127de39b7` |
| `results/explore_v2/Y_R0_course_text.jsonl` | exploratory cell, 80 episodes | exploratory, not pre-registered | 966e83f | 360,829 | `d7d7b5c83370a105e847c5bb803e5ca953a80a9359ee322fd6608985028e31ed` |
| `results/explore_v2/Y_nominal_rack_sentence.jsonl` | exploratory cell, 200 episodes | exploratory, not pre-registered | 966e83f | 877,163 | `418ecee9e6b653db45dc334c465afadb4ea75eecc5a37b2211ccead19533a32c` |
| `results/explore_v2/Y_tilt_down_13.jsonl` | exploratory cell, 40 episodes | exploratory, not pre-registered | 966e83f | 176,014 | `786048370fe534e16206dd2f36e315d9d36b51ad6662d15c86c19891c37b771c` |
| `results/explore_v2/Y_tilt_down_14.jsonl` | exploratory cell, 40 episodes | exploratory, not pre-registered | 966e83f | 175,924 | `d31e62547916ad2a5965be0163d90b663dfb5d7a7bef73c9c2441e5c1a17a5e2` |
| `results/explore_v2/contact_sheet_explore_v2.png` | first front-camera frame of each cell (simulation render), labelled | exploratory, not pre-registered | a0b0db3 | 1,317,414 | `b489a9ef8fa014f5ed5f114590da1b7431bc58348a3926c3bbf4df968d7f7b50` |
| `results/explore_v2/explore_v2_summary.json` | summary of the cells | exploratory, not pre-registered | 966e83f | 5,411 | `783fea96c47617f66c15a74760da84475c4c0f5f2cf36e9ba72daa9295273389` |
| `results/explore_v2/framing_explore_v2.json` | framing check per seed: which objects are fully in frame | exploratory, not pre-registered | a0b0db3 | 130,002 | `fd725230e62d0069585a6cd03effee542677af7d209a727a6611a9a3a8ddf7ee` |
| `results/explore_v2/probe_explore_v2.jsonl` | probe frames: camera and object poses after reset and 10 warm-up steps, no policy | exploratory, not pre-registered | a0b0db3 | 599,919 | `a00f50216ae84651207fd858267e29a578c279d04b931719347be198699c3eff` |
| `results/explore_v2/tilt_failure_modes.json` | failure modes in the 12-15 degree tilt runs, with S0 for reference | exploratory, not pre-registered | 28be591 | 2,619 | `5aab8454b713742011b0dbb0858d2c82c2c6aaeade799af8c1c8088770b4435a` |
| `results/explore_v3/Z_nominal_long.jsonl` | exploratory cell, 40 episodes of 1775 steps | exploratory, not pre-registered | 42722dd | 175,327 | `e99847f636b8f5d87f44cad26b7fdbc8b1280e8a02229ff74f89754bd0b5a478` |
| `results/explore_v3/Z_tilt_down_13_long.jsonl` | exploratory cell, 40 episodes of 1775 steps | exploratory, not pre-registered | 42722dd | 176,243 | `e7fbd34b2324ca08dc24159d41eea174496990201966895d34d3d8679d579884` |
| `results/explore_v3/Z_tilt_down_15_long.jsonl` | exploratory cell, 40 episodes of 1775 steps | exploratory, not pre-registered | 42722dd | 176,287 | `51a6071fb8db3310cee84d4b6eb8f18e590551110a3a34542369cc5d9357f644` |
| `results/explore_v3/explore_v3_successes.json` | release chunk of every success | exploratory, not pre-registered | 42722dd | 11,787 | `02e0eb8849bd6e5907576707befa11a93909babaebae72d168381a2737076cc4` |
| `results/explore_v3/explore_v3_summary.json` | summary of the cells, the latency cutoff and the rule | exploratory, not pre-registered | 42722dd | 3,245 | `3251000415c212b05c0dc68d9a6e2d5e272eb7e4c442aa5dd6b6bbdfd6e92be4` |
| `notes/explore_v1_summary.md` | summary table of the cells (k/n, intervals, tests) | exploratory, not pre-registered | eb2ccaa | 1,486 | `ee5188479f4fc77f3b8af312e0c0cdd2a260e2622ff9a6e7b7a6d323313a1b1a` |
| `notes/explore_v2_summary.md` | summary table of the cells (k/n, intervals, tests) | exploratory, not pre-registered | 966e83f | 989 | `6460e1beb892c0849e06734ff2d47062251c5199ef1e4de8b7a2972ad2c09670` |
| `notes/explore_v3_summary.md` | summary table of the cells (k/n, intervals, tests) | exploratory, not pre-registered | 42722dd | 1,596 | `46a6ae365ec4f197566c4070505f2133eb550287a2a5360fd056a5bfb8df4a0f` |
| `notes/explore_v3_plan.md` | explore-v3 plan: episode length, cutoffs and rule, committed before the first episode | exploratory, not pre-registered | 6e7dea5 | 2,823 | `eeea08365a727bffd6fe3d1335c6afc411f76693df25d33586c94d3d936bc4db` |

## E1 and E3 results on simulated scenes (`results/e1/`, `results/e3/`, `e1/`, `e3/`)

5 files, 32,016 bytes: result files only, and the E1 selection script. The E3 code is in its own section below. `e3/validation_synthetic_cem.json` comes from the private E3 repository at the frozen commit `399025f` (archive
SHA-256 `17fed03e9c82f4c9b05a70da541e23c3e0c4d536c1773de0857fa08395312291`, addendum entry 3); its source column gives
the e3 commit that last changed it. numbers.json marks the E3 numbers on the simulated selection scenes "final sim (E3
development set, not held out)".

| This repository | Source | Commit | Bytes | SHA-256 | What |
|---|---|---|---:|---|---|
| `results/e1/selection_eval.json` | gtc `results/e1/selection_eval.json` | gtc fe210f2 | 11,490 | `896ce5240474c2fcefce26fa5deefbd35b3f6f121b71842d5536f6541b3be179` | E1 variant selection on the simulated selection set (v2 item 2b) |
| `results/e1/selection_truth.json` | gtc `results/e1/selection_truth.json` | gtc a294ec3 | 4,104 | `b25084948d239ef173532f16b5eb9fabe41c91cd6ea271dd3116f293778efcd5` | true camera and rack offsets of the simulated selection scenes |
| `e1/eval_selection.py` | gtc `e1/eval_selection.py` | gtc ca77e84 | 4,112 | `a8651dce5f3fadc8ea4a7d7a71d54fdb038a23a943adc1c077816c790fbd3071` | the E1 selection script: error metric and selection rule |
| `results/e3/simset_e3.json` | gtc `results/e3/simset_e3.json` | gtc fe210f2 | 6,867 | `57af5e1c28a257155bb477081a1f47853524ba09d0a411b3eae70e36fc919b9f` | E3 estimates on the same simulated scenes (development set, not held out) |
| `e3/validation_synthetic_cem.json` | e3 `validation_synthetic_cem.json` | e3 6eea643 | 5,443 | `743ec4cd1269813cca4973777cb878bf84861665a44a7f6478e261a738933365` | E3 validation on synthetic scenes (CEM search): largest camera and rack errors |

## Per-step logs of the real trials (`results/real/steps/`)

61 files, 13,156,084 bytes; same path in gtc. One file per trial record (named in its `steps_jsonl` field) and
one JSON line per policy chunk: query, reply and send times in seconds from the first policy query, the latency, the
joint readings and the actions sent. They were last written on November 9, 2026, 20:24 PST, and committed to gtc
unchanged on November 10 for this copy.

| File | gtc commit | Bytes | SHA-256 |
|---|---|---:|---|
| `results/real/steps/N04-001_a1.jsonl` | 6f835c0 | 225,315 | `1577bde33f0dd1181a0857896de36efeb483f5fb9a2196cb67e051394322e308` |
| `results/real/steps/N04-001_a2.jsonl` | 6f835c0 | 208,528 | `ec9df3057e6044a0a1933794842a12d01b59d9159d0e9b4ed2e765d406970f87` |
| `results/real/steps/N04-002_a1.jsonl` | 6f835c0 | 220,485 | `53ceda64826fbdb36ace1d3885dab245f6186b08d0010846c0edcde123bcc38e` |
| `results/real/steps/N04-003_a1.jsonl` | 6f835c0 | 170,669 | `01244bf9653e8a54ccce54802408209558c2dfe255cf89cdac5cd78bdff2623a` |
| `results/real/steps/N04-004_a1.jsonl` | 6f835c0 | 153,873 | `60d5c1e95aa6e05a058357f3415e20781bc564559557314685cda93a12dd6c2f` |
| `results/real/steps/N04-005_a1.jsonl` | 6f835c0 | 141,513 | `4fbb65388bce24e70911ec280442713503fe4d90cf508123fc593c40c053e37c` |
| `results/real/steps/N04-006_a1.jsonl` | 6f835c0 | 141,629 | `54ca88b91ffc4fb6d072f97506410f273038f463b4be63b0dec6e260dd9a1b26` |
| `results/real/steps/N04-007_a1.jsonl` | 6f835c0 | 267,681 | `f4769db1d64ae5f5f01ed0c460e6807530cf364c053ad111b0003464e30757f3` |
| `results/real/steps/N04-008_a1.jsonl` | 6f835c0 | 208,567 | `0a2d938eef7a2e597b19267625c441f844e302e3ef515c0859dd5d7350f9472c` |
| `results/real/steps/N04-009_a1.jsonl` | 6f835c0 | 158,545 | `69dd96b9af44146fa0ac654cbdc13745e2d47ace55ecf2fc75b5edbf8003a248` |
| `results/real/steps/N04-010_a1.jsonl` | 6f835c0 | 116,507 | `1bb93ac394283c61f614f97a6c2745fb437b1eb1aec839b332d17a69c5fa5e0d` |
| `results/real/steps/N04-011_a1.jsonl` | 6f835c0 | 145,824 | `95e4c759f9bc5c0d15808216a1cc10c695bdc97b43775f999482ac80736f9a97` |
| `results/real/steps/N04-012_a1.jsonl` | 6f835c0 | 384,149 | `6208eacdc94893cbf6dbc84f79fba8b0f48949100803da0146cae5d460f00f51` |
| `results/real/steps/N04-013_a1.jsonl` | 6f835c0 | 166,957 | `44ad6a312fc1bc9acfe053bf146339cbb4bb6fb712cb1882a2c87e569c6bfcae` |
| `results/real/steps/N04-014_a1.jsonl` | 6f835c0 | 242,123 | `a72e2a0b77e2c6199a2c0384470f33757a4f65f370585b68927292112854dda8` |
| `results/real/steps/N04-015_a1.jsonl` | 6f835c0 | 158,223 | `a5092b6cedae53634c00da187240e1cbea9ad3d0269851eb0f7711d216eb6045` |
| `results/real/steps/N04-016_a1.jsonl` | 6f835c0 | 120,754 | `15b635fd4df62e778c81ab54c65401ad61a4ac05c59e1b028a465308e9c68391` |
| `results/real/steps/N04-017_a1.jsonl` | 6f835c0 | 384,510 | `8613a6bd98fbe818cc1ae12114684ebeb9b780708d2df7fe05a3906c4237d826` |
| `results/real/steps/N04-018_a1.jsonl` | 6f835c0 | 384,204 | `220f82dd9c7d990ae29f6f93486870e8840d547b953691b52c5ee0a98240c1c6` |
| `results/real/steps/N04-019_a1.jsonl` | 6f835c0 | 384,219 | `8d980ac0eb02fb516a366ae2d06379e0d4ffbdfe0d4a96739c2baa7388142f72` |
| `results/real/steps/N04-020_a1.jsonl` | 6f835c0 | 128,928 | `ae1415ee86908a9be6b4011b5962e2ebbd36174342f654a72c7d9cca3fd946ce` |
| `results/real/steps/N04B-001_a1.jsonl` | 6f835c0 | 279,667 | `a2ab2265d50758173698e123a72beb2e21652c426b060216c22994329bb264c1` |
| `results/real/steps/N04B-002_a1.jsonl` | 6f835c0 | 120,715 | `cd6bdb9cea82e9cfe3a4b7f7d1c444b6be31d4c5cb1c13bc6b9e0fa20f1ef7e1` |
| `results/real/steps/N04B-003_a1.jsonl` | 6f835c0 | 385,119 | `eb761da0a08c53ac2cc15b782a516bba2ad1b1c231f8cf7104aa7d8c273a7c5c` |
| `results/real/steps/N04B-004_a1.jsonl` | 6f835c0 | 154,082 | `ed7b9033e966a5bef0722a22d8970a84b83d854385ccadcb42a80efb9fd4240e` |
| `results/real/steps/N04B-005_a1.jsonl` | 6f835c0 | 112,368 | `115e36c89499612035500ee2bbb7efaa0855edc1ca353911e9b1800f751378f0` |
| `results/real/steps/N04B-006_a1.jsonl` | 6f835c0 | 124,959 | `5469746009db1fb5d4523f281751b711650ae48d4de449c008c379f8822fcc27` |
| `results/real/steps/N04B-007_a1.jsonl` | 6f835c0 | 104,099 | `53d28870bc21669a5f826d44074071964793310876111c900266d32a26aa4a6d` |
| `results/real/steps/N04B-008_a1.jsonl` | 6f835c0 | 158,486 | `e8ef49989d08a3c331dedd21daba9d488290716e7a82928565e862432c60e5a3` |
| `results/real/steps/N04B-009_a1.jsonl` | 6f835c0 | 133,355 | `76579c2c505b8a5a408ba7b9934e6d7066bbe564c9fd6ac2055c6d5a2d36d285` |
| `results/real/steps/N04B-010_a1.jsonl` | 6f835c0 | 166,875 | `bc5bb413cfebe79246cddda6810468c0ba738e968d47a1a53fe9defc3bf5618e` |
| `results/real/steps/N05-001_a1.jsonl` | 6f835c0 | 388,269 | `d1772f2b969b88bf9881e4c276a19c9053e9ccc33a4b96672520b6f891373bb0` |
| `results/real/steps/N05-002_a1.jsonl` | 6f835c0 | 388,983 | `ec1b5a8c91fd8ac3801ae6f0093c6a2d3d3faab0cccc5b91e0b09f35a4cfc4e6` |
| `results/real/steps/N05-003_a1.jsonl` | 6f835c0 | 388,200 | `383617395852d0dbd3a5cdc7d8cff51b70f2ff42f291eff798f4f68055b0c2e2` |
| `results/real/steps/N05-004_a1.jsonl` | 6f835c0 | 386,626 | `6af0ccd89ab294b706a0b5560a01363cb4677209b05cffdc4f8053fbfa3167f6` |
| `results/real/steps/N05-007_a1.jsonl` | 6f835c0 | 120,709 | `48a070d73f16ae04fa5074120ccc756c278ea484cfde85fb5a64784bb21d9408` |
| `results/real/steps/N05-010_a1.jsonl` | 6f835c0 | 133,227 | `1aea70f8746f676a37216a24d2db17fd7f8b257d6659d731740722955505dc1d` |
| `results/real/steps/N05-011_a1.jsonl` | 6f835c0 | 175,353 | `807688f83943a8779222924128d65e91fd8c03af95d1e76f582c9f82a56d4a8e` |
| `results/real/steps/N05-012_a1.jsonl` | 6f835c0 | 296,571 | `9c5ddfe9f8221c102a219f29e2493301f5e87e36562ee6728df3184520073a88` |
| `results/real/steps/N05-013_a1.jsonl` | 6f835c0 | 112,406 | `f48fd37fa3a9e2ad6c91949b194d10392e1bc1290607c95309e82b2b2364ac8d` |
| `results/real/steps/N05-015_a1.jsonl` | 6f835c0 | 359,268 | `8e3096feddf6f83d36609572137c21fc93a5ecf5d3f5ed4c9761608a4e937dce` |
| `results/real/steps/N05-016_a1.jsonl` | 6f835c0 | 195,861 | `280583051fefef8e2b60c49a625d0f03f27327d40ff6bc36a5cc72029d9b601d` |
| `results/real/steps/N05-018_a1.jsonl` | 6f835c0 | 296,395 | `08312d3671cde6c4ab09a33f3362616a428f75721ecc55f64e1e27c46cc70339` |
| `results/real/steps/N05-022_a1.jsonl` | 6f835c0 | 383,759 | `a7f67a084ae7609bf8af7975dd9cee9c392dd65e492d3850f9c4c17e7bbdf5b4` |
| `results/real/steps/N05-023_a1.jsonl` | 6f835c0 | 258,481 | `143e0023f73a12a8abbea3633145e2a420c29a6f0d248962afee020f73df709d` |
| `results/real/steps/N05-024_a1.jsonl` | 6f835c0 | 125,086 | `572ef2c4b6dea6bbb7f9ed9fdbe8a7e82e2eb907c3aa44ad7446a68fbf723922` |
| `results/real/steps/N06-001_a1.jsonl` | 6f835c0 | 241,883 | `6c2ea2e07280a3288c37bae8724e397553df2a065b2a42c257120c4227a9301d` |
| `results/real/steps/N06-002_a1.jsonl` | 6f835c0 | 199,518 | `6c65d21f4994c41acd16a7da0d53ee6e0f20c51f875753e0fb05b327f7dcddfa` |
| `results/real/steps/N06-003_a1.jsonl` | 6f835c0 | 116,608 | `60025751195425f2becdd3554ec43c0b323fb66c78bd2164f977587f26d3593b` |
| `results/real/steps/N06-004_a1.jsonl` | 6f835c0 | 387,750 | `750fe50100209d59449197355de38534b8a1ee107271a229091de8935e87d772` |
| `results/real/steps/N06-005_a1.jsonl` | 6f835c0 | 141,540 | `320d5dc76fac4cf2b37f65e313719f3f3d6862e0de627a27ae92a95197316220` |
| `results/real/steps/N06-006_a1.jsonl` | 6f835c0 | 116,582 | `56da302d52b6f1e73860a55d7f5a17980cf562ad26bd8daec30fb1f2d8e24161` |
| `results/real/steps/N06-007_a1.jsonl` | 6f835c0 | 146,096 | `33f261acf5b300f42612b2b94a14b878f0831b716193553d417a19c048bd9092` |
| `results/real/steps/N06-016_a1.jsonl` | 6f835c0 | 187,678 | `211752298ca49de695162950f149f2ad3ab97c2dde347b67bf7f2dca8de7f91b` |
| `results/real/steps/N06-017_a1.jsonl` | 6f835c0 | 171,047 | `c3e6ba068e6c0ea3ee8f5888fcc0adccfac89cb4454fa195d3af2d691fdd299f` |
| `results/real/steps/N06-018_a1.jsonl` | 6f835c0 | 129,368 | `38a7880f256ee91d7de9b770075eedb3967bc04e7d8156bd47556bb8abd6d2dc` |
| `results/real/steps/N06-019_a1.jsonl` | 6f835c0 | 200,075 | `27a09eb4ea3f35e43b1ab7a3cd96c8ab1e2b56a4796592d3f5513100097ee9c5` |
| `results/real/steps/N06-020_a1.jsonl` | 6f835c0 | 150,049 | `49032cabdec288abe6c2ffb70e4106de3b28177661d474a65ee6f407fbb0003f` |
| `results/real/steps/N06-021_a1.jsonl` | 6f835c0 | 120,937 | `0dc5486d1f785247bab26df92036ad0449c7c6a0da3fb14d7686a16e84a23597` |
| `results/real/steps/N06-022_a1.jsonl` | 6f835c0 | 195,703 | `7d672d224fb069e2fbcb249fc06c790a775251dbc82cc34d9d45360a5e6d7adf` |
| `results/real/steps/N06-023_a1.jsonl` | 6f835c0 | 389,128 | `d4e9858c15a21cdb52c09888dad340be84a40dea30c416a042f5639f585ae3ed` |

## Code from gtc (snapshot of November 10, 2026)

165 files, 1,881,914 bytes, from gtc at commit `1a753d7`, at the same paths. The folders: the calibration kit
(`calib/`, `stencils/`, `config/`), the trial runner and robot tools (`real/`), the pose and scene tools (`tools/`), the
simulation scripts (`sim/`, `docker/sim/`, `assets/local/`), the analysis (`analysis/`), E1 (`e1/`), the exploratory
runs (`explore/`) and the tests (`tests/`). gtc commit `1a753d7` holds the clean-ups made for this copy (wording, unused imports, imports at the top of the modules, input files found inside the repository); the code files here are byte-identical to it. 16 files replace their prereg-v1 versions on `main` (the tags keep the registered ones); 14 were
already here byte-identical. The SHA-256 and size are those of the gtc file; 4 files were edited for this copy
(*Edited for this copy*, below).

| File | gtc commit | Bytes | SHA-256 (gtc) | Note |
|---|---|---:|---|---|
| `analysis/blind_results.py` | 6f79f5e | 9,712 | `8a3b83a3c5b123b1306c4514bdd23d05261c299f78ec7292372ee38773a197f3` |  |
| `analysis/real.py` | 9deff18 | 16,396 | `25554ae90b10a91041d98eb872e59409ef9a346a4e682d41119ef015dcc26f7b` | already here, unchanged |
| `analysis/stats.py` | 9deff18 | 12,868 | `52029aacf72c7360ddc828be7d520dbe92ed45a2f0e5c5c30869069e9074cf8a` | already here, unchanged |
| `analysis/thresholds.py` | 9deff18 | 11,758 | `f686b996c4a95cd101dfd4e53f60eb455335c1e1c38483bb49ee92c8b8cf4d4b` | already here, unchanged |
| `assets/local/SO-ARM101-USD.local.usda` | 81cf5ec | 776 | `14a38f1c7423e117fdfc1cb354110fc070706d65bf2707ac5af0229527b4f64d` | replaces the prereg-v1 version |
| `assets/local/Vial_opaque.local.usda` | 81cf5ec | 752 | `3780cda1bfa4aef9a6ba20e9a3fc23c5c857371ce60920312f976313900ab623` | replaces the prereg-v1 version |
| `assets/local/lightbox-simple.local.usda` | 81cf5ec | 1,403 | `6d46a7703bf7d4553880dace1e717a7f22da46d054cdf7b46b64261da768f4e6` | replaces the prereg-v1 version |
| `assets/local/mat.local.usda` | 81cf5ec | 1,090 | `5e01f67994719eb755654b52a76d149124d226c53604f784f48fb6e2cf2d6158` | replaces the prereg-v1 version |
| `assets/local/wrappers.json` | be85ea4 | 2,931 | `2a505d093a72a06414d9795cf6e360746d9c0649677ac6ffade4427665624e54` | already here, unchanged |
| `calib/aim_view.py` | 2bd7d90 | 5,120 | `33671a0130be1afebbbf48d4f8212a99ba8aba46174578079810f44ee4d37871` |  |
| `calib/base_view.py` | 1a753d7 | 8,750 | `3d71a19085c7f8d0403936f4b85ab55a3c38773532d5bf7eca40e7d4517a066e` |  |
| `calib/camera_lock.py` | 1a753d7 | 14,647 | `0b1ab5f5ed3d2b65e01af1e0b4e9b6c4b4be6632f4ccac626466edc8e6068e3e` |  |
| `calib/capture.py` | 1a753d7 | 6,527 | `fc044218256d552c06faef557c6b886dbc8abeb1e088029da98aaafab0034840` |  |
| `calib/charuco.py` | 1a753d7 | 10,906 | `3d61526842e63eddad554723921b9a844ba8213ceb7a7b9d039708631922807b` |  |
| `calib/dev_photos.py` | 1a753d7 | 7,041 | `965d50c484b9a2326c78409e4b945620404a649cd7ae41526961f1df84064172` |  |
| `calib/drift_check.py` | 1a753d7 | 10,264 | `55e3a8a5357f7debd41de6789d7f2711966eeb39191ffc192b3443f62e13c8b3` |  |
| `calib/intrinsics_capture.py` | 1a753d7 | 16,272 | `c3912bea4d4f81768f11cb74d6796a63e39fc4bb0344ce0a98698a277ac599b9` |  |
| `calib/intrinsics_solve.py` | 1a753d7 | 16,043 | `84b37004c42146fa1f2465491d3947fc7ceba75f0d389db1c17218a0858d6337` |  |
| `calib/kcheck.py` | 1a753d7 | 32,930 | `b40359a734b7b9a3a31ff8c58337864b38256b26f86bd306e9dcc8d87566bb22` |  |
| `calib/light_log.py` | 1a753d7 | 6,716 | `4575c287709f81db5472e260136aa2d576ac3c78e48764a446fe4b3c063c1dbe` |  |
| `calib/light_view.py` | bd77a67 | 3,565 | `0324ed2c346b04471825997495afa1268e6437567b24f8e3d085f49428786f3c` |  |
| `calib/live.py` | 1a753d7 | 3,945 | `a76819cd2cb52b795e292d52749cca6da923df8323cf8c6c4579a4e42f34ca34` |  |
| `calib/mat_view.py` | 536d8c0 | 5,449 | `ff8945cb740df0dd6443266ae148297c97cda74e41aa0c2757417afb67d0f2b0` |  |
| `calib/overlay.py` | 1a753d7 | 6,693 | `3b5a7887b884b5199e4442a10f9b7bc7c00631b3f5f554e1217c37c2f38bc571` |  |
| `calib/pose.py` | 1a753d7 | 29,845 | `5f677058f9359ada4fa9ffffd345ba2cf8cda0ab8f26c40a382255e756d2264c` |  |
| `calib/preflight.py` | 1a753d7 | 6,034 | `52d915f455cd6e2e0b587b21c3fa43d3f0197e0234fbd591d4a4331e674bd079` |  |
| `calib/rack_ref_view.py` | 1a753d7 | 8,411 | `9c4f2d74b46be46d5467ee8a6eee5ba67aed1d29beed76bd282e3e8ab06c1240` |  |
| `calib/rack_view.py` | 08539b6 | 17,586 | `6a7048aea70dd419876fdb742777ceeb839899720270b89acb238b06034ba42b` |  |
| `calib/record.py` | b4e8d84 | 1,271 | `016369e9391090307cca7b72c5aea0b514d5867bc5882e6633aee68bce2fff44` |  |
| `calib/still_check.py` | 1a753d7 | 6,848 | `238fe2d231900a4cceea513826517294330378905f6c94b08dc9ee55d0bdd085` |  |
| `calib/sweep_record.py` | 53a253f | 2,978 | `7de9b35fbbe0e0058532487e9ed4675a83e74aea6b7841628507c09c848c5b99` |  |
| `calib/usbcam.py` | 1a753d7 | 7,174 | `d229075349cec480aca131bac9e8a2be293495b31177b8f82084a4ba757dc7e5` |  |
| `calib/v4l2.py` | 6c3069c | 5,369 | `5f589d86058b0523bb7c734d8764aeaf0732472646c3e282bed889e8510640c4` |  |
| `calib/vial_view.py` | 1a753d7 | 5,532 | `e6cc85e334518c1804df950cf2313a1703bbafbdf6f34f79814d3a515bde258f` |  |
| `config/board_in_E.json` | 622d273 | 2,140 | `efc6c3cc3c11175b97d1f148170b377be475bc0f176bbbf7bfa5b3956da16f83` | edited (below) |
| `config/board_in_E.template.json` | 6c3069c | 1,055 | `c7f0b9d42ebe19abe6e16d20c99132fa9d3eba501412f55da63e619f19111540` |  |
| `config/c920_intrinsics.json` | 23ac113 | 9,655 | `2e441eeec7142131bd240d84fbcba2da8393d1a129917defa86bcc0529d55e11` |  |
| `config/camera_lock.json` | 1a6f566 | 13,094 | `70a8d5d89bd41c02240786b73907f5c7cc4886c193aed6eaf9792bcee5ad877d` |  |
| `config/cells_active.csv` | 0f2b1f7 | 18 | `d0f97c9e98f4537e343fdd3326f231a8dd20d0468f7086b77cce31c929827288` |  |
| `config/cells_dryrun_v1.csv` | d46e985 | 3,062 | `f2fa01b287e8019317885a6483fbdba4701b7440367e1e4899389b55066cbdd0` |  |
| `config/cells_pilot.csv` | 3354c6f | 1,833 | `473f6f82f8f09b06c993073b70a63458f6b319cca207b7f6320821efa0566b72` |  |
| `config/cells_stoptest.csv` | 58477c6 | 237 | `f4e062f92c2d8cf56ea1d854eeb591f298e63dfaa27ac1c1586856e2e2dbe535` |  |
| `config/cells_sweep_v1.csv` | d46e985 | 12,084 | `263e6f8c865a1d3120607f56560746eac4622d3dee83d81372400b41f122830a` | already here, unchanged |
| `config/cells_sweep_v1_mapping.json` | d46e985 | 17,707 | `3ece94a3d3a0b3544a997e161bb30ff6ace980e47e859e3ae5c03d10db6ceceb` | already here, unchanged |
| `config/checkpoint_source.json` | b3f354c | 4,015 | `b95883a908bd8ceb30e72f0a0cd573b829f02e06d7b7762e1655b393243449ce` |  |
| `config/explore_v1_cells.csv` | 469435b | 2,754 | `c49c5ebfabf6deb34e9419042daf85bffa9aa0434c50df963c59cc7f0ce2ca62` |  |
| `config/explore_v2_cells.csv` | a0b0db3 | 1,760 | `e292161ba68c0e7622783645cb4c3faf26572faa70f5607d0c513d0c34f80719` |  |
| `config/explore_v3_cells.csv` | 6e7dea5 | 1,107 | `f4a4000f3a3037a1539cd7b13fc3fe6ae14a56499f566a0a8d89d9e3dbab40e8` |  |
| `config/kcheck_poses.json` | a700d9a | 11,053 | `747c9244047e9c7d03e07f6dc8493b47874a3e0b039f66776adf4ad001cde7f7` |  |
| `config/layouts.json` | bd8cbaf | 23,055 | `3a10a65f34f4c851001e0833945e114763c2dd399410e759dd42a1b8a24a14a7` | replaces the prereg-v1 version |
| `config/prereg.json` | 26be070 | 878 | `bacdd1625b2d34d6f44a2942de2a5a456201a83dc6f6a2d10376767bb4706b5a` | edited (below) |
| `config/probes/explore_v1_sets.json` | 469435b | 1,037 | `140742d6ba4ced1dd9340b9d6029e85382ad6a70851a796a769cb2c0a10f9c1f` |  |
| `config/probes/explore_v1_tilt15.json` | 469435b | 110 | `20dc92091d3e2647dea7f64fc24eb569b39f4ed1c1cf602b6f1a12554b215007` |  |
| `config/probes/explore_v2_sets.json` | a0b0db3 | 543 | `59592221885405a6bc8077e8e7f5e4799a9754d033851765906671fa705fa91b` |  |
| `config/probes/sweep_v1_top_levels.json` | 469435b | 644 | `02e0fe840b3ae1f4ce165f43162da3b02ff758e271c638a9502a0b3d7200ad89` |  |
| `config/probes/t05_t06_sets.json` | 32d3055 | 2,215 | `c808ee01b9e4a837294a0f6c80dbdb6902c03b9b2e1cf205714a831ee2194246` |  |
| `config/probes/t07_b.json` | 46d5d86 | 185 | `8bca1b4ae02e9ae75b91871034b4b90f0ebd909d9eaeb4c5337ac3a0176fda27` |  |
| `config/probes/v05_t07_a.json` | 46d5d86 | 48 | `d08899b27f5783a899631bcdcbbd53524005db1c1fa475b649e31f3173e6f0e7` |  |
| `config/r0_pose.json` | a0b0db3 | 1,046 | `ef6768342fdd8805ab9390d43b1d587baed70540b125f4b7e325ada3ed81c497` | edited (below) |
| `config/schedule.csv` | cb83c80 | 10,210 | `cd776ae4b5e0ddb16bee1005e15c573a1870f8461298424cb277c806699f4397` |  |
| `config/sign_table.json` | 32d3055 | 23,383 | `ef704dff9dddfe08d2ee05ba173aa3adab430d2c60a48098e374b1d17a8ba1d8` | already here, unchanged |
| `config/versions.json` | c6e9ac6 | 17,085 | `3c9d7303bb831b54d9e223318725276653504b787b3c1423beaafeb8f34694e6` | edited (below) |
| `docker/sim/Dockerfile` | 81cf5ec | 3,505 | `0a842bf3bf385afb8e02442d07bb8fed45db20080f28185728d7f308d01787ef` | replaces the prereg-v1 version |
| `docker/sim/Dockerfile.diff` | 81cf5ec | 1,959 | `1669924b03382a39791e9eda88a6efbc894ab4d906a3b76282faa19586a61530` | replaces the prereg-v1 version |
| `docker/sim/entrypoint_offline.diff` | 81cf5ec | 863 | `3290f975eef21f36edebda6a65df7f72df14fd01690c9266db7328c830f01a37` | replaces the prereg-v1 version |
| `docker/sim/entrypoint_offline.sh` | 81cf5ec | 1,051 | `d2432e24dd1dc6761ca7214a1b9fc9004c5b0dfd22674eb743ab3105e87eb3f2` | replaces the prereg-v1 version |
| `e1/e1_estimate.py` | ca77e84 | 12,639 | `69c64462d150c1061949bfbce36ba3842fe3230450cd716f595dbd43af713a34` |  |
| `e1/eval_selection.py` | ca77e84 | 4,112 | `a8651dce5f3fadc8ea4a7d7a71d54fdb038a23a943adc1c077816c790fbd3071` | already here, unchanged |
| `e1/make_selection_set.py` | a294ec3 | 5,474 | `5cfb8283f9d44ea866451e68618a4bf8bbde9462f6dc9c8e62339dc465467b05` |  |
| `e1/t22_gpu_test.py` | 1a753d7 | 5,999 | `d7b293fc91981b29a9746666b3edcbfd5bb48ad93fc35c7efb1d41d4f6f54fe9` |  |
| `e1/t23_api_identity.py` | 1a753d7 | 3,797 | `2571c66193e9b0281ca4c74b466eb9f57585a6a743307591a554848f4f1017f2` |  |
| `explore/run_cell_long.py` | 6e7dea5 | 2,505 | `634a72f3efcc83aa27da08165d7f2a59eec5578dda864d303a5a9c019230cebb` |  |
| `explore/sweep_eval_long.py` | 6e7dea5 | 22,441 | `203d6ebf704b3fba245eed429c09d7b7db818b86999c670cd3a26dc8559629bb` |  |
| `real/calib_report.py` | 56462ae | 3,617 | `00e2fdbeacc908ef70e04497159282fcb6df4131eb6a8545858c467e38d97667` |  |
| `real/calibrate_arm.sh` | b4e8d84 | 2,012 | `0bc1d112e48bf676d5da510d6495a82993101634cde4449dc37fa542faa6a0a9` |  |
| `real/gripper_check.py` | f4fddbc | 4,047 | `2f90cc05d8564eeb179e761699794111f82f95bcd21e69774141af5d62f89ff0` |  |
| `real/hold_home.py` | 468f945 | 2,146 | `614bb55d9447770256e0db3beef64b41646dc3a80b9843694822a79086a561c0` |  |
| `real/hold_home.sh` | 468f945 | 672 | `2acd55a71e47f09d5a8a505c59606934fcf08d1691b3ebcb40b4b41cd8f1a136` |  |
| `real/kcheck.sh` | a700d9a | 799 | `435ba23f3b86e098c4af9d0ef40de55d20561ad6e3153b40d38dbf22f5775c39` |  |
| `real/mock_policy_server.py` | 56462ae | 1,791 | `c797d559b62026ed63091cb856869d831d3567c87649981ac1ac9c8f045de3b7` |  |
| `real/pilot.py` | b4e8d84 | 12,178 | `96b1c9c0fdedbded739e9c2251c719b9a5401d3eb0c5570e85b3880b480513dd` |  |
| `real/pose_check.py` | 1a753d7 | 6,192 | `762f199210fce7fbc1cc43a4300d80b6874117289c5ac9b3c161f39345701849` |  |
| `real/robot_health.py` | 56462ae | 5,405 | `a612f6b36b17390313f81ed878c97197961e2ca552764e5c85f35c5c6d825e96` |  |
| `real/run_real.sh` | 56462ae | 1,575 | `37c062ed2270d359cc57bfb0eb87af76be31e71da400f2dc7492e9806606d4d8` |  |
| `real/run_teleop.sh` | 56462ae | 1,380 | `a84e1cedbf779af7533868cc8d3feb17ec6e9241d6ada9b3a9c876d7d83e2894` |  |
| `real/start_pose.sh` | b4e8d84 | 1,024 | `8b402083bc14d913b677469f1750ecc17a402a6cee6ad5928fb227db09f9954f` |  |
| `real/teleop.sh` | b4e8d84 | 1,023 | `792fb15d9c0038c3ec35764e9960507a20ceaa4873d167b06b395cc86727b1a4` |  |
| `real/trial_runner.py` | d1f86f6 | 67,440 | `18aa8af2a3cced692ad91e0a5610ba9b324fd17454a76ba7f2c93bbb6fed8301` |  |
| `real/vial_check.py` | 59ccb6e | 17,793 | `0d9bee8c3951feebc9d5ba5dd5564c85186ff04ad5f95fcd0577a02d03dbeaca` |  |
| `real/xcheck_first_chunk.py` | e0fd505 | 5,889 | `56e5896d45c39255c3f1376901043bfef9b4e3fa20b8d4effc8176b52a6dbdd3` |  |
| `sim/analyze_c1.py` | 1a753d7 | 13,311 | `cac374d6ec9588f6d736b43b989e772f13f86d203a4c7f7ff729c485c2a54d87` |  |
| `sim/app_smoke.py` | 6b30cc4 | 485 | `1fc64b97f8a6ffd23dfc86c54f7b1819f0d16ba3daa28ecbf094a46fd64f4fee` |  |
| `sim/dump_scene.py` | be85ea4 | 21,525 | `4d3e463e876cf4e707a454ddd1c596c4b36a47b628ace748c5364508d131cf29` |  |
| `sim/gpu_log.sh` | b3f354c | 789 | `6f2da3765c61a6eb80712d4796ee0b597c0b41ab69fba036d20c17d07b2f74a9` |  |
| `sim/image_matched_pose.py` | 1a753d7 | 31,386 | `949a7f584a395016617e1644305357d7812ced9945712970857fc30e6d11bd00` |  |
| `sim/jaw_tips.py` | 1a753d7 | 10,095 | `bc5afe0f1c777ce2ba0bfce5a5bdac1ba1ebd66556b927006074e22db00610b2` |  |
| `sim/layouts.py` | bd8cbaf | 7,295 | `30ea7b688ae297ad9243bf0fc6d2e883f0717b3869a0eaeb34756b1341de05ca` | replaces the prereg-v1 version |
| `sim/local_assets.py` | be85ea4 | 1,521 | `cba717f1ae293083956d18275db1114a9ff459f1ffabd7ea1e2f8f44c940d44c` | already here, unchanged |
| `sim/make_h4_cells.py` | 58ffd9f | 7,121 | `3dbaa9e96421e507528f6638f0120238974d6758dae5d782f032e242684bcb1e` |  |
| `sim/make_s1_cell.py` | 44f1b81 | 4,120 | `337bfc57baa42632fe380577798d956ce5f9a3ee8c25c1fcfd1a87c64fb22cd8` |  |
| `sim/overrides.py` | be85ea4 | 4,207 | `45fe28bcd0de7170ec39d0e589acf908b80ceb33fb5217ca3be8345c8bb19ad9` | already here, unchanged |
| `sim/pilot_report.py` | eab4b75 | 4,561 | `154f5bf0d8d7a4ebacaf10be4c4f0c8151e6c079996bba3ad41a65917eca3253` |  |
| `sim/provenance.py` | 63f724d | 3,033 | `82654c080c1e3ea156ecc4f468ed5ac5faed3ffbb077d02656bd468d4b9d8497` |  |
| `sim/render_poses.py` | 1a753d7 | 6,424 | `4880738ffddd5441d6a01a20d53055a524ee3315cc844f5df2be5a06de58cdda` |  |
| `sim/run_queue.py` | a0b0db3 | 15,440 | `add0a012ca5301e1c89f7dd041b26f67eaabbc3603b00dbb43f466cc17dac144` | replaces the prereg-v1 version |
| `sim/run_server.sh` | 63f724d | 1,844 | `871210880a43677a0855dd733f5139595dc83efc61bd5b1f720d29a01eeb9839` | replaces the prereg-v1 version |
| `sim/run_sim.sh` | 63f724d | 3,547 | `63a3524e5bf4e8384b3833e05855ad9a763999274fb59908d891c6414ca0dfb2` | replaces the prereg-v1 version |
| `sim/run_t03.sh` | 1a753d7 | 2,744 | `64f10ddbdb6fbaebec115dca614c0db46800bcd353be70140933055fbfac6b0d` |  |
| `sim/server_ping.py` | b3f354c | 3,031 | `2c7168d444b143723c9e004d3cbc544552f46fd80697893ec97946a298b9704b` | already here, unchanged |
| `sim/sign_table.py` | 32d3055 | 9,896 | `22d0f7d223e14956ec82932d5da630250277a55dc2f31c87ae3d7a98644a9005` | already here, unchanged |
| `sim/stamp.py` | b3f354c | 657 | `a8e661bc73633220dd58af2beea2428ec9b8d60745e68d926adc2e325b856a5c` | already here, unchanged |
| `sim/summarize_t03.py` | b915482 | 4,819 | `720d04c34e0483d40c048a4fabd7fa775dbbcec06c2370c438818ced83bb6e92` |  |
| `sim/sweep_eval.py` | 63f724d | 21,581 | `1632205371558107758b18569c90fac3bb692a746294442494a6e5eb4d6a59e5` | replaces the prereg-v1 version |
| `sim/trace_episode.py` | 1a753d7 | 12,180 | `0cc2ba3be448bb595d6cfe06c4120109018e992fd852c8c0abeb8e63cc209268` |  |
| `stencils/stencils_letter_both_sets.pdf` | d46e985 | 172,461 | `d49a6e5b43d230bc068531961086971d95cba86c8b869317c028ac381687af3f` |  |
| `stencils/stencils_letter_setA.pdf` | d46e985 | 86,782 | `a4f7377170908021507ce7c40c1608689ff1ed50c7b5c7ba7e07da05baa2b897` |  |
| `stencils/stencils_letter_setB.pdf` | d46e985 | 86,788 | `ac4257e8055d22d1e18135494fad38ad6d18feaed0b2b85a29bd3c9fbac24052` |  |
| `stencils/stencils_report.json` | d46e985 | 6,193 | `b8325cfb4d9b2bfb3503959665831aa4b0770c792e88dd8ba5715d089949368c` |  |
| `stencils/stencils_tabloid_both_sets.pdf` | d46e985 | 167,616 | `6352e3c4efedf28127a7e4757cf42f2de9c027859e8bdf1c9269870dee6cc157` |  |
| `stencils/stencils_tabloid_setA.pdf` | d46e985 | 84,368 | `74e21094f9e1186f3915bf3ee7f565a856be1cde48bc6cd227da12a4222f673a` |  |
| `stencils/stencils_tabloid_setB.pdf` | d46e985 | 84,357 | `800e040798445052619d913a2c78a1eff3859972fd9f6b4915e83af0da18b8be` |  |
| `tests/fake_cell.sh` | 469435b | 1,059 | `dd3b91c2270d297eefa9a03aa812166a3b75e702ad533dee05eb6575ceb575e7` |  |
| `tests/make_r0_board_frames.py` | 7ee365b | 1,366 | `34eb92c26bc8fcf78a4244eed8d1ac688e4102481a395678fb2732cea177d294` |  |
| `tests/make_synthetic_calib.py` | 7ee365b | 3,970 | `0ccea42d60cf744481620d9030c222f6b50840eaed75751db11df4f68788fe9a` |  |
| `tests/run_monday_dryrun.sh` | b4e8d84 | 4,855 | `7742f2fe098d5fac47f905c7da4d0ff252afcf57de473ab4aff01a6faca5cf45` |  |
| `tests/run_trial_dryrun.sh` | 9a67cb5 | 7,246 | `8404310b8b959248922dc3b9325e66b53356032c764cac56c7058a23b87d8dab` |  |
| `tests/test_aim_view.py` | bceabbb | 3,574 | `3b9a9b07f2e1d05105be1e22f3ba7508a01e9b3fae22b38bb11dceaae59ce95a` |  |
| `tests/test_analysis.py` | 9deff18 | 10,853 | `16a91eb1fab0afdad38c988501a39a234df2600e4c1f10aa2d0fe9318f72089d` |  |
| `tests/test_analysis_scipy.py` | 9deff18 | 4,334 | `adda5a2549c6eaa94b22f7df49ab561b60499ba4b47a7364e68ea5049c4a5f4f` |  |
| `tests/test_drift_synthetic.py` | 1a753d7 | 2,865 | `aef53090c715a8180f57c5c857c24a88e7bf576e531beac44e36b39126d39fee` |  |
| `tests/test_h4_prep.py` | 1a753d7 | 7,848 | `32f4c664cb0e357cfb13366a8a93d0801ba7b9aeac65926ae618b4bd1c15e3aa` |  |
| `tests/test_light_log.py` | b4e8d84 | 2,191 | `da8f34323d70cc544c0c73497f7c28dc22a2aebc3b3acb7c6ff66b2fe4cc4907` |  |
| `tests/test_monday_units.py` | 1a753d7 | 11,175 | `5ade141259c389a2014d88bd294af741813210b2b78dfb5b2ec0bee3802e5901` |  |
| `tests/test_overlay_synthetic.py` | 7ee365b | 4,031 | `bbb769c97cfdd6608d3ba929e40905d7463dc899ef6e89ebf674e3ff7451952f` |  |
| `tests/test_pose_hud.py` | 1a753d7 | 12,803 | `bb89ec90486ac5960b6c86c4ea44db6f56d003ee08166b27807c69d78464c187` |  |
| `tests/test_pose_synthetic.py` | 7ee365b | 3,994 | `2d2b9a6e5a5646055482c4b838765ddb56bedb2ce59f9442606dc5d3c8186b5d` |  |
| `tests/test_still_check.py` | bec5949 | 3,432 | `6296f7a1b5fd47164c900c173f9235055aac8c607a3fb83d9dbff1d7fbcfaacb` |  |
| `tests/test_trial_runner.py` | 1a753d7 | 25,769 | `d924df58dafd3dc6e21aa7a9ff4cec803619cd084270ecf9d7c222e5b8ec756e` |  |
| `tests/test_v4l2_abi.py` | 1a753d7 | 3,541 | `5bf78604c4902c92586c2de8aa25c6972ae52388b276fb01d509ac96cdac2083` |  |
| `tools/arm_fk.py` | 7b5a800 | 4,820 | `20fa399c22dade331e93565c5d6883c6b74eff28749b470a76e265c7315cc856` |  |
| `tools/base_shift_frames.py` | 1a753d7 | 20,584 | `26aa496f1d5f3e7be05e90a64d30c5d84ca73246b27164b2ba5de887721c3137` |  |
| `tools/base_topview.py` | bff1054 | 9,229 | `2fcddae628fe0b40635a68d70261f0f55014497f895311647cf4cf1e42373b37` |  |
| `tools/blind_rename.py` | 459293f | 4,389 | `695558b95a90701789f49179af8b2b85a45907919e8750a27f1fbd94d4849a82` |  |
| `tools/capture_versions.py` | 1a753d7 | 6,134 | `6469123de7f3a1be4aabfdad2fab0aac0fb16e4ef6e432fff1558519ffa490f6` |  |
| `tools/contact_sheet_explore_v1.py` | 1a753d7 | 6,236 | `f46275ef671f5f782bfc26a9ed585d0633a38752f8e8fd9cea6fa5bdd95db9f4` |  |
| `tools/contact_sheet_explore_v2.py` | 1a753d7 | 5,483 | `fde01a891e833f18524b22422f61e6b8ed28d62b50e9c6cbaeb588afde87c2bf` |  |
| `tools/cut_judge_clips.py` | f36014b | 9,725 | `b7ee9671da1104a74552edad9e723d64dcc701fff8134afabca68733697971df` |  |
| `tools/cycle.py` | 1a753d7 | 9,998 | `4e0d3a06100424cd4951bc15f6214943e9ddf3819e37959479c80e3f3f80bbc7` |  |
| `tools/explore_v1_report.py` | 966e83f | 5,551 | `446e15bc7fe0b722c0f04a3943373b18b3e3c4b9967898f92c163624f4e23a8e` |  |
| `tools/explore_v3_report.py` | 1a753d7 | 6,101 | `a7215237d666a82809110476b93e5efb0ccc19423d014890d9082a6c2cc3cf83` |  |
| `tools/framing_check.py` | 1a753d7 | 4,523 | `d73b8498c2624619093bf9e1c7c5f920194fe79e519c2f81cdd366896c37bcd8` |  |
| `tools/ignore_zone_check.py` | ab631ce | 9,241 | `4dd1a1262ce594fc721f1f928843e6806747dfe7fd47716bc76c0915c426a300` |  |
| `tools/jig_fit.py` | 426d18a | 11,443 | `275bcacb15c13b8c97c423b3da43c65cc569169cda57c9490959d987f2865884` |  |
| `tools/make_local_wrappers.py` | 1a753d7 | 4,145 | `a2d5803b09ddb1a7f1e64f8c6f89a1ef67cfc148461233b295000864a243b8b3` | replaces the prereg-v1 version |
| `tools/make_stencils.py` | 1a753d7 | 15,732 | `eb32abe40b20c3f1498d7fe828d3168e062cfbe3cdef3c38ebaf3ab21a2cf747` |  |
| `tools/map_sweep_cells.py` | 1a753d7 | 5,723 | `fef5d004d4cc6d3d85dcf9f6d9e7f117e3695ae2522491e50eb6a623e5aabde8` | replaces the prereg-v1 version |
| `tools/mirror_remote_assets.py` | be85ea4 | 5,644 | `6a812701cff304b40389c42cbf9f03bb35f9de160eaa9bbfea526323df2ff56a` | already here, unchanged |
| `tools/posecheck_compare.py` | 2e4495a | 6,927 | `55ecf81abd2aecf75f53b624d9e10b958dc67ec59b464e898dc64dc5628cdfee` |  |
| `tools/r0_pose.py` | 1a753d7 | 10,350 | `1b996d57bb9879c974c981e317ee57209d6c6141b2677f10bbadf96583270eff` |  |
| `tools/rebase_poses.py` | 34c8a77 | 3,518 | `a925d0aa5b7b72fe2c888a627f4ccded012541c6ddbbf98dc5c0e05ef08a977a` |  |
| `tools/recover_trial_record.py` | 1a753d7 | 11,789 | `5633ac4adf8c67dc3085b0f6929f5a13689f32ae0f15931efcb98d39dfcc5ac0` |  |
| `tools/scene_check.py` | 1a753d7 | 12,759 | `2635f1d46eb25df0350bde2a4c546ec6469a713a6456909a663584f9d6a6bacc` |  |
| `tools/sled_from_views.py` | 34c8a77 | 19,321 | `8798fb001498d6020500708ce72f8a4afdd05cb6b44287b62feb9c7d71a51e91` |  |
| `tools/tilt_failure_modes.py` | 28be591 | 4,462 | `b5284d13eddc5e50274e5e16896720897b9680ddce8cfc707156673e035242b9` |  |
| `tools/vial_check_validate.py` | 1a753d7 | 8,061 | `3166537a29541f61f5f30acc737240efefef17294d1099d168d36106df61cee6` |  |

## E3 code (`e3/`, frozen commit `399025f`)

15 files, 146,835 bytes, from the private E3 repository at the frozen commit
`399025f998ea0114dd00c21f45e7ec937ed12589` (archive SHA-256 `17fed03e9c82f4c9b05a70da541e23c3e0c4d536c1773de0857fa08395312291`, addendum entry 3);
each file's commit is the e3 commit that last changed it. The SHA-256 and size are those of the file at the frozen
commit. `e3/README.md` was edited for this copy (below); the other files are byte-identical to the frozen commit.
Because of that edit, the archive's SHA-256 cannot be recomputed from these files alone. `e3/README.md` was written on November 8, before the freeze; its status lines were updated for this copy. `results/e3/simset_e3.json` records `version_hash` `d826f4e7...`, the hash of the E3 code just before the freeze: the frozen commit only added 15 lines to `validate_real.py`. `e3/cache/scene.npz` is derived from the course's USD files (see
NOTICE).

| File | e3 commit | Bytes | SHA-256 (e3) | Note |
|---|---|---:|---|---|
| `e3/.gitignore` | 60808ca | 19 | `862263fa1f46c20f0d1e4dac5ffcc75abd55c08211b2c3864c5f8764b9d87793` |  |
| `e3/README.md` | 578f043 | 4,371 | `6fe4dfbc10b63ddbe3412824a022790027619e6ea626b20c8a55d24b3ca3108f` | edited (below) |
| `e3/bench.py` | ebe3d11 | 2,791 | `e351dacf8f4d6678b940dfe553231aee01a09e204fa2b962e638a8ac42ebd44a` |  |
| `e3/bench_render.json` | ebe3d11 | 624 | `f883a906c29200c268bdc99eea5f86cab6879f815b36700b057ea3706021d16d` |  |
| `e3/cache/scene.npz` | ebe3d11 | 57,431 | `d94500dddfd3f72d98be96f9d6b4f24f7a72879e50b47145f3ff17bd73b8e316` |  |
| `e3/estimate.py` | ebe3d11 | 16,821 | `999a7a090e9c7a178856fd9b920eafabcb0bb80574843fc6432e159861365d7b` |  |
| `e3/eval_simset.py` | fc8b5fb | 3,385 | `1edc6c7a36706e6e9ee828dfb7f0b86f05f5891ecfe1acb20874b774c1192e6f` |  |
| `e3/render.py` | ebe3d11 | 17,958 | `d4bb39a407ff7cf013ed13973db28991c4678fc735c068d526811897f7990e6d` |  |
| `e3/render_gpu.py` | ebe3d11 | 6,791 | `4a6fc7fb0948034f08f07a387ccf7c8e0a1cd2e2b4f135fa2351bf0527ec4549` |  |
| `e3/segment.py` | fc8b5fb | 5,228 | `02102894ee0b13456635ea8c3c0ca36be31d965a743c7dcaad812ac8760dff5d` |  |
| `e3/smoke_tiled.py` | 60808ca | 10,740 | `ec5ae923d56cefd28cfbb07e0846b7403035ff3c9d6f0dc694e2d9b9cf2969f1` |  |
| `e3/validate.py` | 6eea643 | 3,326 | `d070bb55321bb24b2aafc2d0582c528e0590bd1f475e3a888f61ee364d6860be` |  |
| `e3/validate_real.py` | 399025f | 6,470 | `261f92d1d9e3afd8c7c21225c3c43f09e4bd30421b693b9c109cff9ab887a42b` |  |
| `e3/validation_synthetic.json` | d682878 | 5,437 | `e7a8e1dd1f7b86affb9a664f900b43b5e4ff1e689e003f57725b8dbc1925ac64` |  |
| `e3/validation_synthetic_cem.json` | 6eea643 | 5,443 | `743ec4cd1269813cca4973777cb878bf84861665a44a7f6478e261a738933365` | already here, unchanged |

## Edited for this copy

| File | SHA-256 of the source | SHA-256 here | Change |
|---|---|---|---|
| `config/board_in_E.json` | `efc6c3cc3c11175b97d1f148170b377be475bc0f176bbbf7bfa5b3956da16f83` | `9e2b77712966ba955ea2833b91ca30ec0397ce041c7498104a63f90a0d6aa13f` | names and times removed from four explanatory text fields; every measured value unchanged |
| `config/prereg.json` | `bacdd1625b2d34d6f44a2942de2a5a456201a83dc6f6a2d10376767bb4706b5a` | `a23ad213309506773a77bdd5879684a558415958787f11b56463d8639a608358` | the superseded commit hash of the prereg-v1 tag removed (the tag points to `015789a`) |
| `config/r0_pose.json` | `ef6768342fdd8805ab9390d43b1d587baed70540b125f4b7e325ada3ed81c497` | `e760ccf3a80c743c8edde394bdc7d3204210d52917c5171f9d0e7475aad0fc88` | `definition` names the protocol label instead of a private file path |
| `config/versions.json` | `3c9d7303bb831b54d9e223318725276653504b787b3c1423beaafeb8f34694e6` | `8f99ba44978a53dc17de8a96f2b9099bdc940c6c8e8fb9f71e69c4107042dfa8` | a line about software not used by the project, the driver-switch detail beyond the two driver versions and the reason, two superseded hashes of the October history fix and 8 words of its `reason` text, approval wording, and private staging paths removed; the model's local path written with `~` |
| `e3/README.md` | `6fe4dfbc10b63ddbe3412824a022790027619e6ea626b20c8a55d24b3ca3108f` | `461a7e26a8e67f91cb209d5917fa14c4897a45e735d2fb88759438ac9218db18` | the title's note on the local repository, the November 8 status and the plan to freeze replaced by the freeze record; a reference to a private project file removed |

## Inputs the code reads (`results/c1/`, `results/overlay_refs/`, `results/real/`)

13 files, 534,522 bytes, from gtc at the same paths, byte-identical: the simulation renders, masks and
scene dump that the camera tools, E3, the tests and the trial runner's dry run read, and the list of trials judged from
robot frames that the blind-score analysis reads. `results/c1/nominal_front_rgb.png` is listed above.

| File | gtc commit | Bytes | SHA-256 | What |
|---|---|---:|---|---|
| `results/c1/frames_sim.json` | b915482 | 90,102 | `9ffc7656d47805ff99dd0b3fc0f70b54e52b5d2c60e3bddc3252da5ebf38a02c` | the C1 scene dump: object, robot and camera poses and the camera intrinsics, every randomization at its centre (sim/dump_scene.py) |
| `results/c1/c1_checks.json` | b915482 | 7,806 | `7b14b1ab7e6b05f1e1a31d6d5a9822b2b36de53fa939d47e4d193b62c90d77e0` | the C1 checks: expected values, colour patches and the straight-edge check (sim/analyze_c1.py); calib/light_log.py reads its floor patch |
| `results/c1/nominal_front_instance_ids.png` | b915482 | 8,745 | `951c1f2cabd8675e37c877737725aacc8c601e170fc5057f71843a3d09e6b415` | instance ids of the nominal front render |
| `results/c1/nominal_front_instance_labels.json` | b915482 | 9,895 | `7aaa7e8b9b9ddcca45b7ea3ee2dfe35a1006a86ada69301365d0317449a06ba1` | instance labels of the nominal front render |
| `results/c1/nominal_front_instance_rgba.png` | b915482 | 11,269 | `f54a0b8eb8cbc9d77d5a6077f79718c2275af135b2d0ba5c7ddc98180fdc2d7d` | instance colours of the nominal front render |
| `results/c1/nominal_wrist_rgb.png` | b915482 | 163,775 | `ca6c6c58b6c007738445e2dd26050b9d6bf2df8ffff9c1c4e82893f941b764fb` | the nominal wrist-camera render |
| `results/c1/nominal_wrist_instance_ids.png` | b915482 | 4,562 | `0c8f2c4155714e477df915225fae612f1f290ff8f4e3d22957f8db37edfec99f` | instance ids of the nominal wrist render |
| `results/c1/nominal_wrist_instance_labels.json` | b915482 | 5,906 | `093fb17a81232b6fd3f6eedbb4bc4f8c6810049eef46f17096070e36e5bb0788` | instance labels of the nominal wrist render |
| `results/c1/nominal_wrist_instance_rgba.png` | b915482 | 5,511 | `7061754d89a63aa66ce8ac70ba3e298e8cca5ee007385bf764bbb4c945c9fc37` | instance colours of the nominal wrist render |
| `results/overlay_refs/sim_r0_front_rgb.png` | 6c3069c | 209,206 | `6aa58bf0d719ffaa934c13d1d4e8aa7d8e810b7fd2d7665fa093d7e94b248488` | the front render at the R0 camera pose (calib/overlay.py --ref sim_r0) |
| `results/overlay_refs/sim_r0_front_instance_labels.json` | 6c3069c | 4,401 | `740f765834b9356abbde3ab192cc2dd28f9e1e0f8054ca3c4e029f1d2552a5b0` | its instance labels |
| `results/overlay_refs/sim_r0_front_instance_rgba.png` | 6c3069c | 10,148 | `61de711def5e2ca43c04ad2413bb23d2c2e31c397925155dc3036858b4c5038c` | its instance colours |
| `results/real/judge_clips_robot_frames.json` | 459293f | 3,196 | `358a6afa9b82ae307b7b627d2d366677d02a475899bdcc17a9d9370326ee107f` | the trials without a phone recording, whose judge clip is the runner's front keyframe video (read by analysis/blind_results.py) |

## ChArUco board (`docs/`)

2 files, 795,833 bytes, from the study's protocol sources (`docs/` beside gtc, not a git repository),
byte-identical. The PDF's metadata was checked: made by the Pillow PDF driver, with a title
(`ChArUco_GTC_SO101_letter`) and creation and modification dates only; no author, no XMP metadata; its one image is a
JPEG with a JFIF header only (no EXIF, no comment). Nothing personal was found, so nothing was stripped.

| File | Bytes | SHA-256 | What |
|---|---:|---|---|
| `docs/charuco_board.json` | 159 | `07a887cc4401fc2de899f5d808945e1f0f96c6ad7b3aca17e443ad00b3083f70` | the board definition that calib/charuco.py reads |
| `docs/ChArUco_GTC_SO101_letter.pdf` | 795,674 | `d25d5604da35890b0c1fe1b7aa40ff1ad055242ffa549c4c735651cb34ce3bb7` | the board to print, US Letter landscape at 100 % |

## Package lists (`requirements.txt`, `requirements-e1.txt`)

New files, not copies: the installed packages of the study's two host environments, read on November 10, 2026 with
`importlib.metadata`, one `name==version` per line.

| File | Bytes | SHA-256 | What |
|---|---:|---|---|
| `requirements.txt` | 220 | `0a68668067206804eecd2a4738093a84f4d1934c104a972e0e0952d02fb4bb9e` | the host environment (`.venv`) |
| `requirements-e1.txt` | 1,092 | `eb53321f3fb30c7e950835d9179f8ad5cd57da360f356710bd5f809361c157d7` | the E1 environment (`.venv-e1`), with the PyTorch cu128 index line |

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
  two keys (table above). An `e3/` source is the private E3 repository; its files are copied here under `e3/`.
- **Edits to trial records.** Changes made after a record was written are logged in the record itself (`relabel`,
  `flag_edits`, `note_edits`, `record_recovery`), with the time, the reason and any earlier value. The trial-level
  deviations are in deviations.md.
- **Not copied:** everything else in gtc, including the phone recordings, judge clips and trial frames (the trial frames
  include the photos of the real room); the clip-cutting logs (their video metadata includes the phone's location);
  the audit copies of trials.jsonl made before each edit; the run logs, working notes, machine setup scripts, queue
  state and release staging copies; and gtc's own README and .gitignore. From `results/c1/`: the depth array and the
  check image, which the code does not read.
