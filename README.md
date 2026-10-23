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
`query` resumes the same way: each answer is appended to `results.jsonl` as
soon as it is made, and a rerun skips questions already in the file. It
refuses to append if the rows already written used a different shared config,
index settings, seed, or LLM cache setting, and names what differs. A question
interrupted mid-answer is not written. To start a query over, move
`results.jsonl` aside.

**Outputs** go to `runs/<condition>/<subset>/`, which is git-ignored:

| Path | Contents |
|---|---|
| `lightrag/` | LightRAG working directory (graph, vector stores, LLM cache, document status) |
| `run_manifest.json` | One record per `index` or `query` invocation (session), counted in `index_sessions` and `query_sessions`: timings, document status counts, failed IDs, token counts, config and subset hashes, model digests, versions, git commit |
| `results.jsonl` | One row per question: ID, type, question, gold answer, predicted answer, retrieved and gold paragraph IDs, query time, and the config sha256, index-settings sha256, seed, and cache flag it was answered with |
| `scores.json` | Written by `scripts/score.py`: per-question and aggregate scores |

## Scoring a run

```
python scripts/score.py --condition baseline --subset smoke10
```

This scores `runs/<condition>/<subset>/results.jsonl` with the official
2WikiMultiHopQA v1.1 answer metrics (EM and F1, with and without answer
aliases) and retrieval recall, and adds bootstrap 95% confidence intervals
overall and per question type. It writes `runs/<condition>/<subset>/scores.json`
and a summary in `docs/results/<condition>-<subset>-scores.md`. It needs
`data/raw/2wiki/id_aliases.json` from `scripts/download_2wiki.py` and uses the
standard library only.

Tests:

```
python -m unittest discover -s tests
```

## Ontology

```
python scripts/derive_ontology.py
python scripts/derive_ontology.py --offline
python scripts/derive_ontology.py --check
```

This derives the treatment ontology, `ontology/ontology.json` (19 entity
types, 34 relation types), from the Wikidata property constraints of the
2Wiki relations. It also writes `ontology/derivation_report.json`, which
holds the validation and relation-coverage results. Wikidata responses are cached in
`data/raw/wikidata/` (git-ignored). `--offline` writes both files from the
cache only. `--check` regenerates them from the cache, also without network
calls, and fails if they differ. The decisions and
collapsing rules are in `docs/notes/ontology-decisions.md`.

## Ontology condition

The `ontology` condition is the baseline with the ontology rendered into the
JSON-mode extraction prompts: entity types through
`addon_params["entity_types_guidance"]`, and relation types through overrides
of `entity_extraction_json_system_prompt` and
`entity_extraction_json_user_prompt`. Every other setting, including the
answer template, comes from the shared `configs/run_config.json`.
`configs/conditions/ontology.json` is generated; do not edit it by hand.

```
python scripts/ontology_prompt.py --write-condition    # after any change to ontology/ontology.json
python scripts/ontology_prompt.py --check
python scripts/render_extraction_prompts.py            # prompts for one chunk, and their diff
```

`render_extraction_prompts.py` saves both conditions' prompts for one smoke10
chunk in `docs/results/prompts/`, and their unified diff in
`docs/results/prompt-diff-baseline-vs-ontology.diff`.

Index and query, as for the baseline:

```
python scripts/run_condition.py index --condition ontology --subset mini
caffeinate -i python scripts/run_condition.py index --condition ontology --subset smoke10 \
  2>&1 | tee -a runs/ontology/smoke10-index.log
python scripts/run_condition.py query --condition ontology --subset smoke10
```

Relation conformance is the share of graph relations whose keywords are exactly
one ontology relation label after normalization (lowercase, underscores to
spaces, collapsed whitespace). The rule is documented in the script.

```
python scripts/relation_conformance.py --condition ontology --subset smoke10
```

Score the ontology run and compare it with the baseline. The comparison reads
both runs' `scores.json`, so score each condition first:

```
python scripts/score.py --condition ontology --subset smoke10
python scripts/compare_conditions.py --baseline baseline --treatment ontology --subset smoke10
```

The comparison is written to `docs/results/ontology-vs-baseline-smoke10.md`.
