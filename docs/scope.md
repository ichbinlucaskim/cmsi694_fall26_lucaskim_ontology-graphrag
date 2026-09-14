# Project scope

## In scope

- A narrow ontology of 10-20 classes, hand-checked against the corpus.
- Entity and relation extraction, run once over a frozen snapshot and spot-checked by hand.
- Hybrid retrieval: vector recall first, then graph expansion for precision.
- Evaluation on 50 hand-written questions with gold answers, against a plain vector RAG baseline.

## Out of scope

- Learning or inducing the ontology automatically.
- Real-time or incremental index updates.
- A user-facing web interface.

## Open questions

- Which domain gives a corpus that is rich enough but still small?
- How many traversal hops before precision falls off?
- What baseline does the graph path have to beat: plain vector RAG?
