# Graph metrics, smoke10 (SCRUM-21)

Written by `scripts/graph_metrics.py`, which documents every rule in its docstring. Each measure is shown with the counts behind it.

## Inputs

Ontology: `ontology/ontology.json` (sha256 `dd9d7667c888…`).

| Graph | Run directory | GraphML sha256 |
|---|---|---|
| baseline | `runs/baseline/smoke10` | `acebbf0e2e6c…` |
| ontology | `runs/ontology/smoke10` | `0385cb34ae14…` |

## Metrics

| Measure | baseline | ontology |
|---|---|---|
| Entities | 467 | 481 |
| Relations | 357 | 354 |
| Entity-type conformance | 123 / 467 (26.3%) | 462 / 481 (96.0%) |
| Relation conformance | 38 / 357 (10.6%) | 280 / 354 (79.1%) |
| Relations with comma-joined keywords | 163 | 11 |
| Duplicate clusters | 10 | 18 |
| Entities in duplicate clusters | 20 | 42 |
| Duplicate rate | (20 - 10) / 467 (2.1%) | (42 - 18) / 481 (5.0%) |
| Flagged duplicate pairs | 10 | 40 |

The baseline prompt never showed the ontology, so the baseline's entity-type conformance reflects only how close LightRAG's default type names (person, organization, location, ...) are to the ontology's type names. It is not a measure of the baseline following the ontology.

## Entity types

baseline, all types: person 229, organization 59, content 58, location 51, concept 18, artifact 16, event 12, other 5, date 4, title 4, unknown 3, chart 3, method 2, data 2, award 1.

baseline, types outside the ontology: person 229, content 58, concept 18, artifact 16, other 5, date 4, title 4, chart 3, unknown 3, data 2, method 2.

ontology, all types: human 230, location 48, group 38, creativework 29, organization 28, film 26, country 17, award 14, other 8, event 8, unknown 7, occupation 6, settlementorregion 5, date 4, facility 3, musicalwork 3, writtenwork 3, educationalinstitution 2, broadcastprogram 2.

ontology, types outside the ontology: other 8, unknown 7, date 4.

## Duplicate clusters

### baseline

- `Athenry, County Galway, Ireland`; `County Galway`
- `Cabin by the Lake`; `Return to Cabin by the Lake`
- `FIND`; `Find`
- `Joystick`; `Joystick (song)`
- `King Maha Chakkraphat`; `Maha Chakkraphat`
- `La Hora de los Hornos`; `La hora de los hornos (The Hour of the Furnaces)`
- `New York`; `New York Museum of Modern Art`
- `Siemowit III`; `Siemowit III of Masovia`
- `Sir William Burke, younger son of Ulick Burke, 3rd Earl of Clanricarde`; `Ulick Burke, 3rd Earl of Clanricarde`
- `The Presidents of the United States of America`; `United States`

### ontology

- `Place of Birth`; `Place of Birth (Airplane Birth)`; `Place of Birth (Legal Documents)`; `Place of Birth (Sea Birth)`; `Place of Birth (Sweden)`; `Place of Birth (Switzerland)`; `place of birth`
- `Syedna Mohammad Burhanuddin`; `Syedna Taher Saifuddin bin Syedna Mohammad Burhanuddin`; `Taher Saifuddin`
- `Abd Manaf`; `Hashim ibn' Abd Manaf`
- `Cabin by the Lake`; `Return to Cabin by the Lake`
- `Dazz Band`; `The Dazz Band`
- `Earl of St. Albans`; `Ulick MacRichard Burke, 1st Marquess of Clanricarde, 5th Earl of Clanricarde, 2nd Earl of St Albans`
- `Fakhruddin Shaheed`; `Syedi Fakhruddin Shaheed`
- `Frances Walsingham and Richard Burke, Earl of Clanricarde`; `Richard Burke, Earl of Clanricarde`
- `Grammy Award`; `Grammy Award for Best R&B Performance by a Duo or Group with Vocals`
- `King Maha Chakkraphat`; `Maha Chakkraphat`
- `King Władysław II Jagiełło of Poland`; `Władysław II Jagiełło`
- `Mohammed Burhanuddin`; `Syedna Mohammed Burhanuddin`
- `Place of Origin`; `place of origin`
- `Servant in the Place of Truth`; `The Place of Truth`
- `Siemowit III`; `Siemowit III of Masovia`
- `Sir Philip Sidney`; `Sir Philip Sidney and Robert Devereaux, Earl of Essex`
- `The Presidents of the United States of America`; `United States`
- `The Time`; `Time`

## Interpretation

This section was written by hand after the hand check; regenerating the report
with `--out` drops it.

The duplicate rates, 2.1% for the baseline and 5.0% for the ontology graph,
cannot be compared as measured. In the hand-checked sample of 20 flagged pairs
(`docs/results/duplicate-sample-smoke10.md`), 8 name the same entity:
precision 40.0% overall, 3/7 in the baseline graph and 5/13 in the ontology
graph. Most flagged pairs are therefore not duplicates, and with 7 and 13
sample pairs per graph the precision of each graph is too uncertain to correct
its rate, so the measured rates do not show which graph has more duplicates.

The 12 false pairs show these error patterns:

| Pattern | Sample pairs | In the sample |
|---|---|---|
| A parent's name inside a child's name ("ibn", "bin", "younger son of") | 6, 8, 19 | both graphs; the "ibn" and "bin" forms only in the ontology graph |
| A film and its sequel | 2, 9 | both graphs |
| Two people joined with "and" into one entity | 13, 18 | ontology only |
| A place and the region containing it | 1 | baseline only |
| A title and a person who held it | 11 | ontology only |
| A relation label turned into an entity ("Place of Origin") | 16 | ontology only |
| A name that contains an unrelated name (a band and a country) | 7 | baseline only |
| Two different things with the same name (a band and a magazine) | 20 | ontology only |

Five patterns appear only in the ontology graph's sample pairs: entities
joined with "and", a title against its holder, a relation label as an entity,
the same-name pair, and the "ibn"/"bin" form of the parent pattern. The
cluster lists above agree for the first three: the baseline graph has no
cluster of those kinds, while the ontology graph also has the 7-entity "Place
of Birth (...)" cluster. The band-and-country cluster is in both graphs but
was drawn only from the baseline. Clusters outside the sample were not
labeled.

The "and" entities, the title node, and the relation-label entities are
extraction errors in their own right, so they also bear on the ontology
condition's entity quality, separately from the duplicate rule.

The rule is not changed in this story. A rule with better precision, for
example one that does not link across "and", "ibn", "bin", or "son of", and
that ignores entities named as relation labels, is follow-up work.
