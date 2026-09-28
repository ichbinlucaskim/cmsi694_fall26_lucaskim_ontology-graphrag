# Models and runtime

Model and runtime configuration shared by all experimental conditions.
Established in SCRUM-14; update this file whenever any value changes.

## Models

| Role | Ollama name | Ollama digest | Parameters | Quantization | Native context |
|---|---|---|---|---|---|
| Extraction and generation | `qwen2.5:7b-instruct` | `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e` | 7.6B | Q4_K_M | 32,768 |
| Embeddings | `bge-m3:latest` | `7907646426070047a77226ac3e684fbbe8410524f7b4a74d02837e43f2146bab` | 566.70M | F16 | 8,192 |

Digests are from `GET /api/tags`. The embedding dimension is 1,024.

Selection rationale: `qwen2.5:7b-instruct` is the installed Qwen-family
instruct model in the 7B-8B class. `bge-m3` is the preferred embedding model
and the default of LightRAG's Ollama embedding binding (`ollama_embed`).

## Software

| Component | Version |
|---|---|
| Ollama (server and CLI, macOS app) | 0.34.3 |
| `lightrag-hku` | 1.5.7 (GitHub tag `v1.5.7`, released 2026-09-02) |
| `ollama` (Python client) | 0.6.2 |
| Python | 3.11.9 |

Python packages are pinned in `requirements.txt`.

## Runtime settings

The settings used for experimental runs are in `configs/run_config.json`,
which is shared by every condition and hashed into every run manifest. The
table below explains each value; the config file is authoritative.

| Setting | Value | Source |
|---|---|---|
| LLM `num_ctx` | 32,768 | LightRAG `docs/ProgramingWithCore.md`: "LightRAG requires at least 32k context tokens. Ollama defaults to 8k." Also equal to the model's native context. |
| LLM `num_predict` | 4,096 | Output cap against runaway generation (SCRUM-29 D7). The largest SCRUM-29 D4 extraction output was about 1,194 tokens, for a 315-token paragraph. Scaled to the largest smoke20 paragraph (692 tokens), that is about 2,600 tokens. The cap is 1.6 times that. A capped response is flagged as truncated, parsed as far as it goes, and not cached (`lightrag/utils.py:4875-4889`). |
| LLM timeout | 600 s | Must exceed a capped call: 4,096 tokens at about 10 tokens/s plus about 20 s of prompt evaluation is about 430 s. LightRAG's default of 240 s would cut a legitimate long extraction. |
| Embedding `num_ctx` | 8,192 | LightRAG `env.example`: `OLLAMA_EMBEDDING_NUM_CTX=8192`. Also bge-m3's native context. |
| `llm_model_max_async` | 1 | The Ollama server runs with `OLLAMA_NUM_PARALLEL=1`; at LightRAG's default of 4, requests queued server-side for over 3 minutes. |
| `default_embedding_timeout` | 180 s | LightRAG's default of 30 s (60 s worker limit) aborted a cold bge-m3 load while the LLM was resident. |
| Entity extraction mode | JSON (`entity_extraction_use_json=True`) | SCRUM-29: the delimiter text format produced run-together names with qwen2.5; JSON mode did not. |
| Gleaning passes | 0 (`entity_extract_max_gleaning=0`) | SCRUM-29 D4: halves extraction calls. Its effect on quality was not measured. |
| `max_parallel_insert` | 1 | Documents are merged in a fixed order across repeats; LLM calls are serialized anyway. |
| Query mode | `hybrid` | Retrieves only through the knowledge graph (entities and relations, then their source chunks). The default, `mix`, also adds plain vector search over chunks (`operate.py:5280`), which would be identical across conditions and dilute the effect of the graph. |
| Answer format | `response_type` and `user_prompt` in `configs/run_config.json` | Supported `QueryParam` fields filled into LightRAG's `rag_response` prompt. `disable_user_prompt_prefix=True` keeps any server-side prefix out. The user prompt forbids citation markers, because a seeded mini run answered `Alexandra of Lithuania [8]`. |
| Answer normalization | `predicted_answer` = normalized `predicted_answer_raw` | `results.jsonl` keeps the exact model output as `predicted_answer_raw`. `predicted_answer` is derived from it by `normalize_answer` in `scripts/run_condition.py`, in three steps: (1) keep the text before the first blank line or `### References` heading; (2) keep only its first sentence, splitting on a period followed by whitespace and a capital letter; (3) repeatedly remove, from the end only, a citation marker (`[n]` or `[n, m, ...]`), surrounding whitespace, and one trailing period, until nothing changes. Examples: `No\n\n### References ...` becomes `No`; `Alexandra of Lithuania. She was ...` becomes `Alexandra of Lithuania`; `Alexandra [8].` becomes `Alexandra`. Case and inner punctuation are kept. Known limit: step 2 would cut an answer at an abbreviation followed by a capitalized word (`St. Louis` becomes `St`). `run_condition.py renormalize` re-derives the column for stored results without model calls. The answer template is replaced at the source in SCRUM-30. |
| Sampling | Ollama defaults, plus `seed` 694 | No temperature or other sampling option is set; this is what SCRUM-29 tested. The seed is in `llm.options`; `run_condition.py query --seed` overrides it for query-time calls only. |

The SCRUM-14 smoke run used text mode, gleaning 1, and no output cap; those
settings are superseded by the table above.

Context sizes are passed per request, not baked into a Modelfile, through
`llm_model_kwargs["options"]` and the embedding call's `options`. See
`scripts/run_condition.py`.

LightRAG's documentation recommends an LLM of "at least 32B parameters, 32KB
context (64KB recommended)" for indexing. The 7B model meets the context
requirement but not the parameter recommendation.

## Caching and seeds

Findings from the installed `lightrag-hku==1.5.7` source. Paths are relative to
the `lightrag/` package.

**Query-time calls are cached, by default.**

- `enable_llm_cache` defaults to `True` (`lightrag.py:791`).
- `handle_cache` consults it for every query-mode lookup (`utils.py:4160-4162`).
  Both the answer cache (`operate.py:4765`) and the keyword cache
  (`operate.py:5010`) go through it.
- Writes are guarded by the same flag: answers at `operate.py:4786-4789`,
  keywords at `operate.py:5061`.
- Extraction and description-summary calls use the separate flag
  `enable_llm_cache_for_entity_extract` (`lightrag.py:794`,
  `utils.py:4163-4165`), which also defaults to `True`.

**No cache key contains Ollama options, including the seed.**

| Call | Key fields | Location |
|---|---|---|
| Extraction and summaries | User prompt, system prompt, history, `response_format`, and the role identity (role, binding, model, host) | `utils.py:5233-5250`; identity at `lightrag.py:1237-1250` |
| Query answer | Cache policy version, mode, query, `response_type`, `top_k`, `chunk_top_k`, the three token budgets, high- and low-level keywords, the effective user prompt, `enable_rerank`, `enable_content_headings`, and the role identity | `operate.py:4737-4761` |
| Query keywords | Mode, query text, language, and the role identity | `operate.py:5001-5007` |

`num_ctx`, `num_predict`, `seed`, and any other `options` value are never
hashed.

**Consequences:**

- **Query repeats (SCRUM-22).** A repeat that changes only `--seed` would hit
  the cached keywords and the cached answer from the first run. It would return
  the same answer without calling the model. Repeats must run with
  `enable_llm_cache=False`, which `run_condition.py query --no-llm-cache` sets
  for that run and records in the manifest. Truncated responses are never
  cached (`operate.py:4789`).
- **Re-indexing with a different seed.** This must use a fresh working
  directory. The old directory's extraction cache would return the earlier
  outputs for identical prompts, and `run_condition.py index` also skips
  documents that are already processed.

## Machine

| Item | Value |
|---|---|
| Chip | Apple M1 |
| Memory | 16 GiB (17,179,869,184 bytes) |
| GPU memory visible to Ollama | 11.8 GiB (Metal) |
| macOS | 26.5.1 (build 25F80) |

## Reference timing

**Current reference: baseline smoke10 index** (SCRUM-16, run 2026-09-28,
commit `7ac0e59`, `configs/run_config.json` as committed there; details in
`docs/results/baseline-smoke10.md`).

| Measure | Value |
|---|---|
| Paragraphs | 100 (mean 65.5 words) |
| Indexing wall-clock | 5,383.3 s |
| Seconds per paragraph | **53.8** |
| Result | 100/100 processed, 0 failed |
| LLM tokens (Ollama-reported) | 189,225 prompt + 50,373 completion, 100 calls |

**Projection for study50 at 53.8 s per paragraph:** 427 paragraphs gives
22,973 s, about 6.4 h per condition.

The projection is a rough guide. The rate depends mostly on how much each
extraction generates. smoke10 averaged about 504 completion tokens per call,
and the unseeded 10-paragraph mini run averaged about 923, which took 117.8 s
per paragraph. Treat 54 to 118 s per paragraph as the observed range.

Earlier measurements, kept for history:

| Run | Configuration | Seconds per paragraph |
|---|---|---|
| SCRUM-14 smoke (`scripts/lightrag_smoke.py`, 5 paragraphs) | text mode, gleaning 1, no output cap | 106.0 |
| SCRUM-29 D4 (5 paragraphs) | JSON mode, gleaning 0 | 74.3 |
| SCRUM-16 mini (10 paragraphs) | current configuration, no seed | 117.8 |
