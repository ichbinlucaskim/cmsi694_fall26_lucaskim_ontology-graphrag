"""Index 5 2WikiMultiHopQA paragraphs with LightRAG on Ollama (SCRUM-14, AC1).

Draws 5 distinct context paragraphs from the dev split with a fixed seed,
inserts them into a fresh LightRAG working directory under runs/, and reports
the resulting graph: entity and relation counts, 5 example relations, and the
wall-clock time of the insert. Exits non-zero if any document fails.

Models and context sizes are recorded in MODELS.md. Requires a running Ollama
server with the models below pulled.

Usage:
    python scripts/lightrag_smoke.py

Run scripts/download_2wiki.py first.
"""

import asyncio
import json
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import ollama
from lightrag import LightRAG
from lightrag.base import DocStatus
from lightrag.llm.ollama import ollama_embed, ollama_model_complete
from lightrag.utils import wrap_embedding_func_with_attrs

ROOT = Path(__file__).resolve().parent.parent
DEV_PATH = ROOT / "data" / "raw" / "2wiki" / "dev.json"
RUNS_DIR = ROOT / "runs" / "lightrag_smoke"

OLLAMA_HOST = "http://localhost:11434"
LLM_MODEL = "qwen2.5:7b-instruct"
EMBED_MODEL = "bge-m3:latest"
EMBED_DIM = 1024
# LightRAG docs (docs/ProgramingWithCore.md, "Increasing context size"):
# "LightRAG requires at least 32k context tokens. Ollama defaults to 8k."
LLM_NUM_CTX = 32768
# env.example ships OLLAMA_EMBEDDING_NUM_CTX=8192; also bge-m3's native limit.
EMBED_NUM_CTX = 8192
# The Ollama server runs with OLLAMA_NUM_PARALLEL=1, so concurrent LLM calls
# only queue server-side and run into LightRAG's per-call timeout.
LLM_MAX_ASYNC = 1
# LightRAG's default is 30 s (60 s worker). On a 16 GB M1 with the LLM
# resident, a cold bge-m3 load can take longer than that.
EMBED_TIMEOUT_S = 180

SEED = 694
NUM_PARAGRAPHS = 5
NUM_EXAMPLES = 5


def sample_paragraphs() -> list[tuple[str, str]]:
    """Return NUM_PARAGRAPHS distinct (title, text) paragraphs, seeded."""
    with DEV_PATH.open(encoding="utf-8") as f:
        dev = json.load(f)
    # Dict keeps first-seen order, so the pool is deterministic for a given file.
    pool: dict[tuple[str, str], None] = {}
    for example in dev:
        for title, sentences in example["context"]:
            pool[(title, " ".join(sentences))] = None
    rng = random.Random(SEED)
    return rng.sample(list(pool), NUM_PARAGRAPHS)


@wrap_embedding_func_with_attrs(
    embedding_dim=EMBED_DIM, max_token_size=EMBED_NUM_CTX, model_name=EMBED_MODEL
)
async def embed(texts: list[str], **kwargs) -> np.ndarray:
    return await ollama_embed.func(
        texts,
        embed_model=EMBED_MODEL,
        host=OLLAMA_HOST,
        options={"num_ctx": EMBED_NUM_CTX},
        **kwargs,
    )


async def warm_up() -> None:
    """Load both models into Ollama so the indexing time excludes model load."""
    client = ollama.AsyncClient(host=OLLAMA_HOST)
    await client.embed(
        model=EMBED_MODEL, input="warm-up", options={"num_ctx": EMBED_NUM_CTX}
    )
    await client.chat(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": "Reply with OK."}],
        options={"num_ctx": LLM_NUM_CTX, "num_predict": 4},
    )


async def main() -> int:
    paragraphs = sample_paragraphs()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    working_dir = RUNS_DIR / run_id
    working_dir.mkdir(parents=True)

    print(f"== Sample: {NUM_PARAGRAPHS} paragraphs, seed={SEED} ==")
    for i, (title, text) in enumerate(paragraphs):
        print(f"[{i}] {title} ({len(text.split())} words)")
    print(f"\nWorking dir: {working_dir.relative_to(ROOT)}")
    print(f"LLM: {LLM_MODEL} (num_ctx={LLM_NUM_CTX})")
    print(f"Embedding: {EMBED_MODEL} (dim={EMBED_DIM}, num_ctx={EMBED_NUM_CTX})")

    start = time.perf_counter()
    await warm_up()
    print(f"Model warm-up: {time.perf_counter() - start:.1f} s")

    rag = LightRAG(
        working_dir=str(working_dir),
        llm_model_func=ollama_model_complete,
        llm_model_name=LLM_MODEL,
        llm_model_kwargs={"host": OLLAMA_HOST, "options": {"num_ctx": LLM_NUM_CTX}},
        llm_model_max_async=LLM_MAX_ASYNC,
        embedding_func=embed,
        default_embedding_timeout=EMBED_TIMEOUT_S,
    )
    await rag.initialize_storages()
    try:
        ids = [f"2wiki-smoke-{i}" for i in range(NUM_PARAGRAPHS)]
        start = time.perf_counter()
        await rag.ainsert(
            [f"{title}\n{text}" for title, text in paragraphs],
            ids=ids,
            file_paths=[title for title, _ in paragraphs],
        )
        elapsed = time.perf_counter() - start

        statuses = await rag.aget_docs_by_ids(ids)
        nodes = await rag.chunk_entity_relation_graph.get_all_nodes()
        edges = await rag.chunk_entity_relation_graph.get_all_edges()
    finally:
        await rag.finalize_storages()

    print("\n== Document status ==")
    failed = 0
    for doc_id in ids:
        # aget_docs_by_ids is annotated as returning DocProcessingStatus, but
        # in 1.5.7 it passes through the raw storage record (a dict).
        status = statuses.get(doc_id)
        if status is None:
            print(f"{doc_id}: missing")
            failed += 1
            continue
        print(f"{doc_id}: {status['status']}")
        if status["status"] != DocStatus.PROCESSED.value:
            failed += 1
            if status.get("error_msg"):
                print(f"  error: {status['error_msg']}")

    print("\n== Graph ==")
    print(f"Entities: {len(nodes)}")
    print(f"Relations: {len(edges)}")
    print(f"Indexing wall-clock: {elapsed:.1f} s")

    print(f"\n== {min(NUM_EXAMPLES, len(edges))} example relations ==")
    for edge in edges[:NUM_EXAMPLES]:
        print(f"{edge['source']} -- [{edge.get('keywords', '')}] -- {edge['target']}")
        print(f"  {edge.get('description', '')}")

    if failed or not nodes or not edges:
        print(f"\nFAIL: {failed} failed documents, {len(nodes)} entities, {len(edges)} relations")
        return 1
    print("\nOK")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
