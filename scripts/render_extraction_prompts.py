"""Render the extraction prompts of two conditions for one chunk and diff them (SCRUM-18).

    python scripts/render_extraction_prompts.py
    python scripts/render_extraction_prompts.py --check

For each condition, a separate process builds LightRAG through
run_condition.build_rag (so the condition's addon_params and prompt_overrides
are applied as in a run) and formats the JSON-mode system and user extraction
prompts the way lightrag/operate.py does in 1.5.7:

    context_base                 operate.py:4013-4021
    system prompt                operate.py:4057-4060
    user prompt                  operate.py:4150-4160
    heading block, chunk content operate.py:4098-4119 (empty for plain text)

The chunk is FIXED_PARAGRAPH from smoke10, rendered with the shared
indexing.document_text template; at 1,200 tokens per chunk every smoke10
paragraph is one chunk. No model is called.

Writes docs/results/prompts/<condition>-{system,user}.txt and the unified diff
docs/results/prompt-diff-baseline-vs-ontology.diff. --check compares instead.
"""

import argparse
import difflib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "docs" / "results" / "prompts"
DIFF_PATH = ROOT / "docs" / "results" / "prompt-diff-baseline-vs-ontology.diff"
CONDITIONS = ["baseline", "ontology"]
SUBSET = "smoke10"
# A gold paragraph of the first smoke10 question.
FIXED_PARAGRAPH = "p_05c5ddee76194d7e"


def render_one(condition: str) -> dict:
    """Run inside a fresh process: PROMPTS overrides are process-global."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import run_condition as rc
    from lightrag.chunk_schema import strip_internal_multimodal_markup_for_extraction
    from lightrag.prompt import PROMPTS

    shared, cond, hashes = rc.load_config(condition)
    _, corpus, _ = rc.load_subset(SUBSET)
    paragraph = next(p for p in corpus if p["id"] == FIXED_PARAGRAPH)
    content = shared["indexing"]["document_text"].format(title=paragraph["title"], text=paragraph["text"])
    with tempfile.TemporaryDirectory() as tmp:
        rag = rc.build_rag(shared, cond, Path(tmp), rc.SharedTokenTracker(), rc.SharedTokenTracker())
        if not rag.entity_extraction_use_json:
            raise SystemExit("expected JSON-mode extraction")
        profile = rag._entity_extraction_prompt_profile
        context_base = dict(
            entity_types_guidance=profile["entity_types_guidance"],
            examples="\n".join(profile["entity_extraction_json_examples"]),
            language=rag._resolved_summary_language,
            max_total_records=rag.entity_extract_max_records,
            max_entity_records=rag.entity_extract_max_entities,
        )
        system = PROMPTS["entity_extraction_json_system_prompt"].format(**context_base)
        user = PROMPTS["entity_extraction_json_user_prompt"].format(**{
            **context_base,
            "input_text": strip_internal_multimodal_markup_for_extraction(content),
            "heading_context_block": "",
        })
        tokens = {"system": len(rag.tokenizer.encode(system)), "user": len(rag.tokenizer.encode(user))}
    return {"condition": condition, "hashes": hashes, "system": system, "user": user, "tokens": tokens}


def render_all() -> list[dict]:
    out = []
    for condition in CONDITIONS:
        proc = subprocess.run(
            [sys.executable, __file__, "--render-one", condition],
            cwd=ROOT, capture_output=True, text=True, check=True,
        )
        out.append(json.loads(proc.stdout.strip().splitlines()[-1]))
    return out


def outputs(rendered: list[dict]) -> dict[Path, str]:
    files = {}
    for r in rendered:
        for part in ("system", "user"):
            files[OUT_DIR / f"{r['condition']}-{part}.txt"] = r[part]
    base, onto = rendered
    diff = []
    for part in ("system", "user"):
        diff += difflib.unified_diff(
            base[part].splitlines(keepends=True), onto[part].splitlines(keepends=True),
            fromfile=f"baseline/{part}", tofile=f"ontology/{part}", n=2,
        )
    files[DIFF_PATH] = "".join(line if line.endswith("\n") else line + "\n" for line in diff)
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--render-one", metavar="CONDITION", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.render_one:
        print(json.dumps(render_one(args.render_one)))
        return 0

    rendered = render_all()
    files = outputs(rendered)
    if args.check:
        stale = [p for p, text in files.items() if not p.exists() or p.read_text(encoding="utf-8") != text]
        for p in stale:
            print(f"differs: {p.relative_to(ROOT)}")
        print("check failed" if stale else "check passed")
        return 1 if stale else 0
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for p, text in files.items():
        p.write_text(text, encoding="utf-8")
        print(f"Wrote {p.relative_to(ROOT)}")
    for r in rendered:
        t = r["tokens"]
        print(f"{r['condition']}: system {t['system']} + user {t['user']} = {t['system'] + t['user']} tokens")
    return 0


if __name__ == "__main__":
    sys.exit(main())
