# Ontology v2 vs v1 vs baseline, smoke10 (SCRUM-18)

Three runs on the same smoke10 questions (10 questions, 100 paragraphs), with
the same shared configuration (`configs/run_config.json` sha256
`0462fab880d2…`), answer template, query settings, seed 694, and the LLM cache
off for every query:

- **baseline**: schema-free LightRAG extraction (SCRUM-16, query re-run in SCRUM-30).
- **ontology v1**: the Sprint 2 ontology condition (SCRUM-18, PR #5).
- **ontology v2**: this run, with the revised ontology: a Date entity type as
  the range of the four date relations (D6) and relation definitions without
  Wikidata editor notes (D7). Nothing else in the condition changed; see
  `docs/results/prompt-diff-baseline-vs-ontology.diff`.

v2 was indexed and queried in the SCRUM-18 worktree, so its run directory is
separate from v1's. Its manifest is copied to
`docs/results/ontology-v2-smoke10-manifest.json`, its scores to
`docs/results/ontology-v2-smoke10-scores.md`, and its graph metrics to
`docs/results/graph-metrics-smoke10-ontology-v2.md`. The v1 files keep their
Sprint 2 names.

## Provenance

| | baseline | ontology v1 | ontology v2 |
|---|---|---|---|
| Index commit | `7ac0e59` | `af7fb3c` | `19a76ff` |
| Query commit | `f9b7d24` | `af7fb3c` | `56d8c10` |
| Condition config sha256 | `22f151c2a076…` | `b1e2fd4e2835…` | `b049bbac528c…` |
| Index, 100 paragraphs | 5,383.3 s, 53.8 s per paragraph | 5,156.5 s, 51.6 s per paragraph | 5,896.9 s, 59.0 s per paragraph |
| Query, mean per question | 158.9 s | 149.5 s | 143.4 s |
| Documents processed / failed | 100 / 0 | 100 / 0 | 100 / 0 |
| Fallback rows changed | 0 | 0 | 0 |

## Scores

Percentages, with bootstrap 95% intervals from `scripts/score.py` (1,000
resamples, seed 694). EM and F1 compare with the gold answer only; the alias
columns also accept the answer entity's aliases, as the official
2WikiMultiHopQA v1.1 script does.

| Group | n | Condition | EM | EM (aliases) | F1 | F1 (aliases) | Retrieval recall |
|---|---|---|---|---|---|---|---|
| overall | 10 | baseline | 30.0 [0.0, 60.0] | 30.0 [0.0, 60.0] | 40.0 [13.3, 70.0] | 40.0 [13.3, 70.0] | 100.0 [100.0, 100.0] |
| overall | 10 | ontology v1 | 20.0 [0.0, 40.0] | 30.0 [0.0, 60.0] | 33.3 [6.7, 60.0] | 36.7 [10.0, 66.7] | 100.0 [100.0, 100.0] |
| overall | 10 | ontology v2 | 30.0 [0.0, 60.0] | 40.0 [10.0, 70.0] | 46.7 [20.0, 73.3] | 50.0 [23.3, 76.7] | 95.0 [85.0, 100.0] |
| inference | 3 | baseline | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 33.3 [0.0, 66.7] | 33.3 [0.0, 66.7] | 100.0 [100.0, 100.0] |
| inference | 3 | ontology v1 | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 22.2 [0.0, 66.7] | 22.2 [0.0, 66.7] | 100.0 [100.0, 100.0] |
| inference | 3 | ontology v2 | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 33.3 [0.0, 66.7] | 33.3 [0.0, 66.7] | 100.0 [100.0, 100.0] |
| compositional | 3 | baseline | 33.3 [0.0, 100.0] | 33.3 [0.0, 100.0] | 33.3 [0.0, 100.0] | 33.3 [0.0, 100.0] | 100.0 [100.0, 100.0] |
| compositional | 3 | ontology v1 | 0.0 [0.0, 0.0] | 33.3 [0.0, 100.0] | 22.2 [0.0, 66.7] | 33.3 [0.0, 100.0] | 100.0 [100.0, 100.0] |
| compositional | 3 | ontology v2 | 0.0 [0.0, 0.0] | 33.3 [0.0, 100.0] | 22.2 [0.0, 66.7] | 33.3 [0.0, 100.0] | 100.0 [100.0, 100.0] |
| comparison | 2 | baseline | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] |
| comparison | 2 | ontology v1 | 50.0 [0.0, 100.0] | 50.0 [0.0, 100.0] | 50.0 [0.0, 100.0] | 50.0 [0.0, 100.0] | 100.0 [100.0, 100.0] |
| comparison | 2 | ontology v2 | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] |
| bridge_comparison | 2 | baseline | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 100.0 [100.0, 100.0] |
| bridge_comparison | 2 | ontology v1 | 50.0 [0.0, 100.0] | 50.0 [0.0, 100.0] | 50.0 [0.0, 100.0] | 50.0 [0.0, 100.0] | 100.0 [100.0, 100.0] |
| bridge_comparison | 2 | ontology v2 | 50.0 [0.0, 100.0] | 50.0 [0.0, 100.0] | 50.0 [0.0, 100.0] | 50.0 [0.0, 100.0] | 75.0 [50.0, 100.0] |

## Graphs

Relation conformance and entity types use `scripts/relation_conformance.py`,
duplicates `scripts/graph_metrics.py`, both unchanged. The relation labels
are the same 34 in v1 and v2, so relation conformance is on one scale for all
three graphs. Entity-type conformance is first measured against each
condition's own ontology (v1 for the baseline and v1, v2 for v2), then against
v2 for all three; v2 adds only the Date type. The baseline prompt never
showed an ontology, so its type conformance reflects only how close
LightRAG's default type names are to the ontology's.

| Measure | baseline | ontology v1 | ontology v2 |
|---|---|---|---|
| Nodes | 467 | 481 | 524 |
| Edges | 357 | 354 | 421 |
| Relation conformance | 38 / 357 (10.6%) | 280 / 354 (79.1%) | **343 / 421 (81.5%)** |
| Edges with comma-joined keywords | 163 | 11 | 11 |
| Entity-type conformance, own ontology | 123 / 467 (26.3%) | 462 / 481 (96.0%) | 494 / 524 (94.3%) |
| Entity-type conformance, v2 ontology | 127 / 467 (27.2%) | 466 / 481 (96.9%) | 494 / 524 (94.3%) |
| Duplicate rate | (20 - 10) / 467 (2.1%) | (42 - 18) / 481 (5.0%) | (34 - 17) / 524 (3.2%) |
| Entities typed `date` | 4 | 4 | 23 |
| Date-named entities | 7 | 5 | 19 |
| Date relations, by label (date of birth, date of death, inception, publication date) | 0 | 3 | 23 |
| Date relations, edges with a date-named entity at either end | 4 | 3 | 19 |
| Entities named as a relation label | 4 | 8 | 3 |

- **Duplicate rate.** The duplicate rule's precision, measured by hand on the
  baseline and v1 graphs, is 8/20 (about 40%; see
  `docs/results/duplicate-sample-smoke10.md`). The rates are therefore not
  comparable as measured, and v2's flagged pairs were not hand-checked.
- **Dates.** A date-named entity is a bare year, or a day, month name, and
  year, or a month name and year (the rule in
  `scripts/compare_conditions.py`). v2's date labels: date of birth 12,
  publication date 5, date of death 5, inception 1. Some v2 date entities are
  decades or ISO dates (`1360s`, `1633-02-17`), so they are typed `date`
  but not date-named.
- **Relation-label entities.** An entity counts when its name, with a
  trailing parenthetical removed, equals a relation label after
  normalization. Baseline: Country, Father, Mother, Place of Birth. v1:
  Director, place of birth, and six "Place of Birth" variants such as
  "Place of Birth (Sweden)". v2: Father, Mother, Place of Birth.
- **Types outside the ontology, v2:** other 20, unknown 7, publication 2,
  material 1.
- **Most common non-conforming keywords, v2:** educator (7), starred (7),
  member (5), supporter (3), held in (3), worn by (3), grandfather (3), and
  2 each of child,father,sibling, child,mother,sibling, attributed
  nationality, coup, sequel, conflict with, spouse of, successor. Of the 11
  comma-joined edges, 9 join only ontology labels (v1: 6 of 11).

## Answers, paired

"Right" is official EM with aliases.

| # | Question ID | Type | Gold | baseline | ontology v1 | ontology v2 | Right (EM, aliases) |
|---|---|---|---|---|---|---|---|
| 1 | `c8c5f3ee0baf11ebab90acde48001122` | inference | Uliana of Tver | Alexandra of Lithuania | Alexandra | Alexandra of Lithuania | none |
| 2 | `d4ae7b5e0bdc11eba7f7acde48001122` | compositional | Ayutthaya | unknown | unknown | unknown | none |
| 3 | `549d1a63086a11ebbd5fac1f6bf848b6` | comparison | no | no | no | no | baseline, v1, v2 |
| 4 | `90c8793c087411ebbd67ac1f6bf848b6` | bridge_comparison | Return To Cabin By The Lake | unknown | unknown | unknown | none |
| 5 | `36a3fe2a0baf11ebab90acde48001122` | inference | Richard Burke, 2nd Earl of Clanricarde | Ulick Burke, 3rd Earl of Clanricarde | Ulick Burke, 3rd Earl of Clanricarde | Ulick Burke, 3rd Earl of Clanricarde | none |
| 6 | `e61479860bda11eba7f7acde48001122` | compositional | Reykjavík | Kingston | Kingston | Kingston | none |
| 7 | `787f51ac097311ebbdb0ac1f6bf848b6` | comparison | Find A Place To Die | Find A Place To Die | The Path of Torment | Find A Place to Die | baseline, v2 |
| 8 | `e82674bd089311ebbd75ac1f6bf848b6` | bridge_comparison | A Pistol For Ringo | Los Hijos de Fierro | A Pistol for Ringo | A Pistol for Ringo | v1, v2 |
| 9 | `48137be00baf11ebab90acde48001122` | inference | Abdul Qadir Najmuddin | unknown | unknown | Mohammed Burhanuddin | none |
| 10 | `62e8b66a0bdc11eba7f7acde48001122` | compositional | New York | New York | New York, New York | New York, New York | baseline, v1, v2 |

| Pair | Both right | v2 only | Other only | Both wrong | Same answer text |
|---|---|---|---|---|---|
| v2 vs baseline | 3 | 1 | 0 | 6 | 6 of 10 |
| v2 vs v1 | 3 | 1 | 0 | 6 | 7 of 10 |

v2 is right on 4 of 10 questions, the baseline and v1 on 3 of 10 each. The
difference is one question each way (question 8 against the baseline,
question 7 against v1). Question 9 changed from "unknown" to a wrong name.

## Limitations

- **n = 10.** Every interval above is wide. A difference of one or a few
  questions is within noise: the SCRUM-30 answer-template change alone, on
  the same index, changed 3 of the 10 baseline answers.
- **One run per condition.** Each condition was indexed and queried once,
  with seed 694. Run-to-run variation is measured in SCRUM-22.
- **Duplicate rule precision about 40%.** See Graphs.
- **The base prompt still calls relationships undirected,** in both ontology
  versions, so the conditions differ only in the ontology sections.
- **Two changes at once.** v2 changes the definitions and adds Date together,
  so their separate effects are not measured.
