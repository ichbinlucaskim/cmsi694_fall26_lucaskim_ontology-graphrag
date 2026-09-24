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

| Setting | Value | Source |
|---|---|---|
| LLM `num_ctx` | 32,768 | LightRAG `docs/ProgramingWithCore.md`: "LightRAG requires at least 32k context tokens. Ollama defaults to 8k." Also equal to the model's native context. |
| Embedding `num_ctx` | 8,192 | LightRAG `env.example`: `OLLAMA_EMBEDDING_NUM_CTX=8192`. Also bge-m3's native context. |
| `llm_model_max_async` | 1 | The Ollama server runs with `OLLAMA_NUM_PARALLEL=1`; at LightRAG's default of 4, requests queued server-side for over 3 minutes. |
| `default_embedding_timeout` | 180 s | LightRAG's default of 30 s (60 s worker limit) aborted a cold bge-m3 load while the LLM was resident. |
| Entity extraction mode | text (delimiter) | LightRAG default, `entity_extraction_use_json=False` |
| Gleaning passes | 1 | LightRAG default, `DEFAULT_MAX_GLEANING` |

Context sizes are passed per request, not baked into a Modelfile:
`llm_model_kwargs={"options": {"num_ctx": 32768}}` and
`options={"num_ctx": 8192}` on each embedding call. See
`scripts/lightrag_smoke.py`.

LightRAG's documentation recommends an LLM of "at least 32B parameters, 32KB
context (64KB recommended)" for indexing. The 7B model meets the context
requirement but not the parameter recommendation.

## Machine

| Item | Value |
|---|---|
| Chip | Apple M1 |
| Memory | 16 GiB (17,179,869,184 bytes) |
| GPU memory visible to Ollama | 11.8 GiB (Metal) |
| macOS | 26.5.1 (build 25F80) |

## Reference timing

`scripts/lightrag_smoke.py`, run 2026-09-23 (`runs/lightrag_smoke/20260923T235035Z`):
5 paragraphs from the 2WikiMultiHopQA dev split, seed 694, 358 words in total.

| Measure | Value |
|---|---|
| Indexing wall-clock (`ainsert`, 5 paragraphs) | 529.9 s |
| Model warm-up before indexing (not included above) | 22.3 s |
| Result | 5/5 documents processed; 47 entities, 24 relations |

At about 106 s per paragraph, indexing is the dominant cost of an experimental
run on this machine.
