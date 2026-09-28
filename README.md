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

## Running a condition

Prerequisites: the project virtual environment (`pip install -r requirements.txt`),
a running Ollama server with the models listed in `MODELS.md`, and the frozen
subset files:

```
python scripts/download_2wiki.py
python scripts/freeze_subset.py
```

Index the smoke subset, then answer its 10 questions:

```
python scripts/run_condition.py index --condition baseline --subset smoke10
python scripts/run_condition.py query --condition baseline --subset smoke10
```

`--subset` accepts `mini` (one question, for pipeline checks), `smoke10`,
`smoke20`, and `study50`. `--condition` names a file in `configs/conditions/`. Settings shared by
all conditions are in `configs/run_config.json`.

Indexing smoke10 (100 paragraphs) takes several hours on an M1 Mac. To keep the machine
awake and keep a log:

```
mkdir -p runs/baseline
caffeinate -i python scripts/run_condition.py index --condition baseline --subset smoke10 \
  2>&1 | tee -a runs/baseline/smoke10-index.log
```

**Resuming.** Rerun the same `index` command. Paragraphs already processed are
skipped, paragraphs left pending or interrupted are processed, and paragraphs
that failed are retried once. `query` refuses to run until every paragraph is
processed; `--allow-incomplete` overrides this and is recorded in the manifest.

**Outputs** go to `runs/<condition>/<subset>/`, which is git-ignored:

| Path | Contents |
|---|---|
| `lightrag/` | LightRAG working directory (graph, vector stores, LLM cache, document status) |
| `run_manifest.json` | One record per `index` or `query` invocation: timings, document status counts, failed IDs, token counts, config and subset hashes, model digests, versions, git commit |
| `results.jsonl` | One row per question: ID, type, question, gold answer, predicted answer, retrieved and gold paragraph IDs, query time |
