# Ontology draft

First pass at the classes the graph will hold. Names are provisional.

## Classes

- **Document** — a source text as ingested, before chunking.
- **Chunk** — a passage of a Document, the unit that gets embedded.
- **Entity** — an abstract thing the corpus refers to; the parent of the classes below.
- **Person** — an Entity that is an individual human.
- **Organization** — an Entity that is a group with a name and a boundary.
- **Concept** — an Entity that is an idea rather than a thing in the world.
- **Event** — an Entity located in time.

## Properties

- Every Entity has a `label` and at least one `mention` pointing at a Chunk.
- Every Chunk has a `source` pointing at exactly one Document.
- Labels are not assumed unique; two Persons may share a name.

## Relations

Retrieval walks these, so each one needs a stated domain and range.

| Relation | Domain | Range | Notes |
|---|---|---|---|
| `mentions` | Chunk | Entity | The extraction step writes these. |
| `affiliated_with` | Person | Organization | May be time-bounded. |
| `participated_in` | Person | Event | Also holds for Organization; may need a supertype. |
| `broader_than` | Concept | Concept | Transitive, so traversal must cap depth. |
| `cites` | Document | Document | Only when the corpus carries real references. |

## Constraints

- `broader_than` must stay acyclic, or depth-capped traversal will loop.
- An Entity with no `mentions` edge is an extraction bug, not a valid node.
