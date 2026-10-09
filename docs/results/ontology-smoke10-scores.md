# Scores: ontology, smoke10

Written by `scripts/score.py`; full per-question scores are in `runs/ontology/smoke10/scores.json` (git-ignored).

| Item | Value |
|---|---|
| Results file | `runs/ontology/smoke10/results.jsonl` |
| Results sha256 | `af21cd1d427d90d2dbfed1fe21604e457061f256c5a4b5e8e5d4c1f295e80770` |
| Query run | commit `af7fb3c1a354363ffeff6895e9b92474a86f5aeb`, ended 2026-10-09T20:48:56+00:00 |
| Aliases | `data/raw/2wiki/id_aliases.json`, sha256 `f08ffcb6c2cefca9bdbe86b4248d6ad7a7743762d3f7264c14ff0bae85726fb6` |
| Scorer commit | `b01d525582f46b14b0341d1f735430fd77c205ff` |
| Answer metrics | official 2WikiMultiHopQA v1.1 evaluation ([script](https://github.com/Alab-NII/2wikimultihop/blob/13800e5be57df1b4040b9b1588c6c811779e69e9/2wikimultihop_evaluate_v1.1.py)) |

Scores are percentages. Brackets give the bootstrap 95% confidence interval (1,000 resamples, seed 694). EM and F1 compare with the gold answer only; the alias columns also accept the aliases and demonyms of the answer entity, as the official script does.

| Group | n | EM | EM (aliases) | F1 | F1 (aliases) | Retrieval recall |
|---|---|---|---|---|---|---|
| overall | 10 | 20.0 [0.0, 40.0] | 30.0 [0.0, 60.0] | 33.3 [6.7, 60.0] | 36.7 [10.0, 66.7] | 100.0 [100.0, 100.0] |
| inference | 3 | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 22.2 [0.0, 66.7] | 22.2 [0.0, 66.7] | 100.0 [100.0, 100.0] |
| compositional | 3 | 0.0 [0.0, 0.0] | 33.3 [0.0, 100.0] | 22.2 [0.0, 66.7] | 33.3 [0.0, 100.0] | 100.0 [100.0, 100.0] |
| comparison | 2 | 50.0 [0.0, 100.0] | 50.0 [0.0, 100.0] | 50.0 [0.0, 100.0] | 50.0 [0.0, 100.0] | 100.0 [100.0, 100.0] |
| bridge_comparison | 2 | 50.0 [0.0, 100.0] | 50.0 [0.0, 100.0] | 50.0 [0.0, 100.0] | 50.0 [0.0, 100.0] | 100.0 [100.0, 100.0] |

Mean paragraphs retrieved per question: 20.0.

Rows that relied on the answer-normalization fallback: 0 of 10.

## Per question

| # | Question ID | Type | Predicted | Gold | EM | EM (aliases) | F1 | F1 (aliases) | Recall | Retrieved |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `c8c5f3ee0baf11ebab90acde48001122` | inference | Alexandra | Uliana of Tver | 0 | 0 | 0.00 | 0.00 | 1.00 | 20 |
| 2 | `d4ae7b5e0bdc11eba7f7acde48001122` | compositional | unknown | Ayutthaya | 0 | 0 | 0.00 | 0.00 | 1.00 | 20 |
| 3 | `549d1a63086a11ebbd5fac1f6bf848b6` | comparison | no | no | 1 | 1 | 1.00 | 1.00 | 1.00 | 20 |
| 4 | `90c8793c087411ebbd67ac1f6bf848b6` | bridge_comparison | unknown | Return To Cabin By The Lake | 0 | 0 | 0.00 | 0.00 | 1.00 | 20 |
| 5 | `36a3fe2a0baf11ebab90acde48001122` | inference | Ulick Burke, 3rd Earl of Clanricarde | Richard Burke, 2nd Earl of Clanricarde | 0 | 0 | 0.67 | 0.67 | 1.00 | 20 |
| 6 | `e61479860bda11eba7f7acde48001122` | compositional | Kingston | Reykjavík | 0 | 0 | 0.00 | 0.00 | 1.00 | 20 |
| 7 | `787f51ac097311ebbdb0ac1f6bf848b6` | comparison | The Path of Torment | Find A Place To Die | 0 | 0 | 0.00 | 0.00 | 1.00 | 20 |
| 8 | `e82674bd089311ebbd75ac1f6bf848b6` | bridge_comparison | A Pistol for Ringo | A Pistol For Ringo | 1 | 1 | 1.00 | 1.00 | 1.00 | 20 |
| 9 | `48137be00baf11ebab90acde48001122` | inference | unknown | Abdul Qadir Najmuddin | 0 | 0 | 0.00 | 0.00 | 1.00 | 20 |
| 10 | `62e8b66a0bdc11eba7f7acde48001122` | compositional | New York, New York | New York | 0 | 1 | 0.67 | 1.00 | 1.00 | 20 |
