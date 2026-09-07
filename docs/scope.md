# Project scope

## In scope

- A single domain ontology, small enough to hand-check (roughly 10-20 classes).
- Entity and relation extraction from a fixed text corpus.
- Retrieval that combines vector similarity with graph traversal.
- Evaluation on a hand-written question set with known answers.

## Out of scope

- Learning or inducing the ontology automatically.
- Real-time or incremental index updates.
- A user-facing web interface.

## Open questions

- Which domain gives a corpus that is rich enough but still small?
- How many traversal hops before precision falls off?
- What baseline does the graph path have to beat: plain vector RAG?
