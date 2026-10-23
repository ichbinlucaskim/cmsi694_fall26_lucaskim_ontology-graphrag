# Baseline, study50 (SCRUM-32)

The schema-free baseline condition on the frozen study50 subset: 50 questions
(13 inference, 13 compositional, 12 comparison, 12 bridge_comparison) and
their 427 context paragraphs, indexed into one graph. This is the control half
of the study's main result.

The run manifest is copied unchanged to
`docs/results/baseline-study50-manifest.json`; it contains no paragraph text.
Scores are in `docs/results/baseline-study50-scores.md`, written by
`scripts/score.py`. Per-question outputs are in
`runs/baseline/study50/results.jsonl` and `scores.json`, which are git-ignored.

Commands:

```
python scripts/freeze_subset.py --check
python scripts/run_condition.py index --condition baseline --subset study50
python scripts/run_condition.py query --condition baseline --subset study50 --no-llm-cache
python scripts/score.py --condition baseline --subset study50
```

## Provenance

| Item | Value |
|---|---|
| Condition | `baseline` (`configs/conditions/baseline.json`, sha256 `22f151c2a0766d27cc0297b53d1831ce72f58181086413178579bfecfcd2453c`) |
| Models | `qwen2.5:7b-instruct` (`845dbda0ea48…`), `bge-m3:latest` (`7907646426…`); digests in the manifest |
| Software | LightRAG 1.5.7, Ollama 0.34.3 |
| Seed | 694 (index and query) |
| `configs/run_config.json` sha256 | `0462fab880d215c56e98f07db049581f380b4add5a8919ec9ed5b965b4cf1a5a`, for both index sessions and the query; the same as the smoke10 baseline's SCRUM-30 query |
| Index settings sha256 | `e2a4c0dcb9777fb8ee037d86c148249adb7cf871da56f46da6c355c55858e7d2`, the same as smoke10 |
| Index commit | `2b358d29a32a56da2cca547ee5a4ddafbde28576` (clean), both sessions |
| Query commit | `fca12d581c4fee54c9857432f908855b2ba262de`, recorded as dirty |
| Query LLM cache | off (`--no-llm-cache`) |
| Results sha256 | `2b01ce8b86f782368f5ee95487ca7223612dce76613cfdfc5040435f8248c02c` |

The query record's `dirty: true` comes from one untracked file, a note
holding the run command, created a minute before the query started. No
tracked file differed from `fca12d5`. The scorer's "dirty" mark has the same
cause.

The smoke10 baseline index was built with config `a14572f9…`; its config
changed afterwards only in the `query` section (answer instruction, then the
SCRUM-30 answer template). Those changes do not affect the index, so the index
settings hash is the same for smoke10 and study50, and study50 used the
current config for both phases.

## Scores

Percentages, with bootstrap 95% intervals (1,000 resamples over questions,
seed 694). EM and F1 compare with the gold answer only; the alias columns also
accept the answer entity's aliases and demonyms, as the official
2WikiMultiHopQA v1.1 script does.

| Group | n | EM | EM (aliases) | F1 | F1 (aliases) | Retrieval recall |
|---|---|---|---|---|---|---|
| overall | 50 | 36.0 [24.0, 48.0] | 42.0 [30.0, 56.0] | 47.8 [35.6, 59.9] | 51.2 [38.3, 63.9] | 94.5 [90.5, 98.0] |
| inference | 13 | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 23.3 [6.8, 39.5] | 23.7 [6.8, 40.5] | 100.0 [100.0, 100.0] |
| compositional | 13 | 15.4 [0.0, 38.5] | 38.5 [15.4, 69.2] | 32.3 [11.8, 55.6] | 45.1 [21.0, 71.0] | 100.0 [100.0, 100.0] |
| comparison | 12 | 66.7 [41.7, 91.7] | 66.7 [41.7, 91.7] | 66.7 [41.7, 91.7] | 66.7 [41.7, 91.7] | 100.0 [100.0, 100.0] |
| bridge_comparison | 12 | 66.7 [41.7, 91.7] | 66.7 [41.7, 91.7] | 72.2 [47.2, 91.7] | 72.2 [47.2, 91.7] | 77.1 [66.7, 87.5] |

All 50 queries succeeded. All 50 raw answers are a single line, and the
answer-normalization fallback changed 0 rows, so `predicted_answer` equals
`predicted_answer_raw` for every row.

## Retrieval

Every question retrieved 20 paragraphs, out of 427 in the index (4.7%). On
smoke10 the same 20 were out of 100, so recall there said little; here a
question's own 10 context paragraphs are 2.3% of the index.

| Measure | Value |
|---|---|
| Paragraphs retrieved per question | 20 of 427, for all 50 questions |
| Mean retrieved paragraphs that are among the question's own 10 context paragraphs | 5.5 |
| Questions with every gold paragraph retrieved | 42 of 50 |
| Distinct paragraphs retrieved over all 50 questions | 312 of 427 |

All 8 questions with a gold paragraph missing are bridge_comparison questions,
which have 4 gold paragraphs each; every other type has 2.

## Timing and tokens

Indexing ran in two sessions. The first was interrupted after processing 149
paragraphs; the manifest records its start and end times but, as the
interrupted record was written then, no indexing wall-clock or token counts.
`scripts/run_condition.py` now records token counts for an interrupted index
session too. The second session processed the remaining 278.

| Phase | Wall-clock | Per unit | LLM tokens (prompt + completion) | LLM calls | Embedding tokens |
|---|---|---|---|---|---|
| Index session 1 (interrupted, 149 paragraphs) | 8,187 s, from start and end timestamps | 54.9 s per paragraph | not recorded | not recorded | not recorded |
| Index session 2 (278 paragraphs) | 16,685.1 s | 60.0 s per paragraph | 525,646 + 157,887 = 683,533 | 278 | 126,785 (859 calls) |
| Index, both sessions (427 paragraphs) | 24,872 s (6.9 h) | **58.2 s per paragraph** | | | |
| Query (50 questions, cache off) | 11,486.2 s (3.2 h) | mean 229.7 s, median 232.7 s, max 365.4 s per question | 744,610 + 1,954 = 746,564 | 100 | 1,891 (50 calls) |

Session 1's figure also includes model warm-up (7.2 s) and storage start-up. Index result: 427 of 427 processed, 0 failed, none failed on the
first pass, one chunk per paragraph. The index projection in SCRUM-32 was
about 6 h at 51.6 to 53.8 s per paragraph; the measured rate is 58.2.

The slowest question was `c7134f820bdd11eba7f7acde48001122` (365.4 s). Query
time is dominated by prompt processing: about 7,446 prompt tokens per LLM
call, against about 5,972 on the smoke10 SCRUM-30 re-run (158.9 s per
question), because the context is assembled from a larger graph.

## Consistency with smoke10

The first 10 study50 questions are the smoke10 questions. Their answers are
compared below with the smoke10 SCRUM-30 re-run (same config, cache off, same
seed). This is informational: the study50 index has 427 paragraphs instead of
100, so retrieval and therefore answers can change. "Shared retrieved" counts
the paragraph IDs the two runs both retrieved, of 20.

| # | Question ID | smoke10 (SCRUM-30) | study50 | Same answer | Shared retrieved |
|---|---|---|---|---|---|
| 1 | `c8c5f3ee0baf11ebab90acde48001122` | Alexandra of Lithuania | unknown | no | 10 |
| 2 | `d4ae7b5e0bdc11eba7f7acde48001122` | unknown | unknown | yes | 7 |
| 3 | `549d1a63086a11ebbd5fac1f6bf848b6` | no | no | yes | 15 |
| 4 | `90c8793c087411ebbd67ac1f6bf848b6` | unknown | Return to Cabin by the Lake | no | 6 |
| 5 | `36a3fe2a0baf11ebab90acde48001122` | Ulick Burke, 3rd Earl of Clanricarde | Ulick Burke, 3rd Earl of Clanricarde | yes | 13 |
| 6 | `e61479860bda11eba7f7acde48001122` | Kingston | Kingston | yes | 14 |
| 7 | `787f51ac097311ebbdb0ac1f6bf848b6` | Find A Place To Die | Find a Place to Die | no (case only) | 9 |
| 8 | `e82674bd089311ebbd75ac1f6bf848b6` | Los Hijos de Fierro | Los Hijos de Fierro | yes | 9 |
| 9 | `48137be00baf11ebab90acde48001122` | unknown | unknown | yes | 8 |
| 10 | `62e8b66a0bdc11eba7f7acde48001122` | New York | New York, New York | no | 5 |

4 of 10 answers differ. Scored with official EM and aliases, question 4 went
from wrong to right; questions 1, 7, and 10 keep their outcome (1 wrong both
times, 7 and 10 right both times; 10 loses plain EM but keeps EM with
aliases). Overall EM with aliases on these 10 is 4 of 10, against 3 of 10 on
smoke10.

## Limitations

- **One run.** The index and the query ran once, with seed 694. Run-to-run
  variation is measured in SCRUM-22.
- **n = 50.** The intervals are wide: overall EM with aliases is
  42.0 [30.0, 56.0], and each type has 12 or 13 questions.
- **Session 1 has no token counts** (see Timing and tokens), so the index's
  total token use is not known; session 2's 278 paragraphs averaged 1,891
  prompt and 568 completion tokens per call.
