# Project scope

## In scope

- One narrow ontology, kept deliberately small so errors stay visible.
- Extraction of entities and relations, with a human spot-check pass.
- Hybrid retrieval: vector recall first, then graph expansion for precision.
- Evaluation against a baseline of plain vector RAG on the same questions.

## Out of scope

- Learning or inducing the ontology automatically.
- Real-time or incremental index updates.
- A user-facing web interface.

## Open questions

- Which domain gives a corpus that is rich enough but still small?
- How many traversal hops before precision falls off?
- What baseline does the graph path have to beat: plain vector RAG?
