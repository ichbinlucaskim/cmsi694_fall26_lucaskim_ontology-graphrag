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
