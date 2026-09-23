# 2WikiMultiHopQA dev split: schema inspection (SCRUM-13)

## Source

- Repository: https://github.com/Alab-NII/2wikimultihop (authors' README,
  "New Update (April 7, 2021)")
- Archive: `https://www.dropbox.com/s/ms2m13252h6xubs/data_ids_april7.zip?dl=1`
  (258,968,175 bytes; contains `train.json`, `dev.json`, `test.json`,
  `id_aliases.json`)
- Downloaded: 2026-09-23, by `scripts/download_2wiki.py`, which extracts only
  `dev.json` and `id_aliases.json` via HTTP range requests (25.7 MB fetched).

| File | Bytes | sha256 |
|---|---|---|
| `data/raw/2wiki/dev.json` | 57,614,142 | `79f77ae104088ea8e25b1a65dbece768d45771194663bc5660ec9a98070dadf5` |
| `data/raw/2wiki/id_aliases.json` | 17,501,406 | `f08ffcb6c2cefca9bdbe86b4248d6ad7a7743762d3f7264c14ff0bae85726fb6` |

`dev.json` is a single JSON array; `id_aliases.json` is JSON Lines.

All figures below come from `python scripts/inspect_2wiki.py --wikidata`.

## Field list

12,576 questions. Every field is present in every record.

| Field | Type | Notes |
|---|---|---|
| `_id` | str | |
| `type` | str | `comparison` 3,040; `inference` 1,549; `compositional` 5,236; `bridge_comparison` 2,751 |
| `question` | str | |
| `context` | list of `[title: str, sentences: list[str]]` | |
| `entity_ids` | str | QIDs joined by `_` |
| `supporting_facts` | list of `[title: str, sent_id: int]` | |
| `evidences` | list of `[subject, relation, object]`, all str | |
| `answer` | str | |
| `evidences_id` | list of `[subject, relation, object]`, all str | empty list in 4,512 records |
| `answer_id` | str or null | null in 1,973 records (e.g. dates, yes/no answers) |

## evidences_id coverage

**Authors' claim** (README, "Update on December 8, 2020"): "For Inference and
Compositional questions: we add to all questions. For Comparison and
Bridge_comparison questions: we add to questions that have relations:
`country`, `country of origin`, and `country of citizenship`."

**What the data shows** (full dev set, "has" = non-empty `evidences_id`):

| Type | Questions | Has evidences_id | % | Has a country relation | Country relation but empty | Non-empty without country relation |
|---|---|---|---|---|---|---|
| comparison | 3,040 | 854 | 28.1% | 864 | 10 | 0 |
| inference | 1,549 | 1,549 | 100.0% | 0 | 0 | 1,549 |
| compositional | 5,236 | 5,236 | 100.0% | 802 | 0 | 4,434 |
| bridge_comparison | 2,751 | 425 | 15.4% | 429 | 4 | 0 |

The data matches the claim for inference and compositional. For comparison and
bridge_comparison it matches in one direction only: every non-empty
`evidences_id` involves a country relation, but 14 questions with a country
relation (10 comparison, 4 bridge_comparison) have an empty `evidences_id`.

Where `evidences_id` is non-empty, its relation sequence is identical to
`evidences` in every question (0 mismatches). Subjects are always QIDs; objects
are QIDs except 678 objects that are the literal placeholder `date_information`.

## How relations are expressed

Stratified random sample of 50 questions, `SEED = 694` in
`scripts/inspect_2wiki.py` (13 comparison, 13 inference, 12 compositional,
12 bridge_comparison). A relation counts as a P-id if it matches `^P[0-9]+$`;
both `evidences` and `evidences_id` were checked.

| Type | n | P-id | Label | Both | Questions with evidences_id |
|---|---|---|---|---|---|
| comparison | 13 | 0 | 13 | 0 | 6/13 |
| inference | 13 | 0 | 13 | 0 | 13/13 |
| compositional | 12 | 0 | 12 | 0 | 12/12 |
| bridge_comparison | 12 | 0 | 12 | 0 | 0/12 |
| **total** | **50** | **0** | **50** | **0** | 31/50 |

In the full dev set, 0 of 34 distinct relation strings are P-ids.

## Distinct relations

**In the sample** (triple counts in parentheses):

- comparison (4): country (4), country of origin (8), date of birth (4),
  publication date (10)
- inference (3): father (18), mother (5), spouse (3)
- compositional (11): award received (1), composer (1), country of
  citizenship (2), date of death (1), director (8), employer (1), father (2),
  place of birth (2), place of burial (1), place of death (2), spouse (3)
- bridge_comparison (4): date of birth (20), date of death (4), director (22),
  producer (2)

**In the full dev set:** 34 distinct relations. Per type: comparison 11,
inference 7, compositional 28, bridge_comparison 5.

## Wikidata property lookup

This is an external check, not something the dataset contains. Each of the 34
relation strings was searched on Wikidata (`wbsearchentities`,
`type=property`) on 2026-09-23, keeping exact matches in English variants only.

- 32 of 34 equal the English label of exactly one property (e.g. director →
  P57, father → P22, country of citizenship → P27, publication date → P577).
- `founded by`: matches only the `en-gb` label of P112 (English label:
  "founder").
- `has part`: no exact match; the closest hit is P527 "has part(s)".
- Some strings are also aliases of other properties (e.g. `country` is an alias
  of P3005, `creator` of P50), so a lookup must prefer label matches.
- The per-relation result is saved in `docs/notes/2wiki-relation-map.json`
  (32 `exact_en`, 1 `en_variant` [en-gb], 1 `none`).

The dataset and README do not say that relation strings were taken from
Wikidata property labels. The labels were checked against today's Wikidata,
not the 2020 version. This check shows the strings match labels; it does not
show that they have the same meaning.

## Verdict

These verdicts are about relations, meaning whether they map to Wikidata
properties.

- **comparison: partial.** No P-ids; all 11 labels equal an English Wikidata
  property label. Entity QIDs are present for only 28.1% of questions.
- **inference: partial.** No P-ids; all 7 labels equal an English Wikidata
  property label. Entity QIDs are present for 100%.
- **compositional: partial.** No P-ids; 26 of 28 labels equal an English label
  (`founded by` en-gb only, `has part` none). Entity QIDs are present for 100%,
  with dates replaced by `date_information`.
- **bridge_comparison: partial.** No P-ids; all 5 labels equal an English label.
  Entity QIDs are present for only 15.4%.

**Overall: partial.** The data has no Wikidata property IDs anywhere; relations
are English labels even inside `evidences_id`. 32 of the 34 labels resolve to a
single property by exact English-label lookup, so a mapping can be built by
lookup but is not given by the data.

## Findings that affect the ontology design

- **Relation vocabulary.** It is small and closed: 34 relations across the
  dev set. That is small enough to write as an explicit ontology relation list.
- **Inference questions.** They ask for relations that never appear as
  evidence. 1,396 of 1,549 inference questions contain a derived kinship term
  ("paternal grandfather" 556, "father-in-law" 142, "uncle" 42, ...). Their
  evidence triples use only base relations (father, mother, spouse, sibling,
  child, doctoral advisor, employer). Answering them needs composition rules
  over base relations.
- **Country relations.** There are three separate ones (`country`,
  `country of origin`, `country of citizenship`), each matching a different
  property (P17, P495, P27). The ontology has to decide whether to keep them
  apart.
- **Literal values.** Dates are not entities and have no normal form. In
  `evidences`, date relations (date of birth, date of death, publication date,
  inception) use 13 distinct surface formats, e.g. `28 August 1921`,
  `March 20, 1995`, `2003`. In `evidences_id` they become `date_information`.
- **Entity names.** Evidence entity names do not always match paragraph titles.
  10.6% of evidence subjects (3,301 of 31,120) differ from every context
  title, e.g. `Polish-Russian War` vs `Polish-Russian War (film)`,
  `Cleopatra IV` vs `Cleopatra IV of Egypt`. Matching extracted entities to
  gold triples needs QIDs or alias handling, and QIDs are missing for most
  comparison and bridge_comparison questions.
- **Triple counts.** Comparison questions are not always two triples: 230 of
  3,040 have 3 to 7. Bridge_comparison has 4 to 6. Inference and compositional
  always have 2.

## Not determined from the data

- Whether the relation strings were generated from Wikidata property labels, or
  from which Wikidata dump.
- Why 14 comparison/bridge_comparison questions with a country relation lack
  `evidences_id`.
- What `id_aliases.json` contains beyond being JSON Lines. It was extracted for
  a later story and not inspected here.
