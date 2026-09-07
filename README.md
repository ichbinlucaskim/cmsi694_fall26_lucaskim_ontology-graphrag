# cmsi694_fall26_lucaskim_ontology-graphrag

Course project for CMSI 694 (Fall 2026): an ontology-driven Graph RAG system.

## Idea

Classic RAG retrieves flat text chunks by vector similarity. This project adds an
explicit ontology layer so retrieval can walk typed entities and relationships
instead of guessing from embeddings alone.

## Planned pieces

- **Ontology** — the classes, properties, and constraints of the domain.
- **Graph store** — entities and relations extracted from the source corpus.
- **Retriever** — hybrid vector + graph traversal over the ontology.
- **Generator** — answer synthesis grounded in the retrieved subgraph.

## Status

Early scaffolding.
