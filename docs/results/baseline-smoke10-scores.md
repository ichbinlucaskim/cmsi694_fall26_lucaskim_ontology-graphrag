# Scores: baseline, smoke10

Written by `scripts/score.py`; full per-question scores are in `runs/baseline/smoke10/scores.json` (git-ignored).

| Item | Value |
|---|---|
| Results file | `runs/baseline/smoke10/results.jsonl` |
| Results sha256 | `6cc98361fb17481bbfe0f2c0e2ab89d2e82ba158a7d2e8f607c29571e231f560` |
| Query run | commit `f9b7d24e8217eb1b756f78e9458072a3642cd8ab`, ended 2026-10-06T20:26:02+00:00 |
| Aliases | `data/raw/2wiki/id_aliases.json`, sha256 `f08ffcb6c2cefca9bdbe86b4248d6ad7a7743762d3f7264c14ff0bae85726fb6` |
| Scorer commit | `e7a2bb496332e07e73a80332ec23c5d1908194b9` |
| Answer metrics | official 2WikiMultiHopQA v1.1 evaluation ([script](https://github.com/Alab-NII/2wikimultihop/blob/13800e5be57df1b4040b9b1588c6c811779e69e9/2wikimultihop_evaluate_v1.1.py)) |

Scores are percentages. Brackets give the bootstrap 95% confidence interval (1,000 resamples, seed 694). EM and F1 compare with the gold answer only; the alias columns also accept the aliases and demonyms of the answer entity, as the official script does.

| Group | n | EM | EM (aliases) | F1 | F1 (aliases) | Retrieval recall |
|---|---|---|---|---|---|---|
| overall | 10 | 30.0 [0.0, 60.0] | 30.0 [0.0, 60.0] | 40.0 [13.3, 70.0] | 40.0 [13.3, 70.0] | 100.0 [100.0, 100.0] |
| inference | 3 | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 33.3 [0.0, 66.7] | 33.3 [0.0, 66.7] | 100.0 [100.0, 100.0] |
| compositional | 3 | 33.3 [0.0, 100.0] | 33.3 [0.0, 100.0] | 33.3 [0.0, 100.0] | 33.3 [0.0, 100.0] | 100.0 [100.0, 100.0] |
| comparison | 2 | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] |
| bridge_comparison | 2 | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 100.0 [100.0, 100.0] |

Mean paragraphs retrieved per question: 20.0.

Rows that relied on the answer-normalization fallback: 0 of 10.

## Per question

| # | Question ID | Type | Predicted | Gold | EM | EM (aliases) | F1 | F1 (aliases) | Recall | Retrieved |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `c8c5f3ee0baf11ebab90acde48001122` | inference | Alexandra of Lithuania | Uliana of Tver | 0 | 0 | 0.33 | 0.33 | 1.00 | 20 |
| 2 | `d4ae7b5e0bdc11eba7f7acde48001122` | compositional | unknown | Ayutthaya | 0 | 0 | 0.00 | 0.00 | 1.00 | 20 |
| 3 | `549d1a63086a11ebbd5fac1f6bf848b6` | comparison | no | no | 1 | 1 | 1.00 | 1.00 | 1.00 | 20 |
| 4 | `90c8793c087411ebbd67ac1f6bf848b6` | bridge_comparison | unknown | Return To Cabin By The Lake | 0 | 0 | 0.00 | 0.00 | 1.00 | 20 |
| 5 | `36a3fe2a0baf11ebab90acde48001122` | inference | Ulick Burke, 3rd Earl of Clanricarde | Richard Burke, 2nd Earl of Clanricarde | 0 | 0 | 0.67 | 0.67 | 1.00 | 20 |
| 6 | `e61479860bda11eba7f7acde48001122` | compositional | Kingston | Reykjavík | 0 | 0 | 0.00 | 0.00 | 1.00 | 20 |
| 7 | `787f51ac097311ebbdb0ac1f6bf848b6` | comparison | Find A Place To Die | Find A Place To Die | 1 | 1 | 1.00 | 1.00 | 1.00 | 20 |
| 8 | `e82674bd089311ebbd75ac1f6bf848b6` | bridge_comparison | Los Hijos de Fierro | A Pistol For Ringo | 0 | 0 | 0.00 | 0.00 | 1.00 | 20 |
| 9 | `48137be00baf11ebab90acde48001122` | inference | unknown | Abdul Qadir Najmuddin | 0 | 0 | 0.00 | 0.00 | 1.00 | 20 |
| 10 | `62e8b66a0bdc11eba7f7acde48001122` | compositional | New York | New York | 1 | 1 | 1.00 | 1.00 | 1.00 | 20 |
