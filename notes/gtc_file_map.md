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
  before each edit; the simulation episode files; the E3 code.
