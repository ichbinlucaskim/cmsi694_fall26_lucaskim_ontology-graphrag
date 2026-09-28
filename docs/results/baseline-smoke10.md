# Baseline, smoke10 (SCRUM-16)

End-to-end run of the schema-free baseline condition on the smoke10 subset: 10
questions (3 inference, 3 compositional, 2 comparison, 2 bridge_comparison) and
their 100 context paragraphs. The run proves the pipeline. It is not an
evaluation; the official metrics are defined in SCRUM-19.

The full run manifest is `docs/results/baseline-smoke10-manifest.json`, copied
from `runs/baseline/smoke10/run_manifest.json`. Per-question outputs are in
`runs/baseline/smoke10/results.jsonl`, which is git-ignored.

Commands:

```
python scripts/run_condition.py index --condition baseline --subset smoke10
python scripts/run_condition.py query --condition baseline --subset smoke10
python scripts/run_condition.py renormalize --condition baseline --subset smoke10
```

## Provenance

| Item | Value |
|---|---|
| Condition | `baseline` (`configs/conditions/baseline.json`, sha256 `22f151c2a0766d27cc0297b53d1831ce72f58181086413178579bfecfcd2453c`) |
| Subset manifest | `data/subsets/manifest.json`, sha256 `094198d427cd05be619c023f15dc1be80d7d3b4df98891967aa356181797a30d` |
| Models | `qwen2.5:7b-instruct` (`845dbda0ea48…`), `bge-m3:latest` (`7907646426…`); digests in the manifest |
| Software | LightRAG 1.5.7, Ollama 0.34.3 |
| Seed | 694 (index and query) |

| Phase | Commit (clean) | `configs/run_config.json` sha256 | Index settings sha256 |
|---|---|---|---|
| Index | `7ac0e59cbc011cf2bac03a5c38f932abe54f052e` | `a14572f9fc751039543e36a7880029fe812a1d9ead77def4b3ed12f6ddb54566` | `e2a4c0dcb9777fb8ee037d86c148249adb7cf871da56f46da6c355c55858e7d2` |
| Query | `c7022724d13974ec7f0243e1339c4433ae3b0a21` | `8b69423758b7cce446ccfe2706e331d776e80c1122caee3cabdd32f5f92c6b5e` | `e2a4c0dcb9777fb8ee037d86c148249adb7cf871da56f46da6c355c55858e7d2` |
| Renormalize | `dc58506b369fb57b889843f6a5a17bc72882d044` | not used | not used |

The two config hashes differ because the query's answer instruction
(`query.user_prompt`) was tightened between indexing and querying. That section
does not affect the index, so the index settings hash is the same for both
phases, and the query ran without `--allow-settings-mismatch`.

## Timing and tokens

Token counts are Ollama's own `prompt_eval_count` and `eval_count`, summed over
every call actually sent. LightRAG cache hits send no call and count nothing.
The query ran with the LLM cache enabled, but this was the first query on this
index, so every call went to the model: 20 LLM calls, 2 per question.

| Phase | Wall-clock | Per unit | LLM tokens (prompt + completion) | LLM calls | Embedding tokens |
|---|---|---|---|---|---|
| Index (100 paragraphs) | 5,383.3 s | 53.8 s per paragraph | 189,225 + 50,373 = 239,598 | 100 | 41,444 (304 calls) |
| Query (10 questions) | 1,852.2 s | 185.2 s per question | 122,822 + 432 = 123,254 | 20 | 381 (10 calls) |

Index: 100 of 100 documents processed, none failed, one chunk per paragraph.

## Graph size

| Measure | Value |
|---|---|
| Nodes (entities) | 467 |
| Edges (relations) | 357 |

## Answer format

**The answer template itself is not yet fixed.** LightRAG's `rag_response`
prompt asks for Markdown and a References section. Our instruction in
`query.user_prompt` does not always override it.

In this run, 3 of 10 raw answers carried extra text:

| Row | Raw output | `predicted_answer` |
|---|---|---|
| 1 | `Alexandra of Lithuania. She was the daughter of Algirdas, the Grand Duke of Lithuania` | `Alexandra of Lithuania` |
| 3 | `No`, followed by a `### References` list | `No` |
| 8 | `A Pistol for Ringo`, followed by a `### References` list | `A Pistol for Ringo` |

These three rows rely on the post-processing rule documented in `MODELS.md`
("Answer normalization"):

- `renormalize` re-derived `predicted_answer` from the stored raw outputs,
  without model calls.
- It changed exactly these three rows. The manifest's `renormalize` record
  lists them and the results file's sha256 before and after.
- The raw outputs are kept as `predicted_answer_raw`.

SCRUM-30 (Sprint 2) replaces LightRAG's answer template at the source.

## Per-question results

"Gold retrieved" compares the question's gold paragraph IDs (from
`supporting_facts`) with `retrieved_paragraph_ids`. Every question retrieved
20 of the 100 paragraphs, which is the `chunk_top_k` limit.

| # | Question ID | Type | Predicted answer | Gold answer | Any gold retrieved | All gold retrieved |
|---|---|---|---|---|---|---|
| 1 | `c8c5f3ee0baf11ebab90acde48001122` | inference | Alexandra of Lithuania | Uliana of Tver | yes | yes (2/2) |
| 2 | `d4ae7b5e0bdc11eba7f7acde48001122` | compositional | unknown | Ayutthaya | yes | yes (2/2) |
| 3 | `549d1a63086a11ebbd5fac1f6bf848b6` | comparison | No | no | yes | yes (2/2) |
| 4 | `90c8793c087411ebbd67ac1f6bf848b6` | bridge_comparison | unknown | Return To Cabin By The Lake | yes | yes (4/4) |
| 5 | `36a3fe2a0baf11ebab90acde48001122` | inference | Ulick Burke, 3rd Earl of Clanricarde | Richard Burke, 2nd Earl of Clanricarde | yes | yes (2/2) |
| 6 | `e61479860bda11eba7f7acde48001122` | compositional | unknown | Reykjavík | yes | yes (2/2) |
| 7 | `787f51ac097311ebbdb0ac1f6bf848b6` | comparison | Find a Place to Die | Find A Place To Die | yes | yes (2/2) |
| 8 | `e82674bd089311ebbd75ac1f6bf848b6` | bridge_comparison | A Pistol for Ringo | A Pistol For Ringo | yes | yes (4/4) |
| 9 | `48137be00baf11ebab90acde48001122` | inference | unknown | Abdul Qadir Najmuddin | yes | yes (2/2) |
| 10 | `62e8b66a0bdc11eba7f7acde48001122` | compositional | unknown | New York | yes | yes (2/2) |

## Sanity numbers (unofficial)

**These are rough checks, not the SCRUM-19 metrics.** They use no answer
normalization beyond case and must not be reported as results.

| Check | Value |
|---|---|
| Case-insensitive exact match of `predicted_answer` and gold answer | 3 of 10 (rows 3, 7, 8) |
| Questions with all gold paragraphs retrieved | 10 of 10 |

Observations, not conclusions:

- Retrieval found every gold paragraph for every question.
- Six answers were `unknown` even though the gold paragraphs were in the
  retrieved set.
- The two wrong named answers (rows 1 and 5) are one generation off the gold
  entity.
