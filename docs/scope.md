# Project scope

## In scope

- A single domain ontology of 10-20 classes, hand-checked against the corpus.
- Entity and relation extraction, run once over a frozen snapshot.
- Retrieval that walks the graph first and falls back to vector search.
- Evaluation on 50 hand-written questions with gold answers.

## Out of scope

- Learning or inducing the ontology automatically.
- Real-time or incremental index updates.
- A user-facing web interface.

## Open questions

- Which domain gives a corpus that is rich enough but still small?
- How many traversal hops before precision falls off?
- What baseline does the graph path have to beat: plain vector RAG?
