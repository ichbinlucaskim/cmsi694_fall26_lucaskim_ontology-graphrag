"""Diagnose LightRAG extraction quality on one paragraph (spike, D2-D3).

D2 sends a plain question to qwen2.5:7b-instruct with default options and with
the smoke run's options. D3 rebuilds the exact extraction prompts LightRAG sent
for one smoke-run chunk, checks them byte for byte against the prompt stored in
the smoke run's LLM cache, and sends them straight to Ollama in several
variants. Every call is recorded with Ollama's timing counters; outputs are
parsed with LightRAG's own parsers.

Outputs go to runs/diagnosis/. Requires the smoke run from SCRUM-14.

Usage:
    python scripts/diagnose_extraction.py d2
    python scripts/diagnose_extraction.py d3
    python scripts/diagnose_extraction.py d6
"""

import argparse
import asyncio
import json
import time
from pathlib import Path

import ollama
from lightrag.constants import (
    DEFAULT_MAX_EXTRACTION_ENTITIES,
    DEFAULT_MAX_EXTRACTION_RECORDS,
    DEFAULT_SUMMARY_LANGUAGE,
)
from lightrag.operate import (
    _process_extraction_result,
    _process_json_extraction_result,
)
from lightrag.prompt import PROMPTS, get_default_entity_extraction_prompt_profile
from lightrag.utils import sanitize_text_for_encoding

ROOT = Path(__file__).resolve().parent.parent
SMOKE_DIR = ROOT / "runs" / "lightrag_smoke" / "20260923T235035Z"
CHUNK_ID = "2wiki-smoke-1-chunk-000"  # [1] Christiane Wartenberg
CACHE_KEY = "default:extract:72105fa8f9b3ffbba241d34c154728ef"
OUT_DIR = ROOT / "runs" / "diagnosis"

OLLAMA_HOST = "http://localhost:11434"
QWEN = "qwen2.5:7b-instruct"
LLAMA = "llama3.1:latest"
# Exactly what the smoke run sent: llm_model_kwargs options, nothing else
# (extraction passes no max_tokens, so no num_predict is added).
SMOKE_OPTIONS = {"num_ctx": 32768}
ALT_DELIMITER = " | "
# D6: keeps LightRAG's documented <|UPPER_CASE_STRING|> form (prompt.py:13).
SEP_DELIMITER = "<|SEP|>"


def build_prompts(content: str, use_json: bool) -> tuple[str, str]:
    """Format the extraction prompts the way operate.extract_entities does."""
    profile = get_default_entity_extraction_prompt_profile()
    common = dict(
        entity_types_guidance=profile["entity_types_guidance"],
        language=DEFAULT_SUMMARY_LANGUAGE,
        max_total_records=DEFAULT_MAX_EXTRACTION_RECORDS,
        max_entity_records=DEFAULT_MAX_EXTRACTION_ENTITIES,
    )
    if use_json:
        context = dict(
            common, examples="\n".join(profile["entity_extraction_json_examples"])
        )
        system = PROMPTS["entity_extraction_json_system_prompt"].format(**context)
        user = PROMPTS["entity_extraction_json_user_prompt"].format(
            **context, input_text=content, heading_context_block=""
        )
        return sanitize_text_for_encoding(system), sanitize_text_for_encoding(user)
    delimiters = dict(
        tuple_delimiter=PROMPTS["DEFAULT_TUPLE_DELIMITER"],
        completion_delimiter=PROMPTS["DEFAULT_COMPLETION_DELIMITER"],
    )
    examples = "\n".join(profile["entity_extraction_examples"]).format(
        **delimiters,
        entity_types_guidance=common["entity_types_guidance"],
        language=common["language"],
    )
    context = dict(common, **delimiters, examples=examples)
    system = PROMPTS["entity_extraction_system_prompt"].format(**context)
    user = PROMPTS["entity_extraction_user_prompt"].format(
        **context, input_text=content, heading_context_block=""
    )
    # use_llm_func_with_cache sends the sanitized strings (utils.py:5214-5217),
    # which strips surrounding whitespace.
    return sanitize_text_for_encoding(system), sanitize_text_for_encoding(user)


def chat(model: str, messages: list[dict], options: dict | None, fmt=None) -> dict:
    """One non-streaming chat call; returns output plus Ollama's counters."""
    client = ollama.Client(host=OLLAMA_HOST)
    start = time.perf_counter()
    kwargs = {"model": model, "messages": messages, "stream": False}
    if options is not None:
        kwargs["options"] = options
    if fmt is not None:
        kwargs["format"] = fmt
    response = client.chat(**kwargs)
    wall = time.perf_counter() - start
    return {
        "model": model,
        "options": options,
        "format": fmt,
        "wall_s": round(wall, 2),
        "total_duration_s": round(response["total_duration"] / 1e9, 2),
        "load_duration_s": round(response["load_duration"] / 1e9, 2),
        "prompt_eval_count": response["prompt_eval_count"],
        "prompt_eval_duration_s": round(response["prompt_eval_duration"] / 1e9, 2),
        "eval_count": response["eval_count"],
        "eval_duration_s": round(response["eval_duration"] / 1e9, 2),
        "output": response["message"]["content"],
    }


def parse(output: str, use_json: bool, delimiter: str) -> dict:
    """Parse with LightRAG's own parser and summarize entity names."""
    if use_json:
        nodes, edges = asyncio.run(
            _process_json_extraction_result(output, CHUNK_ID, 0, CHUNK_ID)
        )
    else:
        nodes, edges = asyncio.run(
            _process_extraction_result(
                output,
                CHUNK_ID,
                0,
                CHUNK_ID,
                tuple_delimiter=delimiter,
                completion_delimiter=PROMPTS["DEFAULT_COMPLETION_DELIMITER"],
            )
        )
    names = sorted(nodes)
    return {
        "entities_parsed": sum(len(v) for v in nodes.values()),
        "relations_parsed": sum(len(v) for v in edges.values()),
        "entity_names": names,
        "names_with_space": sum(" " in n for n in names),
        "entity_types": sorted({d["entity_type"] for v in nodes.values() for d in v}),
    }


def run_d2() -> list[dict]:
    messages = [
        {"role": "user", "content": "In one sentence, who was Alfonso VII of León?"}
    ]
    results = []
    for label, options in (("default options", None), ("smoke options", SMOKE_OPTIONS)):
        result = chat(QWEN, messages, options)
        result["label"] = label
        results.append(result)
    return results


def run_d3() -> list[dict]:
    chunks = json.loads((SMOKE_DIR / "kv_store_text_chunks.json").read_text())
    cache = json.loads((SMOKE_DIR / "kv_store_llm_response_cache.json").read_text())
    content = chunks[CHUNK_ID]["content"]

    system, user = build_prompts(content, use_json=False)
    # use_llm_func_with_cache hashes "\n".join([user, system]) (utils.py:5232-5240)
    # and stores that string as original_prompt.
    if f"{user}\n{system}" != cache[CACHE_KEY]["original_prompt"]:
        raise SystemExit("Rebuilt prompt does not match the smoke run's cached prompt.")
    json_system, json_user = build_prompts(content, use_json=True)

    def msgs(s: str, u: str) -> list[dict]:
        return [{"role": "system", "content": s}, {"role": "user", "content": u}]

    delim = PROMPTS["DEFAULT_TUPLE_DELIMITER"]
    variants = [
        ("V0", "qwen2.5, original prompt, smoke options", QWEN,
         msgs(system, user), SMOKE_OPTIONS, None, False, delim),
        ("V1", "qwen2.5, original prompt, temperature 0", QWEN,
         msgs(system, user), {**SMOKE_OPTIONS, "temperature": 0}, None, False, delim),
        ("V2", "qwen2.5, delimiter ' | '", QWEN,
         msgs(system.replace(delim, ALT_DELIMITER), user.replace(delim, ALT_DELIMITER)),
         SMOKE_OPTIONS, None, False, ALT_DELIMITER),
        ("V3", "qwen2.5, JSON-mode prompts, format=json", QWEN,
         msgs(json_system, json_user), SMOKE_OPTIONS, "json", True, delim),
        ("V4", "llama3.1, original prompt, smoke options", LLAMA,
         msgs(system, user), SMOKE_OPTIONS, None, False, delim),
        ("V5", "qwen2.5, original prompt, num_ctx 8192", QWEN,
         msgs(system, user), {"num_ctx": 8192}, None, False, delim),
    ]
    return [run_variant(*variant) for variant in variants]


def run_variant(vid, label, model, messages, options, fmt, use_json, delimiter) -> dict:
    result = chat(model, messages, options, fmt)
    result.update(variant=vid, label=label, **parse(result["output"], use_json, delimiter))
    print(
        f"{vid} {label}: wall {result['wall_s']} s, load {result['load_duration_s']} s, "
        f"prompt {result['prompt_eval_count']} tok / {result['prompt_eval_duration_s']} s, "
        f"gen {result['eval_count']} tok / {result['eval_duration_s']} s, "
        f"{result['entities_parsed']} ent + {result['relations_parsed']} rel, "
        f"{result['names_with_space']}/{len(result['entity_names'])} names with space",
        flush=True,
    )
    return result


def run_d6() -> list[dict]:
    """Original prompt with the tuple delimiter set to <|SEP|>, sent twice."""
    chunks = json.loads((SMOKE_DIR / "kv_store_text_chunks.json").read_text())
    original = PROMPTS["DEFAULT_TUPLE_DELIMITER"]
    # Assign the key, as a LightRAG caller would; build_prompts reads it.
    PROMPTS["DEFAULT_TUPLE_DELIMITER"] = SEP_DELIMITER
    try:
        system, user = build_prompts(chunks[CHUNK_ID]["content"], use_json=False)
    finally:
        PROMPTS["DEFAULT_TUPLE_DELIMITER"] = original
    if original in system or SEP_DELIMITER not in system:
        raise SystemExit("Delimiter substitution did not take effect.")
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    return [
        run_variant(vid, "qwen2.5, delimiter <|SEP|>, smoke options", QWEN,
                    messages, SMOKE_OPTIONS, None, False, SEP_DELIMITER)
        for vid in ("V6a", "V6b")
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("step", choices=["d2", "d3", "d6"])
    args = parser.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results = {"d2": run_d2, "d3": run_d3, "d6": run_d6}[args.step]()
    out = OUT_DIR / f"{args.step}.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2))
    model_s = sum(r["total_duration_s"] for r in results)
    print(f"\nWrote {out.relative_to(ROOT)}; model runtime {model_s:.1f} s")
    for r in results:
        print(f"\n--- {r.get('variant', '')} {r['label']} ---\n{r['output']}")


if __name__ == "__main__":
    main()
