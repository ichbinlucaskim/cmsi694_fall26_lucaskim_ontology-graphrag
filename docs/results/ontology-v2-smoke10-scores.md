# Scores: ontology, smoke10

Written by `scripts/score.py`; full per-question scores are in `runs/ontology/smoke10/scores.json` (git-ignored).

| Item | Value |
|---|---|
| Results file | `runs/ontology/smoke10/results.jsonl` |
| Results sha256 | `0d44e8afb9effbaa196fcf1f939efe75503cae3c6e7f59ea3971c273440750df` |
| Query run | commit `56d8c102281dcb6ea9b7206196b68efb50413fa1`, ended 2026-10-23T22:13:45+00:00 |
| Aliases | `data/raw/2wiki/id_aliases.json`, sha256 `f08ffcb6c2cefca9bdbe86b4248d6ad7a7743762d3f7264c14ff0bae85726fb6` |
| Scorer commit | `56d8c102281dcb6ea9b7206196b68efb50413fa1` (dirty) |
| Answer metrics | official 2WikiMultiHopQA v1.1 evaluation ([script](https://github.com/Alab-NII/2wikimultihop/blob/13800e5be57df1b4040b9b1588c6c811779e69e9/2wikimultihop_evaluate_v1.1.py)) |

Scores are percentages. Brackets give the bootstrap 95% confidence interval (1,000 resamples, seed 694). EM and F1 compare with the gold answer only; the alias columns also accept the aliases and demonyms of the answer entity, as the official script does.

| Group | n | EM | EM (aliases) | F1 | F1 (aliases) | Retrieval recall |
|---|---|---|---|---|---|---|
| overall | 10 | 30.0 [0.0, 60.0] | 40.0 [10.0, 70.0] | 46.7 [20.0, 73.3] | 50.0 [23.3, 76.7] | 95.0 [85.0, 100.0] |
| inference | 3 | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 33.3 [0.0, 66.7] | 33.3 [0.0, 66.7] | 100.0 [100.0, 100.0] |
| compositional | 3 | 0.0 [0.0, 0.0] | 33.3 [0.0, 100.0] | 22.2 [0.0, 66.7] | 33.3 [0.0, 100.0] | 100.0 [100.0, 100.0] |
| comparison | 2 | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] |
| bridge_comparison | 2 | 50.0 [0.0, 100.0] | 50.0 [0.0, 100.0] | 50.0 [0.0, 100.0] | 50.0 [0.0, 100.0] | 75.0 [50.0, 100.0] |

Mean paragraphs retrieved per question: 20.0.

Rows that relied on the answer-normalization fallback: 0 of 10.

## Per question

| # | Question ID | Type | Predicted | Gold | EM | EM (aliases) | F1 | F1 (aliases) | Recall | Retrieved |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `c8c5f3ee0baf11ebab90acde48001122` | inference | Alexandra of Lithuania | Uliana of Tver | 0 | 0 | 0.33 | 0.33 | 1.00 | 20 |
| 2 | `d4ae7b5e0bdc11eba7f7acde48001122` | compositional | unknown | Ayutthaya | 0 | 0 | 0.00 | 0.00 | 1.00 | 20 |
| 3 | `549d1a63086a11ebbd5fac1f6bf848b6` | comparison | no | no | 1 | 1 | 1.00 | 1.00 | 1.00 | 20 |
| 4 | `90c8793c087411ebbd67ac1f6bf848b6` | bridge_comparison | unknown | Return To Cabin By The Lake | 0 | 0 | 0.00 | 0.00 | 0.50 | 20 |
| 5 | `36a3fe2a0baf11ebab90acde48001122` | inference | Ulick Burke, 3rd Earl of Clanricarde | Richard Burke, 2nd Earl of Clanricarde | 0 | 0 | 0.67 | 0.67 | 1.00 | 20 |
| 6 | `e61479860bda11eba7f7acde48001122` | compositional | Kingston | Reykjavík | 0 | 0 | 0.00 | 0.00 | 1.00 | 20 |
| 7 | `787f51ac097311ebbdb0ac1f6bf848b6` | comparison | Find A Place to Die | Find A Place To Die | 1 | 1 | 1.00 | 1.00 | 1.00 | 20 |
| 8 | `e82674bd089311ebbd75ac1f6bf848b6` | bridge_comparison | A Pistol for Ringo | A Pistol For Ringo | 1 | 1 | 1.00 | 1.00 | 1.00 | 20 |
| 9 | `48137be00baf11ebab90acde48001122` | inference | Mohammed Burhanuddin | Abdul Qadir Najmuddin | 0 | 0 | 0.00 | 0.00 | 1.00 | 20 |
| 10 | `62e8b66a0bdc11eba7f7acde48001122` | compositional | New York, New York | New York | 0 | 1 | 0.67 | 1.00 | 1.00 | 20 |
