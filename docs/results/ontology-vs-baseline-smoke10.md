# Ontology vs baseline, smoke10 (SCRUM-18)

Written by `scripts/compare_conditions.py`. Both conditions answer the same smoke10 questions with the same shared configuration, answer template, query settings, and seed; they differ only in the extraction prompt (see `docs/results/prompt-diff-baseline-vs-ontology.diff`).

## Provenance

| | baseline | ontology |
|---|---|---|
| Index commit | `7ac0e59` | `af7fb3c` |
| Index wall-clock | 5,383.3 s (53.8 s per paragraph) | 5,156.5 s (51.6 s per paragraph) |
| Query commit | `f9b7d24` | `af7fb3c` |
| Query LLM cache | off | off |
| Shared config sha256 | `0462fab880d2…` | `0462fab880d2…` |
| Condition config sha256 | `22f151c2a076…` | `b1e2fd4e2835…` |
| Answer template sha256 | `7f0e7292a5c2…` | `7f0e7292a5c2…` |
| Results sha256 | `6cc98361fb17…` | `af21cd1d427d…` |
| Fallback rows changed | 0 | 0 |

## Scores

Percentages, with the bootstrap 95% intervals from `scripts/score.py` (1,000 resamples, seed 694). EM and F1 compare with the gold answer only; the alias columns also accept the answer entity's aliases, as the official 2WikiMultiHopQA v1.1 script does.

| Group | n | Condition | EM | EM (aliases) | F1 | F1 (aliases) | Retrieval recall |
|---|---|---|---|---|---|---|---|
| overall | 10 | baseline | 30.0 [0.0, 60.0] | 30.0 [0.0, 60.0] | 40.0 [13.3, 70.0] | 40.0 [13.3, 70.0] | 100.0 [100.0, 100.0] |
| overall | 10 | ontology | 20.0 [0.0, 40.0] | 30.0 [0.0, 60.0] | 33.3 [6.7, 60.0] | 36.7 [10.0, 66.7] | 100.0 [100.0, 100.0] |
| inference | 3 | baseline | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 33.3 [0.0, 66.7] | 33.3 [0.0, 66.7] | 100.0 [100.0, 100.0] |
| inference | 3 | ontology | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 22.2 [0.0, 66.7] | 22.2 [0.0, 66.7] | 100.0 [100.0, 100.0] |
| compositional | 3 | baseline | 33.3 [0.0, 100.0] | 33.3 [0.0, 100.0] | 33.3 [0.0, 100.0] | 33.3 [0.0, 100.0] | 100.0 [100.0, 100.0] |
| compositional | 3 | ontology | 0.0 [0.0, 0.0] | 33.3 [0.0, 100.0] | 22.2 [0.0, 66.7] | 33.3 [0.0, 100.0] | 100.0 [100.0, 100.0] |
| comparison | 2 | baseline | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] |
| comparison | 2 | ontology | 50.0 [0.0, 100.0] | 50.0 [0.0, 100.0] | 50.0 [0.0, 100.0] | 50.0 [0.0, 100.0] | 100.0 [100.0, 100.0] |
| bridge_comparison | 2 | baseline | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 100.0 [100.0, 100.0] |
| bridge_comparison | 2 | ontology | 50.0 [0.0, 100.0] | 50.0 [0.0, 100.0] | 50.0 [0.0, 100.0] | 50.0 [0.0, 100.0] | 100.0 [100.0, 100.0] |

## Per question

"Right" is official EM with aliases.

| # | Question ID | Type | Gold | baseline answer | ontology answer | Right |
|---|---|---|---|---|---|---|
| 1 | `c8c5f3ee0baf11ebab90acde48001122` | inference | Uliana of Tver | Alexandra of Lithuania | Alexandra | both wrong |
| 2 | `d4ae7b5e0bdc11eba7f7acde48001122` | compositional | Ayutthaya | unknown | unknown | both wrong |
| 3 | `549d1a63086a11ebbd5fac1f6bf848b6` | comparison | no | no | no | both right |
| 4 | `90c8793c087411ebbd67ac1f6bf848b6` | bridge_comparison | Return To Cabin By The Lake | unknown | unknown | both wrong |
| 5 | `36a3fe2a0baf11ebab90acde48001122` | inference | Richard Burke, 2nd Earl of Clanricarde | Ulick Burke, 3rd Earl of Clanricarde | Ulick Burke, 3rd Earl of Clanricarde | both wrong |
| 6 | `e61479860bda11eba7f7acde48001122` | compositional | Reykjavík | Kingston | Kingston | both wrong |
| 7 | `787f51ac097311ebbdb0ac1f6bf848b6` | comparison | Find A Place To Die | Find A Place To Die | The Path of Torment | baseline only |
| 8 | `e82674bd089311ebbd75ac1f6bf848b6` | bridge_comparison | A Pistol For Ringo | Los Hijos de Fierro | A Pistol for Ringo | ontology only |
| 9 | `48137be00baf11ebab90acde48001122` | inference | Abdul Qadir Najmuddin | unknown | unknown | both wrong |
| 10 | `62e8b66a0bdc11eba7f7acde48001122` | compositional | New York | New York | New York, New York | both right |

Paired counts:

| Outcome | Questions |
|---|---|
| both right | 2 |
| baseline only | 1 |
| ontology only | 1 |
| both wrong | 6 |

Overall EM with aliases is 30.0 for baseline and 30.0 for ontology. The conditions disagree on 2 of 10 questions (1 baseline only, 1 ontology only). At this sample size these numbers do not show that either condition answers better; see Limitations.

## Graphs

Relation conformance and entity types are from `scripts/relation_conformance.py`. A date relation is an edge with a date-named node at either end (see the script docstring). The baseline prompt never names the ontology types, so its count of types outside the ontology only shows how far LightRAG's default type names are from the ontology's.

| Measure | baseline | ontology |
|---|---|---|
| Nodes | 467 | 481 |
| Edges | 357 | 354 |
| Relation conformance | 38 / 357 (10.6%) | 280 / 354 (79.1%) |
| Edges with several comma-joined keywords | 163 | 11 |
| Distinct entity types | 15 | 19 |
| Entities with a type outside the ontology | 344 of 467 | 19 of 481 |
| Date nodes | 7 | 5 |
| Date relations | 4 | 3 |

Entity types, baseline: person 229, organization 59, content 58, location 51, concept 18, artifact 16, event 12, other 5, date 4, title 4, unknown 3, chart 3, method 2, data 2, award 1.

Entity types, ontology: human 230, location 48, group 38, creativework 29, organization 28, film 26, country 17, award 14, other 8, event 8, unknown 7, occupation 6, settlementorregion 5, date 4, facility 3, musicalwork 3, writtenwork 3, educationalinstitution 2, broadcastprogram 2.

Date nodes, baseline: 1952, 1982, 1983, 2009, 6 February, 2018, December 19, 2015, January 31, 1886.

Date nodes, ontology: 12 November 1965, 31 December 1939, 4 August 1888, January 31, 1886, October 22, 1970.

Most common non-conforming keywords, ontology: `member of` (5), `grandfather` (4), `held in` (3), `worn by` (3), `member` (2), `engaged to` (2), `composer,creator` (2), `brother` (2), `cousin,served with` (2), `presented by` (2), `friend` (2), `collaborator` (2), `great grandfather` (2), `played for` (2), `co-regent` (1).

## Limitations

- **n = 10.** Every interval above is wide, and a difference of a few questions
  is within noise. For scale: the SCRUM-30 answer-template change alone, with
  the same index, changed 3 of the 10 baseline answers.
- **One run per condition.** Each condition was indexed and queried once, with
  seed 694. Run-to-run variation has not been measured (SCRUM-22).
- **No entity type for dates.** Dates are literal attributes in the ontology
  (SCRUM-17, D4), so a date the model extracts as a node gets a type outside
  the ontology (`date`, `other`, or `unknown`).
- **The base prompt still calls relationships undirected.** The ontology
  relations are directional, but the unchanged LightRAG instruction says to
  treat relationships as undirected, and the graph is stored undirected.
- **Relation definitions include Wikidata editor notes.** The definitions are
  English Wikidata property descriptions, copied verbatim, and some carry
  editing guidance such as "Use 'manner of death' (P1196)".
- **Conformance counts merged edges strictly.** An edge that LightRAG merged
  from two extractions with different labels carries both, comma-joined, and
  does not conform.
