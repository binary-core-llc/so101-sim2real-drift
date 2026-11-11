# Files copied from the private working repository

The study's working repository (`gtc`) is private, and its history is not published. The files below were copied from
it on November 10, 2026, after the poster was submitted, with gtc at commit `6f835c0`. Each file is byte-identical to the
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

5 files, 32,016 bytes: result files only, and the E1 selection script. The E3 code is not published here
yet. `e3/validation_synthetic_cem.json` comes from the private E3 repository at the frozen commit `399025f` (archive
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
  two keys (table above). An `e3/` source is the private E3 repository; `e3/validation_synthetic_cem.json` is copied here at that path.
- **Edits to trial records.** Changes made after a record was written are logged in the record itself (`relabel`,
  `flag_edits`, `note_edits`, `record_recovery`), with the time, the reason and any earlier value. The trial-level
  deviations are in deviations.md.
- **Not copied:** the phone recordings, judge clips and trial frames (the trial frames include the photos of the real room); the clip-cutting logs (their video metadata
  includes the phone's location); the audit copies of trials.jsonl made
  before each edit; the E3 code and its README (`e3/README.md`).
