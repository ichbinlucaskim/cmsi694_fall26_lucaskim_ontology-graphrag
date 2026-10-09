"""Render the ontology into LightRAG's extraction prompt (SCRUM-18).

    python scripts/ontology_prompt.py --write-condition   # write configs/conditions/ontology.json
    python scripts/ontology_prompt.py --check             # compare the condition file with a regeneration

render(ontology) returns the two pieces of text the treatment adds:

    entity_types_guidance  every entity type with its definition, and its
                           broader type where it has one. LightRAG fills it
                           into {entity_types_guidance} of the extraction
                           prompts when given as addon_params.
    relation_types_block   every relation as
                           "<label> (<domain> -> <range>): <definition>",
                           with the instruction that a relationship's keywords
                           are exactly one label from the list.

--write-condition builds the ontology condition from these and from the
installed LightRAG 1.5.7 JSON-mode extraction templates (lightrag/prompt.py):

    entity_extraction_json_system_prompt  (prompt.py:175-234)
        the `keywords` bullet of the relationship instructions is replaced,
        and a ---Relation Types--- section is added after ---Entity Types---.
    entity_extraction_json_user_prompt    (prompt.py:236-253)
        the same ---Relation Types--- section is added after ---Entity Types---,
        as LightRAG repeats the entity types there.

Each change is an exact substitution that must match once. The output format
template, the delimiters, and every placeholder stay as installed. The
gleaning prompt (entity_continue_extraction_json_user_prompt, prompt.py:255)
is not overridden: gleaning is off (indexing.entity_extract_max_gleaning = 0).

The ontology module is standard library only; --write-condition and --check
import lightrag to read the installed templates.
"""

import argparse
import hashlib
import json
import string
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ONTOLOGY_PATH = ROOT / "ontology" / "ontology.json"
CONDITION_PATH = ROOT / "configs" / "conditions" / "ontology.json"

ENTITY_TYPES_INTRO = "Classify each entity using one of the following types. If no type fits, use `Other`."
RELATION_TYPES_INTRO = (
    "Label each relationship with exactly one of the following relation labels. The `keywords` "
    "field of a relationship must be exactly one label from this list, written as listed. "
    "Extract only relationships that one of these labels describes. Each line gives the label, "
    "the entity types of its source and target, and its definition. For a relation whose target "
    "is a date, the target entity is the date as written in the input text."
)
DATE_RANGE = "literal:date"

SYSTEM_KEY = "entity_extraction_json_system_prompt"
USER_KEY = "entity_extraction_json_user_prompt"
KEYWORDS_BULLET = (
    "    - `keywords`: One or more high-level keywords summarizing the overarching nature, "
    "concepts, or themes of the relationship, separated by commas.\n"
)
ONTOLOGY_KEYWORDS_BULLET = (
    "    - `keywords`: Exactly one relation label from the `---Relation Types---` section, "
    "written exactly as listed.\n"
)
SYSTEM_ANCHOR = "---Entity Types---\n{entity_types_guidance}\n\n---Output Format Template---\n"
USER_ANCHOR = "---Entity Types---\n{entity_types_guidance}\n\n{heading_context_block}"


def load_ontology(path: Path = ONTOLOGY_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _types(value) -> str:
    return "date" if value == DATE_RANGE else " | ".join(value)


def render_entity_types(ontology: dict) -> str:
    lines = [ENTITY_TYPES_INTRO, ""]
    for t in sorted(ontology["entity_types"], key=lambda t: t["name"]):
        broader = f" (a kind of {t['broader']})" if t["broader"] else ""
        lines.append(f"- {t['name']}{broader}: {t['definition']}")
    return "\n".join(lines)


def render_relation_types(ontology: dict) -> str:
    lines = [RELATION_TYPES_INTRO, ""]
    for r in sorted(ontology["relation_types"], key=lambda r: r["relation"]):
        lines.append(f"- {r['relation']} ({_types(r['domain'])} -> {_types(r['range'])}): {r['definition']}")
    return "\n".join(lines)


def render(ontology: dict) -> dict[str, str]:
    """The entity type guidance and the relation types block for one ontology."""
    return {
        "entity_types_guidance": render_entity_types(ontology),
        "relation_types_block": render_relation_types(ontology),
    }


def placeholders(template: str) -> set[str]:
    return {field for _, field, _, _ in string.Formatter().parse(template) if field is not None}


def _escape(text: str) -> str:
    """Make literal text safe inside a str.format template."""
    return text.replace("{", "{{").replace("}", "}}")


def _substitute(template: str, old: str, new: str, key: str) -> str:
    if template.count(old) != 1:
        raise SystemExit(f"{key}: expected exactly one match for {old!r}")
    return template.replace(old, new)


def build_condition(ontology: dict, prompts: dict) -> dict:
    """The ontology condition file, from the ontology and the installed PROMPTS."""
    rendered = render(ontology)
    section = "---Relation Types---\n" + _escape(rendered["relation_types_block"]) + "\n\n"
    system = _substitute(prompts[SYSTEM_KEY], KEYWORDS_BULLET, ONTOLOGY_KEYWORDS_BULLET, SYSTEM_KEY)
    system = _substitute(
        system, SYSTEM_ANCHOR,
        "---Entity Types---\n{entity_types_guidance}\n\n" + section + "---Output Format Template---\n",
        SYSTEM_KEY,
    )
    user = _substitute(
        prompts[USER_KEY], USER_ANCHOR,
        "---Entity Types---\n{entity_types_guidance}\n\n" + section + "{heading_context_block}",
        USER_KEY,
    )
    for key, new in ((SYSTEM_KEY, system), (USER_KEY, user)):
        if placeholders(new) != placeholders(prompts[key]):
            raise SystemExit(f"{key}: placeholders changed")
    ontology_raw = ONTOLOGY_PATH.read_bytes()
    return {
        "name": "ontology",
        "description": (
            "Ontology-guided extraction: the baseline with the entity types and relation types "
            "of ontology/ontology.json rendered into the JSON-mode extraction prompts. Written by "
            "scripts/ontology_prompt.py --write-condition; do not edit by hand."
        ),
        "ontology_sha256": hashlib.sha256(ontology_raw).hexdigest(),
        "settings": {
            "addon_params": {"entity_types_guidance": rendered["entity_types_guidance"]},
            "prompt_overrides": {SYSTEM_KEY: system, USER_KEY: user},
        },
    }


def dump(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write-condition", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()

    from lightrag.prompt import PROMPTS

    text = dump(build_condition(load_ontology(), PROMPTS))
    if args.check:
        same = CONDITION_PATH.exists() and CONDITION_PATH.read_text(encoding="utf-8") == text
        print("check passed" if same else f"differs: {CONDITION_PATH.relative_to(ROOT)}")
        return 0 if same else 1
    CONDITION_PATH.write_text(text, encoding="utf-8")
    print(f"Wrote {CONDITION_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
