# Graph metrics, smoke10 (SCRUM-21)

Written by `scripts/graph_metrics.py`, which documents every rule in its docstring. Each measure is shown with the counts behind it.

## Inputs

Ontology: `ontology/ontology.json` (sha256 `d0bb31142999…`).

| Graph | Run directory | GraphML sha256 |
|---|---|---|
| ontology v2 | `runs/ontology/smoke10` | `94795d48f171…` |

## Metrics

| Measure | ontology v2 |
|---|---|
| Entities | 524 |
| Relations | 421 |
| Entity-type conformance | 494 / 524 (94.3%) |
| Relation conformance | 343 / 421 (81.5%) |
| Relations with comma-joined keywords | 11 |
| Duplicate clusters | 17 |
| Entities in duplicate clusters | 34 |
| Duplicate rate | (34 - 17) / 524 (3.2%) |
| Flagged duplicate pairs | 17 |

The baseline prompt never showed the ontology, so the baseline's entity-type conformance reflects only how close LightRAG's default type names (person, organization, location, ...) are to the ontology's type names. It is not a measure of the baseline following the ontology.

## Entity types

ontology v2, all types: human 232, location 44, group 34, creativework 31, organization 27, film 27, date 23, other 20, award 16, country 13, occupation 12, event 9, settlementorregion 8, unknown 7, facility 4, product 3, musicalwork 3, writtenwork 3, educationalinstitution 2, publication 2, broadcastprogram 2, material 1, causeofdeath 1.

ontology v2, types outside the ontology: other 20, unknown 7, publication 2, material 1.

## Duplicate clusters

### ontology v2

- `Cabin by the Lake`; `Return to Cabin by the Lake`
- `Dazz Band`; `The Dazz Band`
- `Director of the Indian Intelligence Bureau`; `Indian Intelligence Bureau`
- `Earl of St. Albans`; `Ulick MacRichard Burke, 1st Marquess of Clanricarde, 5th Earl of Clanricarde, 2nd Earl of St Albans`
- `Fakhruddin Shaheed`; `Syedi Fakhruddin Shaheed`
- `Father's Place of Origin`; `Place of Origin`
- `Grammy Award`; `Grammy Award for Best R&B Performance by a Duo or Group with Vocals`
- `Joystick`; `Joystick (song)`
- `King Maha Chakkraphat`; `Maha Chakkraphat`
- `Mohammed Burhanuddin`; `Syedna Mohammed Burhanuddin`
- `Mother's Place of Birth`; `Place of Birth`
- `Panda`; `Panda (album)`
- `Siemowit III`; `Siemowit III of Masovia`
- `Swiss Passport`; `Swiss Passport Holder`
- `The Presidents of the United States of America`; `United States`
- `The Time`; `Time`
- `Victorian Football League`; `Victorian Football League (VFL)`

## Note

This report is for the ontology v2 smoke10 graph (SCRUM-18), indexed in the
story's own working directory at commit `19a76ff` and scored against the v2
ontology, which adds the Date type. The main repo's `runs/ontology/smoke10`
holds the v1 graph (GraphML sha256 `0385cb34ae14…`), reported in
`graph-metrics-smoke10.md`. The duplicate rule was hand-checked on the
baseline and v1 graphs only (precision 8/20); v2's pairs were not checked.
