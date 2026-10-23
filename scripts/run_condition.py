"""Index a frozen 2WikiMultiHopQA subset and answer its questions (SCRUM-16).

One command per phase, for one experimental condition and one subset:

    python scripts/run_condition.py index --condition baseline --subset smoke10
    python scripts/run_condition.py query --condition baseline --subset smoke10
    python scripts/run_condition.py renormalize --condition baseline --subset smoke10

Settings shared by every condition come from configs/run_config.json; a
condition file, configs/conditions/<condition>.json, may add settings but not
redefine shared ones. Subsets are the frozen files from SCRUM-15, verified
against data/subsets/manifest.json before use. "mini" is the first smoke20
question and its own context paragraphs, for pipeline tests.

Outputs go to runs/<condition>/<subset>/ (git-ignored):
    lightrag/            LightRAG working directory
    run_manifest.json    one record per index or query invocation (session);
                         index_sessions and query_sessions count them
    results.jsonl        one row per question (query)

query replaces LightRAG's answer template (query.answer_template_key) with
query.answer_template from the shared config, for every condition, after
checking that both have the same placeholders. normalize_answer stays as a
fallback; the query record counts the rows it changed.

renormalize re-derives predicted_answer from the stored predicted_answer_raw
with the current normalize_answer rule, without model calls, and records which
rows changed.

index is resumable: documents already PROCESSED are skipped, documents left
PENDING or interrupted are picked up, and FAILED documents get one retry.
query is resumable too: each answered question's row is appended to
results.jsonl and flushed at once, and a re-run skips the question_ids already
in the file. It refuses to append when the rows already written have a
different shared-config sha256, index-settings sha256, seed, or LLM cache flag
(RESUME_KEYS, stored on every row), and says which differ. A question
interrupted mid-answer (Ctrl+C) is not written. To start a query run over,
move results.jsonl aside.
query refuses to run on an incomplete index unless --allow-incomplete is given.
index always uses the seed in the shared config. query --seed overrides it for
query-time LLM calls, and query --no-llm-cache bypasses LightRAG's LLM response
cache, whose keys do not include the seed; see MODELS.md, "Caching and seeds".
"""

import argparse
import asyncio
import hashlib
import json
import os
import re
import string
import subprocess
import sys
import time
import urllib.request
import uuid
from collections import Counter
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

import numpy as np
import ollama
from lightrag import LightRAG, QueryParam
from lightrag.base import DocStatus
from lightrag.kg.shared_storage import (
    commit_manual_retry_request,
    get_namespace_data,
    get_namespace_lock,
    get_pipeline_ingress,
)
from lightrag.llm.ollama import ollama_embed, ollama_model_complete
from lightrag.prompt import PROMPTS
from lightrag.utils import TokenTracker, wrap_embedding_func_with_attrs

import freeze_subset

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "configs" / "run_config.json"
CONDITIONS_DIR = ROOT / "configs" / "conditions"
RUNS_DIR = ROOT / "runs"
SUBSETS = ["mini", "smoke10", "smoke20", "study50"]
# Sections that determine the index. query refuses an index built with others.
INDEX_SECTIONS = ["ollama_host", "llm", "embedding", "indexing"]
# One trailing citation marker such as "[8]" or "[2, 3]", with leading space.
TRAILING_CITATION = re.compile(r"\s*\[\d+(?:\s*,\s*\d+)*\]\s*$")
# Where the answer ends: a blank line, or a References heading.
ANSWER_END = re.compile(r"\n[ \t]*\n|#+\s*References")
# A sentence boundary: a period, whitespace, then a capital letter.
SENTENCE_END = re.compile(r"\.\s+(?=[A-Z])")
NORMALIZE_RULE = (
    "keep text before the first blank line or '### References' heading; keep its "
    "first sentence (split on a period, whitespace, capital letter); then repeatedly "
    "strip trailing [n] / [n, m] markers, surrounding whitespace, and one trailing period"
)
# Stored on every result row; query appends only to rows that agree on all four.
RESUME_KEYS = ["config_sha256", "index_settings_sha256", "seed", "llm_cache"]
# Keys a condition file may add under "settings", and how they are applied.
CONDITION_KEYS = {"addon_params", "prompt_overrides"}


class SharedTokenTracker(TokenTracker):
    """TokenTracker that survives copy.deepcopy, so every copy counts here."""

    def __deepcopy__(self, memo):
        return self


def normalize_answer(raw: str) -> str:
    """Reduce a raw model answer to its short answer phrase; see NORMALIZE_RULE.

    "No\n\n### References\n- [1] X" -> "No"
    "Alexandra of Lithuania. She was the daughter of ..." -> "Alexandra of Lithuania"
    "Alexandra [8]." -> "Alexandra"
    """
    answer = ANSWER_END.split(raw.strip(), maxsplit=1)[0]
    answer = SENTENCE_END.split(answer, maxsplit=1)[0].strip()
    while True:
        cleaned = TRAILING_CITATION.sub("", answer).strip()
        if cleaned.endswith("."):
            cleaned = cleaned[:-1].strip()
        if cleaned == answer:
            return answer
        answer = cleaned


# ---------------------------------------------------------------- inputs


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_config(condition: str) -> tuple[dict, dict, dict]:
    """Return (shared config, condition file, provenance hashes)."""
    shared_raw = CONFIG_PATH.read_text(encoding="utf-8")
    shared = json.loads(shared_raw)
    condition_path = CONDITIONS_DIR / f"{condition}.json"
    if not condition_path.exists():
        raise SystemExit(f"No condition file: {condition_path.relative_to(ROOT)}")
    condition_raw = condition_path.read_text(encoding="utf-8")
    cond = json.loads(condition_raw)
    answer_key = shared["query"]["answer_template_key"]
    if answer_key in cond.get("settings", {}).get("prompt_overrides", {}):
        raise SystemExit(f"Condition overrides the shared answer template: {answer_key}")
    unknown = set(cond.get("settings", {})) - CONDITION_KEYS
    if unknown:
        raise SystemExit(f"Unsupported condition settings: {sorted(unknown)}")
    clashes = set(cond.get("settings", {})) & set(shared)
    if clashes:
        raise SystemExit(f"Condition redefines shared settings: {sorted(clashes)}")
    index_settings = {key: shared[key] for key in INDEX_SECTIONS}
    index_settings["condition_settings"] = cond.get("settings", {})
    hashes = {
        "config_sha256": sha256_text(shared_raw),
        "condition_config_sha256": sha256_text(condition_raw),
        "index_settings_sha256": sha256_text(json.dumps(index_settings, sort_keys=True)),
    }
    return shared, cond, hashes


def load_subset(name: str) -> tuple[list[dict], list[dict], dict]:
    """Load and verify a frozen subset; return questions, corpus, provenance."""
    manifest_raw = freeze_subset.MANIFEST_PATH.read_text(encoding="utf-8")
    manifest = json.loads(manifest_raw)
    source = "smoke20" if name == "mini" else name
    entry = manifest["subsets"][source]
    for file_name, digest in entry["files"].items():
        path = freeze_subset.PROCESSED_DIR / file_name
        if not path.exists() or freeze_subset.sha256_of(path) != digest:
            raise SystemExit(
                f"{path.relative_to(ROOT)} is missing or differs from the subset "
                "manifest; run scripts/freeze_subset.py"
            )
    q_file, c_file = freeze_subset.FILE_NAMES[source]
    questions = [json.loads(line) for line in (freeze_subset.PROCESSED_DIR / q_file).open()]
    corpus = [json.loads(line) for line in (freeze_subset.PROCESSED_DIR / c_file).open()]
    if [q["_id"] for q in questions] != entry["question_ids"]:
        raise SystemExit(f"{q_file} question order differs from the subset manifest")
    provenance = {
        "subset_manifest_sha256": sha256_text(manifest_raw),
        "source_subset": source,
        "files": entry["files"],
    }
    if name == "mini":
        questions = questions[:1]
        wanted = questions[0]["context_paragraph_ids"]
        by_id = {p["id"]: p for p in corpus}
        corpus = [by_id[pid] for pid in wanted]
        provenance["derivation"] = "first smoke20 question and its context paragraphs"
    return questions, corpus, provenance


# ------------------------------------------------------------ environment


def ollama_info(host: str, models: list[str]) -> dict:
    def get(path: str) -> dict:
        with urllib.request.urlopen(f"{host}{path}", timeout=10) as response:
            return json.load(response)

    tags = {m["name"]: m["digest"] for m in get("/api/tags")["models"]}
    missing = [m for m in models if m not in tags]
    if missing:
        raise SystemExit(f"Ollama models not installed: {missing}")
    return {
        "ollama_version": get("/api/version")["version"],
        "model_digests": {m: tags[m] for m in models},
    }


def git_info() -> dict:
    def git(*args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()

    return {"commit": git("rev-parse", "HEAD"), "dirty": bool(git("status", "--porcelain"))}


def env(shared: dict) -> dict:
    """Environment facts recorded on every invocation."""
    models = [shared["llm"]["model"], shared["embedding"]["model"]]
    return {
        "models": {"llm": models[0], "embedding": models[1]},
        **ollama_info(shared["ollama_host"], models),
        "lightrag_version": version("lightrag-hku"),
        "git": git_info(),
    }


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# --------------------------------------------------------------- manifest


def read_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def write_manifest(path: Path, manifest: dict) -> None:
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def start_record(manifest_path: Path, base: dict, phase: str, record: dict) -> tuple[dict, dict]:
    """Append a new invocation record (status "running") and persist it."""
    manifest = read_manifest(manifest_path)
    for key, value in base.items():
        manifest.setdefault(key, value)
    record = {"status": "running", "started_at": now(), **record}
    manifest.setdefault(phase, []).append(record)
    manifest[f"{phase}_sessions"] = len(manifest[phase])
    write_manifest(manifest_path, manifest)
    return manifest, record


# ----------------------------------------------------------------- LightRAG


def build_rag(
    shared: dict,
    cond: dict,
    working_dir: Path,
    llm_tracker,
    embed_tracker,
    llm_options: dict | None = None,
    enable_llm_cache: bool = True,
) -> LightRAG:
    """Build LightRAG from the config. llm_options replaces llm.options if given."""
    llm, emb, idx, ret = shared["llm"], shared["embedding"], shared["indexing"], shared["retrieval"]
    llm_options = llm["options"] if llm_options is None else llm_options
    host = shared["ollama_host"]
    settings = cond.get("settings", {})
    for key, value in settings.get("prompt_overrides", {}).items():
        if key not in PROMPTS:
            raise SystemExit(f"Unknown PROMPTS key in condition: {key}")
        if placeholders(value) != placeholders(PROMPTS[key]):
            raise SystemExit(f"Condition override of {key} changes its placeholders")
        PROMPTS[key] = value  # assign the key; never rebind PROMPTS

    @wrap_embedding_func_with_attrs(
        embedding_dim=emb["dim"], max_token_size=emb["max_token_size"], model_name=emb["model"]
    )
    async def embed(texts: list[str], **kwargs) -> np.ndarray:
        return await ollama_embed.func(
            texts,
            embed_model=emb["model"],
            host=host,
            options=emb["options"],
            token_tracker=embed_tracker,
            **kwargs,
        )

    return LightRAG(
        working_dir=str(working_dir),
        llm_model_func=ollama_model_complete,
        llm_model_name=llm["model"],
        # Every role (extract, keyword, query) inherits these kwargs, and the
        # Ollama binding forwards "options" verbatim to AsyncClient.chat.
        llm_model_kwargs={"host": host, "options": llm_options, "token_tracker": llm_tracker},
        enable_llm_cache=enable_llm_cache,
        llm_model_max_async=llm["max_async"],
        default_llm_timeout=llm["timeout_s"],
        embedding_func=embed,
        default_embedding_timeout=emb["timeout_s"],
        entity_extraction_use_json=idx["entity_extraction_use_json"],
        entity_extract_max_gleaning=idx["entity_extract_max_gleaning"],
        chunk_token_size=idx["chunk_token_size"],
        chunk_overlap_token_size=idx["chunk_overlap_token_size"],
        max_parallel_insert=idx["max_parallel_insert"],
        related_chunk_number=ret["related_chunk_number"],
        kg_chunk_pick_method=ret["kg_chunk_pick_method"],
        cosine_better_than_threshold=ret["cosine_better_than_threshold"],
        vector_db_storage_cls_kwargs={
            "cosine_better_than_threshold": ret["cosine_better_than_threshold"]
        },
        addon_params=settings.get("addon_params", {}),
    )


def placeholders(template: str) -> set[str]:
    return {field for _, field, _, _ in string.Formatter().parse(template) if field is not None}


def apply_answer_template(shared: dict) -> dict:
    """Replace LightRAG's answer template with the shared one; return provenance.

    Refuses a template whose placeholders differ from the installed one's.
    """
    key, template = shared["query"]["answer_template_key"], shared["query"]["answer_template"]
    if key not in PROMPTS:
        raise SystemExit(f"Unknown PROMPTS key for the answer template: {key}")
    original = PROMPTS[key]
    if placeholders(template) != placeholders(original):
        raise SystemExit(
            f"Answer template placeholders {sorted(placeholders(template))} differ from "
            f"LightRAG's {key} {sorted(placeholders(original))}"
        )
    PROMPTS[key] = template  # assign the key; never rebind PROMPTS
    return {
        "key": key,
        "placeholders": sorted(placeholders(template)),
        "template_sha256": sha256_text(template),
        "replaced_template_sha256": sha256_text(original),
    }


async def warm_up(shared: dict) -> float:
    """Load both models so timed phases exclude model load."""
    start = time.perf_counter()
    client = ollama.AsyncClient(host=shared["ollama_host"])
    await client.embed(
        model=shared["embedding"]["model"],
        input="warm-up",
        options=shared["embedding"]["options"],
    )
    await client.chat(
        model=shared["llm"]["model"],
        messages=[{"role": "user", "content": "Reply with OK."}],
        options={**shared["llm"]["options"], "num_predict": 4},
    )
    return round(time.perf_counter() - start, 1)


async def doc_records(rag: LightRAG, ids: list[str]) -> dict[str, dict]:
    # aget_docs_by_ids returns raw storage records (dicts) in 1.5.7.
    return await rag.aget_docs_by_ids(ids)


async def doc_statuses(rag: LightRAG, ids: list[str]) -> dict[str, str]:
    """Map each ID to its status value; IDs not in storage map to "missing"."""
    found = await doc_records(rag, ids)
    return {i: DocStatus(found[i]["status"]).value if i in found else "missing" for i in ids}


async def retry_failed(rag: LightRAG) -> None:
    """Grant FAILED documents one retry, as LightRAG's /reprocess_failed does."""
    pipeline_status = await get_namespace_data("pipeline_status", workspace=rag.workspace)
    lock = get_namespace_lock("pipeline_status", workspace=rag.workspace)
    ingress = await get_pipeline_ingress(rag.workspace)
    refusal = await commit_manual_retry_request(
        pipeline_status, lock, ingress, uuid.uuid4().hex, {}
    )
    if refusal:
        raise RuntimeError(f"LightRAG refused the retry request: {refusal}")
    await rag.apipeline_process_enqueue_documents()


def status_summary(statuses: dict[str, str]) -> dict:
    return {
        "status_counts": dict(Counter(statuses.values())),
        "failed_ids": sorted(i for i, s in statuses.items() if s == DocStatus.FAILED.value),
        "unfinished_ids": sorted(
            i for i, s in statuses.items()
            if s not in (DocStatus.PROCESSED.value, DocStatus.FAILED.value)
        ),
    }


# ---------------------------------------------------------------- results


def read_results(path: Path) -> list[dict]:
    """Rows already in a results file; refuse a torn last line or duplicate IDs."""
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    if text and not text.endswith("\n"):
        raise SystemExit(f"{path}: the last line is incomplete; remove it or move the file aside")
    rows = []
    for n, line in enumerate(text.splitlines(), start=1):
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            raise SystemExit(f"{path}: line {n} is not valid JSON") from None
    duplicates = sorted(q for q, c in Counter(r["question_id"] for r in rows).items() if c > 1)
    if duplicates:
        raise SystemExit(f"{path}: duplicate question_ids {duplicates}")
    return rows


def resume_mismatches(rows: list[dict], run_keys: dict) -> list[str]:
    """One line per RESUME_KEYS value on which written rows differ from this run."""
    out = []
    for key in RESUME_KEYS:
        mine = json.dumps(run_keys[key])
        theirs = sorted({json.dumps(r[key]) if key in r else "missing" for r in rows} - {mine})
        if theirs:
            out.append(f"{key}: file has {', '.join(theirs)}, this run has {mine}")
    return out


async def answer_questions(questions: list[dict], path: Path, run_keys: dict, answer,
                           progress: dict) -> None:
    """Answer the questions not yet in path, appending and flushing one row each.

    answer(question) is awaited for a row; run_keys are added to it. progress
    gets "already_answered" and a running "answered" count, so a caller can
    record them if this is interrupted.
    """
    rows = read_results(path)
    problems = resume_mismatches(rows, run_keys)
    if problems:
        raise SystemExit(
            f"Refusing to append to {path}: " + "; ".join(problems) + ". Rerun with the "
            "settings of the rows already written, or move the file aside to start over."
        )
    wanted = {q["_id"] for q in questions}
    strangers = sorted(r["question_id"] for r in rows if r["question_id"] not in wanted)
    if strangers:
        raise SystemExit(f"{path} has rows for questions not in this subset: {strangers}")
    done = {r["question_id"] for r in rows}
    progress.update(already_answered=len(done), answered=0)
    pending = [q for q in questions if q["_id"] not in done]
    print(f"{len(done)} of {len(questions)} questions already answered; {len(pending)} to go", flush=True)
    with path.open("a", encoding="utf-8", newline="\n") as f:
        for question in pending:
            row = await answer(question)
            # No await between here and the fsync, so a cancellation (Ctrl+C)
            # lands either before the row is written or after it is on disk.
            f.write(json.dumps({**row, **run_keys}, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())
            progress["answered"] += 1


# ------------------------------------------------------------------ phases


async def run_index(args, shared, cond, hashes, questions, corpus, provenance, base) -> int:
    run_dir = RUNS_DIR / args.condition / args.subset
    rag_dir = run_dir / "lightrag"
    rag_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = run_dir / "run_manifest.json"
    manifest, record = start_record(manifest_path, base, "index", {
        **hashes, **env(shared), "seed": shared["llm"]["options"].get("seed"),
    })

    llm_tracker, embed_tracker = SharedTokenTracker(), SharedTokenTracker()
    rag = build_rag(shared, cond, rag_dir, llm_tracker, embed_tracker)
    await rag.initialize_storages()
    try:
        ids = [p["id"] for p in corpus]
        before = await doc_statuses(rag, ids)
        new = [p for p in corpus if before[p["id"]] == "missing"]
        record["documents_total"] = len(ids)
        record["documents_already_processed"] = sum(s == "processed" for s in before.values())
        record["documents_enqueued"] = len(new)
        print(
            f"{len(ids)} documents: {record['documents_already_processed']} already processed, "
            f"{len(new)} new, "
            f"{sum(s not in ('processed', 'missing') for s in before.values())} to resume",
            flush=True,
        )
        needs_work = new or any(s not in ("processed", "missing") for s in before.values())
        if not needs_work:
            print("Nothing to do: every document is already processed.")
            record.update(status="completed", ended_at=now(), indexing_wall_s=0.0,
                          **status_summary(before))
            write_manifest(manifest_path, manifest)
            return 0

        record["warmup_s"] = await warm_up(shared)
        template = shared["indexing"]["document_text"]
        start = time.perf_counter()
        if new:
            await rag.ainsert(
                [template.format(title=p["title"], text=p["text"]) for p in new],
                ids=[p["id"] for p in new],
                file_paths=[p["title"] for p in new],
            )
        else:
            await rag.apipeline_process_enqueue_documents()
        first_pass = await doc_statuses(rag, ids)
        record["first_pass"] = status_summary(first_pass)

        if record["first_pass"]["failed_ids"]:
            print(f"Retrying {len(record['first_pass']['failed_ids'])} FAILED documents once", flush=True)
            await retry_failed(rag)
        wall = time.perf_counter() - start
        final = await doc_statuses(rag, ids)

        records = await doc_records(rag, ids)
        chunks_per_doc = [r.get("chunks_count") or 0 for r in records.values()]
        processed_now = sum(
            1 for i in ids if before[i] != "processed" and final[i] == "processed"
        )
        record.update(
            status="completed",
            ended_at=now(),
            indexing_wall_s=round(wall, 1),
            documents_processed_this_run=processed_now,
            seconds_per_processed_document=round(wall / processed_now, 1) if processed_now else None,
            max_chunks_per_document=max(chunks_per_doc, default=0),
            tokens={
                "method": (
                    "Ollama-reported prompt_eval_count and eval_count for every LLM and "
                    "embedding call actually sent in this invocation, collected with "
                    "LightRAG's token_tracker hook; LLM cache hits send no call and "
                    "count nothing."
                ),
                "llm": llm_tracker.get_usage(),
                "embedding": embed_tracker.get_usage(),
            },
            **status_summary(final),
        )
    except BaseException as exc:
        # Keep the tokens spent before the interruption; a resumed run does
        # not redo the documents this session finished.
        record.update(status="interrupted", ended_at=now(), error=repr(exc), tokens={
            "method": ("Ollama-reported counts via token_tracker for the calls sent before "
                       "the interruption; cache hits count nothing"),
            "llm": llm_tracker.get_usage(),
            "embedding": embed_tracker.get_usage(),
        })
        raise
    finally:
        write_manifest(manifest_path, manifest)
        await rag.finalize_storages()

    print(json.dumps({k: record[k] for k in (
        "indexing_wall_s", "documents_processed_this_run", "seconds_per_processed_document",
        "status_counts", "failed_ids", "unfinished_ids")}, indent=2))
    return 1 if record["failed_ids"] or record["unfinished_ids"] else 0


async def run_query(args, shared, cond, hashes, questions, corpus, provenance, base) -> int:
    run_dir = RUNS_DIR / args.condition / args.subset
    rag_dir = run_dir / "lightrag"
    manifest_path = run_dir / "run_manifest.json"
    manifest = read_manifest(manifest_path)
    completed = [r for r in manifest.get("index", []) if r.get("status") == "completed"]
    if not completed:
        raise SystemExit("No completed index run for this condition and subset; run index first.")
    index_hash = completed[-1]["index_settings_sha256"]
    settings_mismatch = index_hash != hashes["index_settings_sha256"]
    if settings_mismatch and not args.allow_settings_mismatch:
        raise SystemExit(
            "The index was built with different index settings; re-index into a fresh "
            "working directory, or pass --allow-settings-mismatch (recorded)."
        )

    seed = shared["llm"]["options"].get("seed") if args.seed is None else args.seed
    llm_options = {**shared["llm"]["options"], "seed": seed}
    llm_tracker, embed_tracker = SharedTokenTracker(), SharedTokenTracker()
    rag = build_rag(
        shared, cond, rag_dir, llm_tracker, embed_tracker,
        llm_options=llm_options, enable_llm_cache=not args.no_llm_cache,
    )
    answer_template = apply_answer_template(shared)
    await rag.initialize_storages()
    record = None
    try:
        statuses = await doc_statuses(rag, [p["id"] for p in corpus])
        summary = status_summary(statuses)
        incomplete = any(s != "processed" for s in statuses.values())
        if incomplete and not args.allow_incomplete:
            raise SystemExit(
                f"Index is incomplete ({summary['status_counts']}); "
                "finish indexing or pass --allow-incomplete."
            )
        results_path = run_dir / "results.jsonl"
        run_keys = {"config_sha256": hashes["config_sha256"],
                    "index_settings_sha256": hashes["index_settings_sha256"],
                    "seed": seed, "llm_cache": not args.no_llm_cache}
        # Refuse before recording a session or warming up, so a mismatch
        # leaves the manifest unchanged and costs no model call.
        problems = resume_mismatches(read_results(results_path), run_keys)
        if problems:
            raise SystemExit(f"Refusing to append to {results_path.relative_to(ROOT)}: "
                             + "; ".join(problems) + ". Rerun with the settings of the rows "
                             "already written, or move the file aside to start over.")
        manifest, record = start_record(manifest_path, base, "query", {
            **hashes,
            **env(shared),
            "seed": seed,
            "llm_cache": not args.no_llm_cache,
            "index_built_with_settings_sha256": index_hash,
            "allow_settings_mismatch": bool(args.allow_settings_mismatch),
            "settings_mismatch": settings_mismatch,
            "allow_incomplete": bool(args.allow_incomplete),
            "index_incomplete": incomplete,
            "index_status_counts": summary["status_counts"],
            "answer_template": answer_template,
        })
        q = shared["query"]
        progress = {"already_answered": 0, "answered": 0}
        session_failures, start = 0, time.perf_counter()
        total = len(questions)

        async def answer(question: dict) -> dict:
            nonlocal session_failures
            param = QueryParam(
                mode=q["mode"],
                top_k=q["top_k"],
                chunk_top_k=q["chunk_top_k"],
                max_entity_tokens=q["max_entity_tokens"],
                max_relation_tokens=q["max_relation_tokens"],
                max_total_tokens=q["max_total_tokens"],
                enable_rerank=q["enable_rerank"],
                response_type=q["response_type"],
                user_prompt=q["user_prompt"],
                disable_user_prompt_prefix=q["disable_user_prompt_prefix"],
                stream=False,
            )
            before = llm_tracker.get_usage()["total_tokens"]
            t0 = time.perf_counter()
            result = await rag.aquery_llm(question["question"], param=param)
            elapsed = time.perf_counter() - t0
            chunks = (result.get("data") or {}).get("chunks") or []
            chunk_ids = [c["chunk_id"] for c in chunks]
            chunk_records = await rag.text_chunks.get_by_ids(chunk_ids) if chunk_ids else []
            retrieved = list(dict.fromkeys(
                rec["full_doc_id"] for rec in chunk_records if rec and "full_doc_id" in rec
            ))
            text = (result.get("llm_response") or {}).get("content") or ""
            session_failures += result.get("status") != "success"
            n = progress["already_answered"] + progress["answered"] + 1
            print(f"[{n}/{total}] {question['_id']} {elapsed:.1f}s -> {text.strip()[:80]!r}", flush=True)
            return {
                "question_id": question["_id"],
                "type": question["type"],
                "question": question["question"],
                "gold_answer": question["answer"],
                "predicted_answer_raw": text,
                "predicted_answer": normalize_answer(text),
                "retrieved_paragraph_ids": retrieved,
                "gold_paragraph_ids": question["gold_paragraph_ids"],
                "query_status": result.get("status"),
                "query_message": result.get("message"),
                "retrieved_entities": len((result.get("data") or {}).get("entities") or []),
                "retrieved_relations": len((result.get("data") or {}).get("relationships") or []),
                "query_wall_s": round(elapsed, 2),
                "llm_tokens": llm_tracker.get_usage()["total_tokens"] - before,
            }

        def session(wall: float) -> dict:
            return {
                "ended_at": now(),
                "questions_already_answered": progress["already_answered"],
                "questions_answered": progress["answered"],
                "query_failures_this_session": session_failures,
                "query_wall_s": round(wall, 1),
                "mean_query_s": round(wall / progress["answered"], 2) if progress["answered"] else None,
                "tokens": {
                    "method": "as for index: Ollama-reported counts via token_tracker; cache hits count nothing",
                    "llm": llm_tracker.get_usage(),
                    "embedding": embed_tracker.get_usage(),
                },
            }

        try:
            record["warmup_s"] = await warm_up(shared)
            start = time.perf_counter()
            await answer_questions(questions, results_path, run_keys, answer, progress)
        except BaseException as exc:
            record.update(status="interrupted", error=repr(exc), **session(time.perf_counter() - start))
            raise
        rows = read_results(results_path)
        if [r["question_id"] for r in rows] != [x["_id"] for x in questions]:
            record.update(status="failed", error="results rows are not in subset order",
                          **session(time.perf_counter() - start))
            raise SystemExit(f"{results_path.relative_to(ROOT)} rows are not in subset order")
        failures = sum(r.get("query_status") != "success" for r in rows)
        fallback = [
            {"row": n, "question_id": row["question_id"],
             "raw": row["predicted_answer_raw"], "normalized": row["predicted_answer"]}
            for n, row in enumerate(rows, start=1)
            if row["predicted_answer"] != row["predicted_answer_raw"].strip()
        ]
        record.update(
            status="completed",
            **session(time.perf_counter() - start),
            questions=len(rows),
            query_failures=failures,
            results_file=str(results_path.relative_to(ROOT)),
            results_sha256=freeze_subset.sha256_of(results_path),
            normalization_fallback={
                "rule": NORMALIZE_RULE,
                "rows_changed": len(fallback),
                "changed": fallback,
            },
        )
    finally:
        if record is not None:
            write_manifest(manifest_path, manifest)
        await rag.finalize_storages()
    print(f"Wrote {results_path.relative_to(ROOT)}: {len(rows)} rows ({progress['answered']} this "
          f"session), {failures} failed queries, {len(fallback)} changed by the normalization fallback")
    return 1 if failures else 0


async def run_renormalize(args, shared, cond, hashes, questions, corpus, provenance, base) -> int:
    run_dir = RUNS_DIR / args.condition / args.subset
    results_path = run_dir / "results.jsonl"
    if not results_path.exists():
        raise SystemExit(f"No results to renormalize: {results_path.relative_to(ROOT)}")
    manifest_path = run_dir / "run_manifest.json"
    manifest, record = start_record(manifest_path, base, "renormalize", {
        "git": git_info(),
        "rule": NORMALIZE_RULE,
        "results_sha256_before": freeze_subset.sha256_of(results_path),
    })
    rows = [json.loads(line) for line in results_path.open(encoding="utf-8")]
    changed = []
    for n, row in enumerate(rows, start=1):
        after = normalize_answer(row["predicted_answer_raw"])
        if after != row["predicted_answer"]:
            changed.append({"row": n, "question_id": row["question_id"],
                            "before": row["predicted_answer"], "after": after})
            row["predicted_answer"] = after
    with results_path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    record.update(
        status="completed",
        ended_at=now(),
        rows=len(rows),
        rows_changed=len(changed),
        changed=changed,
        results_sha256_after=freeze_subset.sha256_of(results_path),
    )
    write_manifest(manifest_path, manifest)
    print(f"{len(changed)} of {len(rows)} rows changed")
    for c in changed:
        print(f"  row {c['row']} {c['question_id']}: {c['before']!r} -> {c['after']!r}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("phase", choices=["index", "query", "renormalize"])
    parser.add_argument("--condition", required=True)
    parser.add_argument("--subset", required=True, choices=SUBSETS)
    parser.add_argument(
        "--allow-incomplete", action="store_true",
        help="query: run even if some documents are not processed (recorded)",
    )
    parser.add_argument(
        "--allow-settings-mismatch", action="store_true",
        help="query: run even if the index was built with other index settings (recorded)",
    )
    parser.add_argument(
        "--seed", type=int, default=None,
        help="query: LLM seed for query-time calls (default: llm.options.seed in the config)",
    )
    parser.add_argument(
        "--no-llm-cache", action="store_true",
        help="query: bypass LightRAG's LLM response cache for this run (recorded)",
    )
    args = parser.parse_args()
    if args.phase != "query" and (
        args.seed is not None or args.no_llm_cache or args.allow_settings_mismatch
    ):
        parser.error("--seed, --no-llm-cache and --allow-settings-mismatch apply to query only")
    if args.phase != "query" and args.allow_incomplete:
        parser.error("--allow-incomplete applies to query only")

    shared, cond, hashes = load_config(args.condition)
    questions, corpus, provenance = load_subset(args.subset)
    base = {
        "condition": args.condition,
        "subset": args.subset,
        "subset_provenance": provenance,
        "question_count": len(questions),
        "paragraph_count": len(corpus),
    }
    phase = {"index": run_index, "query": run_query, "renormalize": run_renormalize}[args.phase]
    return asyncio.run(phase(args, shared, cond, hashes, questions, corpus, provenance, base))


if __name__ == "__main__":
    sys.exit(main())
