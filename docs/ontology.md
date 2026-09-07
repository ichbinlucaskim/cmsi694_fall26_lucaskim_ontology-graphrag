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
