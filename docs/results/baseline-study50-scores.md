# Scores: baseline, study50

Written by `scripts/score.py`; full per-question scores are in `runs/baseline/study50/scores.json` (git-ignored).

| Item | Value |
|---|---|
| Results file | `runs/baseline/study50/results.jsonl` |
| Results sha256 | `2b01ce8b86f782368f5ee95487ca7223612dce76613cfdfc5040435f8248c02c` |
| Query run | commit `fca12d581c4fee54c9857432f908855b2ba262de`, ended 2026-10-23T15:13:29+00:00 |
| Aliases | `data/raw/2wiki/id_aliases.json`, sha256 `f08ffcb6c2cefca9bdbe86b4248d6ad7a7743762d3f7264c14ff0bae85726fb6` |
| Scorer commit | `fca12d581c4fee54c9857432f908855b2ba262de` (dirty) |
| Answer metrics | official 2WikiMultiHopQA v1.1 evaluation ([script](https://github.com/Alab-NII/2wikimultihop/blob/13800e5be57df1b4040b9b1588c6c811779e69e9/2wikimultihop_evaluate_v1.1.py)) |

Scores are percentages. Brackets give the bootstrap 95% confidence interval (1,000 resamples, seed 694). EM and F1 compare with the gold answer only; the alias columns also accept the aliases and demonyms of the answer entity, as the official script does.

| Group | n | EM | EM (aliases) | F1 | F1 (aliases) | Retrieval recall |
|---|---|---|---|---|---|---|
| overall | 50 | 36.0 [24.0, 48.0] | 42.0 [30.0, 56.0] | 47.8 [35.6, 59.9] | 51.2 [38.3, 63.9] | 94.5 [90.5, 98.0] |
| inference | 13 | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 23.3 [6.8, 39.5] | 23.7 [6.8, 40.5] | 100.0 [100.0, 100.0] |
| compositional | 13 | 15.4 [0.0, 38.5] | 38.5 [15.4, 69.2] | 32.3 [11.8, 55.6] | 45.1 [21.0, 71.0] | 100.0 [100.0, 100.0] |
| comparison | 12 | 66.7 [41.7, 91.7] | 66.7 [41.7, 91.7] | 66.7 [41.7, 91.7] | 66.7 [41.7, 91.7] | 100.0 [100.0, 100.0] |
| bridge_comparison | 12 | 66.7 [41.7, 91.7] | 66.7 [41.7, 91.7] | 72.2 [47.2, 91.7] | 72.2 [47.2, 91.7] | 77.1 [66.7, 87.5] |

Mean paragraphs retrieved per question: 20.0.

Rows that relied on the answer-normalization fallback: 0 of 50.

## Per question

| # | Question ID | Type | Predicted | Gold | EM | EM (aliases) | F1 | F1 (aliases) | Recall | Retrieved |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `c8c5f3ee0baf11ebab90acde48001122` | inference | unknown | Uliana of Tver | 0 | 0 | 0.00 | 0.00 | 1.00 | 20 |
| 2 | `d4ae7b5e0bdc11eba7f7acde48001122` | compositional | unknown | Ayutthaya | 0 | 0 | 0.00 | 0.00 | 1.00 | 20 |
| 3 | `549d1a63086a11ebbd5fac1f6bf848b6` | comparison | no | no | 1 | 1 | 1.00 | 1.00 | 1.00 | 20 |
| 4 | `90c8793c087411ebbd67ac1f6bf848b6` | bridge_comparison | Return to Cabin by the Lake | Return To Cabin By The Lake | 1 | 1 | 1.00 | 1.00 | 0.75 | 20 |
| 5 | `36a3fe2a0baf11ebab90acde48001122` | inference | Ulick Burke, 3rd Earl of Clanricarde | Richard Burke, 2nd Earl of Clanricarde | 0 | 0 | 0.67 | 0.67 | 1.00 | 20 |
| 6 | `e61479860bda11eba7f7acde48001122` | compositional | Kingston | Reykjavík | 0 | 0 | 0.00 | 0.00 | 1.00 | 20 |
| 7 | `787f51ac097311ebbdb0ac1f6bf848b6` | comparison | Find a Place to Die | Find A Place To Die | 1 | 1 | 1.00 | 1.00 | 1.00 | 20 |
| 8 | `e82674bd089311ebbd75ac1f6bf848b6` | bridge_comparison | Los Hijos de Fierro | A Pistol For Ringo | 0 | 0 | 0.00 | 0.00 | 1.00 | 20 |
| 9 | `48137be00baf11ebab90acde48001122` | inference | unknown | Abdul Qadir Najmuddin | 0 | 0 | 0.00 | 0.00 | 1.00 | 20 |
| 10 | `62e8b66a0bdc11eba7f7acde48001122` | compositional | New York, New York | New York | 0 | 1 | 0.67 | 1.00 | 1.00 | 20 |
| 11 | `e4d6a06c08a111ebbd7aac1f6bf848b6` | comparison | Adolf Fischhof | Adolf Fischhof | 1 | 1 | 1.00 | 1.00 | 1.00 | 20 |
| 12 | `711cc23a088011ebbd6cac1f6bf848b6` | bridge_comparison | unknown | A Man Of Mayfair | 0 | 0 | 0.00 | 0.00 | 0.50 | 20 |
| 13 | `21ec1e0e0baf11ebab90acde48001122` | inference | unknown | Henrietta Maria of France | 0 | 0 | 0.00 | 0.00 | 1.00 | 20 |
| 14 | `8abaaafe0bdc11eba7f7acde48001122` | compositional | 18 February 1703 | 18 February 1703 | 1 | 1 | 1.00 | 1.00 | 1.00 | 20 |
| 15 | `3afdad9c086f11ebbd62ac1f6bf848b6` | comparison | Patrick Janvier | Patrick Janvier | 1 | 1 | 1.00 | 1.00 | 1.00 | 20 |
| 16 | `103f164e088e11ebbd70ac1f6bf848b6` | bridge_comparison | Madam Satan | Madam Satan | 1 | 1 | 1.00 | 1.00 | 0.75 | 20 |
| 17 | `fcd1f6ba0baf11ebab90acde48001122` | inference | John Lyon, 4th Earl of Strathmore and Kinghorne | Patrick Lyon, 3rd Earl of Strathmore and Kinghorne | 0 | 0 | 0.75 | 0.80 | 1.00 | 20 |
| 18 | `3581ccec0bdd11eba7f7acde48001122` | compositional | Yugoslav | Serbian | 0 | 0 | 0.00 | 0.00 | 1.00 | 20 |
| 19 | `569f6717097d11ebbdb0ac1f6bf848b6` | comparison | Alkohol | Alkohol | 1 | 1 | 1.00 | 1.00 | 1.00 | 20 |
| 20 | `4782cd7d087e11ebbd6bac1f6bf848b6` | bridge_comparison | The Olsen Gang's Big Score | The Olsen Gang'S Big Score | 1 | 1 | 1.00 | 1.00 | 0.75 | 20 |
| 21 | `9d570e6e0baf11ebab90acde48001122` | inference | Thutmose II | Hatshepsut | 0 | 0 | 0.00 | 0.00 | 1.00 | 20 |
| 22 | `805844f80bdd11eba7f7acde48001122` | compositional | unknown | Fairfax | 0 | 0 | 0.00 | 0.00 | 1.00 | 20 |
| 23 | `f998c58c091b11ebbdaeac1f6bf848b6` | comparison | no | yes | 0 | 0 | 0.00 | 0.00 | 1.00 | 20 |
| 24 | `53ab316c08b911ebbd88ac1f6bf848b6` | bridge_comparison | The Devil's Hairpin | The Devil'S Hairpin | 1 | 1 | 1.00 | 1.00 | 0.75 | 20 |
| 25 | `be0a16240baf11ebab90acde48001122` | inference | Princess Caroline of Nassau-Usingen | Princess Mary of Great Britain | 0 | 0 | 0.44 | 0.44 | 1.00 | 20 |
| 26 | `407810d40bdd11eba7f7acde48001122` | compositional | Toronto | Toronto, Ontario | 0 | 1 | 0.67 | 1.00 | 1.00 | 20 |
| 27 | `f75d22fa095d11ebbdafac1f6bf848b6` | comparison | Age of the Dragons | Age Of The Dragons | 1 | 1 | 1.00 | 1.00 | 1.00 | 20 |
| 28 | `8b165288088911ebbd6eac1f6bf848b6` | bridge_comparison | The McConnell Story | The Mcconnell Story | 1 | 1 | 1.00 | 1.00 | 0.50 | 20 |
| 29 | `8eb5dfe20bb011ebab90acde48001122` | inference | Francesco Ruspoli, 8th Prince of Cerveteri | Alessandro Ruspoli, 7th Prince of Cerveteri | 0 | 0 | 0.67 | 0.67 | 1.00 | 20 |
| 30 | `05155b180bde11eba7f7acde48001122` | compositional | University of the Philippines Open University | University of Perpetual Help System DALTA | 0 | 0 | 0.36 | 0.36 | 1.00 | 20 |
| 31 | `5ac1f04908d311ebbd96ac1f6bf848b6` | comparison | yes | yes | 1 | 1 | 1.00 | 1.00 | 1.00 | 20 |
| 32 | `78b84f3608db11ebbd9cac1f6bf848b6` | bridge_comparison | Adieu Bonaparte | Adieu Bonaparte | 1 | 1 | 1.00 | 1.00 | 1.00 | 20 |
| 33 | `9fdd38980baf11ebab90acde48001122` | inference | Alessandro Vitelli | Troilo I de' Rossi | 0 | 0 | 0.00 | 0.00 | 1.00 | 20 |
| 34 | `38fdf5420bda11eba7f7acde48001122` | compositional | Los Angeles | L.A. | 0 | 1 | 0.00 | 1.00 | 1.00 | 20 |
| 35 | `77119398087411ebbd67ac1f6bf848b6` | comparison | The Apocalypse Code | Just Imagine | 0 | 0 | 0.00 | 0.00 | 1.00 | 20 |
| 36 | `bf3e001408c111ebbd8bac1f6bf848b6` | bridge_comparison | The Buttercup Chain | Gambling On The High Seas | 0 | 0 | 0.00 | 0.00 | 0.75 | 20 |
| 37 | `67d898240bb011ebab90acde48001122` | inference | unknown | Isabelle of Luxembourg | 0 | 0 | 0.00 | 0.00 | 1.00 | 20 |
| 38 | `26c35f920bdb11eba7f7acde48001122` | compositional | unknown | Georgia O'Keeffe | 0 | 0 | 0.00 | 0.00 | 1.00 | 20 |
| 39 | `debaf1c5084c11ebbd56ac1f6bf848b6` | comparison | unknown | James Pender | 0 | 0 | 0.00 | 0.00 | 1.00 | 20 |
| 40 | `3f894264086411ebbd5eac1f6bf848b6` | bridge_comparison | 5 År – Som Vi Så Dem | 5 År – Som Vi Så Dem | 1 | 1 | 1.00 | 1.00 | 0.50 | 20 |
| 41 | `6c80bc4e0bb011ebab90acde48001122` | inference | unknown | Margaret Montgomerie | 0 | 0 | 0.00 | 0.00 | 1.00 | 20 |
| 42 | `38779cfe0bda11eba7f7acde48001122` | compositional | unknown | Tennessee | 0 | 0 | 0.00 | 0.00 | 1.00 | 20 |
| 43 | `a469ea08084b11ebbd56ac1f6bf848b6` | comparison | unknown | Robert Von Zimmermann | 0 | 0 | 0.00 | 0.00 | 1.00 | 20 |
| 44 | `8474fb5e08a811ebbd7fac1f6bf848b6` | bridge_comparison | Lying, Sleeping | Jára Cimrman Lying, Sleeping | 0 | 0 | 0.67 | 0.67 | 1.00 | 20 |
| 45 | `52599bce0bb011ebab90acde48001122` | inference | unknown | Charles, Duke of Lower Lorraine | 0 | 0 | 0.00 | 0.00 | 1.00 | 20 |
| 46 | `8ecf15540bdb11eba7f7acde48001122` | compositional | Paris | Paris | 1 | 1 | 1.00 | 1.00 | 1.00 | 20 |
| 47 | `ab28bfb6097d11ebbdb0ac1f6bf848b6` | comparison | Mama's Little Pirate | Mama'S Little Pirate | 1 | 1 | 1.00 | 1.00 | 1.00 | 20 |
| 48 | `16b5529e085d11ebbd5cac1f6bf848b6` | bridge_comparison | Det drønner gjennom dalen | Det Drønner Gjennom Dalen | 1 | 1 | 1.00 | 1.00 | 1.00 | 20 |
| 49 | `e9dc3da00bae11ebab90acde48001122` | inference | Nurbu Sultan | Hürrem Sultan | 0 | 0 | 0.50 | 0.50 | 1.00 | 20 |
| 50 | `c7134f820bdd11eba7f7acde48001122` | compositional | 1945 | 6 June 1945 | 0 | 0 | 0.50 | 0.50 | 1.00 | 20 |
