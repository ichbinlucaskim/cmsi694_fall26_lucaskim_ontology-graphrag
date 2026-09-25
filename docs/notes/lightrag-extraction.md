# LightRAG entity and relation extraction prompt (SCRUM-14)

Applies to `lightrag-hku==1.5.7` (GitHub tag `v1.5.7`), as installed by
`requirements.txt`. Paths below are relative to the installed package,
`.venv/lib/python3.11/site-packages/lightrag/`. Line numbers were read from the
installed source and will drift in other versions.

## Where the prompt lives

All templates are entries in the module-level dict `PROMPTS` in
`lightrag/prompt.py`.

| Key | Lines | Role |
|---|---|---|
| `default_entity_types_guidance` | 20-34 | Default entity type list (Person, Creature, Organization, Location, Event, Concept, Method, Content, Data, Artifact, NaturalObject, plus `Other`) |
| `entity_extraction_system_prompt` | 56-126 | System prompt: role, extraction rules, output format, `---Entity Types---` block |
| `entity_extraction_user_prompt` | 127-144 | Per-chunk user prompt that carries the input text |
| `entity_continue_extraction_user_prompt` | 145-162 | Gleaning pass ("extract anything you missed") |
| `entity_extraction_examples` | 163-174 | Output format template inserted as `{examples}` |
| `entity_extraction_json_*` | 175-296 | JSON-mode equivalents, used only when `entity_extraction_use_json=True` |

Delimiters are `DEFAULT_TUPLE_DELIMITER = "<|#|>"` (line 14) and
`DEFAULT_COMPLETION_DELIMITER = "<|COMPLETE|>"` (line 15).

The prompts are assembled in `extract_entities` in `lightrag/operate.py`
(starts at line 3941):

- 3999-4008: reads the entity type guidance resolved at construction (see below).
- 4071-4073: formats `PROMPTS["entity_extraction_system_prompt"]` once per
  `extract_entities` call.
- 4168-4180: formats `PROMPTS["entity_extraction_user_prompt"]` and the
  continue prompt once per chunk.
- 4181-4191: sends both to the extract-role LLM through
  `use_llm_func_with_cache`.

The model returns rows in this form:

```
entity<|#|>entity_name<|#|>entity_type<|#|>entity_description
relation<|#|>source_entity<|#|>target_entity<|#|>relationship_keywords<|#|>relationship_description
<|COMPLETE|>
```

## Placeholders

Verified with `string.Formatter().parse` on the installed templates.

| Template | Placeholders |
|---|---|
| `entity_extraction_system_prompt` | `tuple_delimiter`, `completion_delimiter`, `entity_types_guidance`, `examples`, `language`, `max_total_records`, `max_entity_records` |
| `entity_extraction_user_prompt` | `completion_delimiter`, `heading_context_block`, `input_text`, `language`, `max_total_records`, `max_entity_records` |
| `entity_continue_extraction_user_prompt` | `completion_delimiter`, `language`, `max_total_records`, `max_entity_records` |

`operate.py` formats every template with the same keyword set, so an override
may drop placeholders but must not introduce new ones; an unknown `{name}`
raises `KeyError` at format time. Literal braces must be doubled (`{{`, `}}`).

## Configuring entity types (no prompt override)

LightRAG accepts entity types as configuration, as free-text guidance rather
than a list of type names.

**How it is passed.** Through the `addon_params` constructor argument:

```python
rag = LightRAG(
    ...,
    addon_params={"entity_types_guidance": "Classify each entity ... \n- Human: ...\n- Film: ..."},
)
```

The string replaces `default_entity_types_guidance` in full and is substituted
into `{entity_types_guidance}` in the system prompt (text mode) or in both the
system and user prompts (JSON mode, `prompt.py` lines 228 and 245).

**Code locations.**

- `prompt.py:811-862`, `resolve_entity_extraction_prompt_profile`. Precedence
  (lines 838-843): `addon_params["entity_types_guidance"]`, then the
  `entity_types_guidance` field of a YAML profile named by
  `addon_params["entity_type_prompt_file"]`, then the built-in default. A
  non-string or empty value raises `ValueError`.
- `lightrag.py:1171-1189`, `_refresh_addon_params_cache`, resolves the profile
  at construction and again when `addon_params` changes.
- `lightrag.py:1258-1263`: the older `ENTITY_TYPES` environment variable is
  rejected. If it is set, construction exits with "ENTITY_TYPES environment
  variable is no longer supported." There is no list-valued `entity_types`
  parameter in 1.5.7; a search of the package for an `"entity_types"` key
  found none.

**YAML profile alternative.** `addon_params={"entity_type_prompt_file":
"<name>.yml"}` loads `PROMPT_DIR/entity_type/<name>.yml` (`PROMPT_DIR` defaults
to `./prompts`, relative to the working directory; `prompt.py:553-641`). The
file may set `entity_types_guidance` and must set `entity_extraction_examples`
(or `entity_extraction_json_examples` in JSON mode), or construction fails
(`prompt.py:825-835`). Only a bare file name is accepted.

**Relation types cannot be constrained this way.** No configuration value
covers relations. `relationship_keywords` is free text produced under the
fixed instruction in `entity_extraction_system_prompt` section 2 ("One or more
high-level keywords summarizing the relationship"). Constraining relations to
an ontology's properties requires changing prompt text: either put the
relation vocabulary into the `entity_types_guidance` string (it is plain prompt
text, so the model sees it, but the section is headed `---Entity Types---` and
nothing enforces it), or override the system prompt as described below.

Verified offline: resolving a profile with
`{"entity_types_guidance": "- Human: ONTOLOGY_MARKER"}` and formatting the
system prompt yields a string that contains the marker and no longer contains
the default `NaturalObject` type.

## Overriding the prompt without editing the library

`operate.py` imports `PROMPTS` from `lightrag.prompt` (line 79) and indexes it
at call time, so both modules hold the same dict object (verified:
`lightrag.operate.PROMPTS is lightrag.prompt.PROMPTS` is `True`). Assigning a
key before indexing takes effect on the next insert:

```python
from lightrag.prompt import PROMPTS

PROMPTS["entity_extraction_system_prompt"] = ONTOLOGY_SYSTEM_PROMPT
```

Rules:

- Assign keys; do not rebind `PROMPTS` itself.
- The change is process-global. Run each experimental condition in its own
  process, or restore the original string afterwards.
- Keep the output format and delimiters. The parser in `operate.py` expects
  the 4-field `entity` and 5-field `relation` rows.

### Wrapper around the extraction call

The Jira story prefers a wrapper over editing library code. LightRAG supports
one through the `extract` role:

```python
from lightrag.llm_roles import RoleLLMConfig

async def ontology_extract(prompt, system_prompt=None, **kwargs):
    if system_prompt is not None:          # extraction and gleaning calls
        system_prompt = inject_ontology(system_prompt)
    return await ollama_model_complete(prompt, system_prompt=system_prompt, **kwargs)

rag = LightRAG(..., role_llm_configs={"extract": RoleLLMConfig(func=ontology_extract)})
```

This sketch follows the role API (`lightrag/llm_roles.py`, `RoleLLMConfig`)
but has not been run yet. Caveats, from the source:

- The extract role serves more than extraction. `_summarize_descriptions`
  (`operate.py:566`, call at 611) also uses it, with no system prompt, to merge
  entity and relation descriptions. The wrapper above distinguishes the two
  by `system_prompt is None`.
- **The LLM response cache is keyed before the wrapper runs.**
  `use_llm_func_with_cache` (`utils.py:5236-5252`) hashes the user prompt,
  system prompt, history, response format, and role identity (role, binding,
  model, host; `lightrag.py:1237-1250`), then calls the role function. A
  wrapper that rewrites the prompt inside the call is invisible to the cache
  key, so two conditions that share a working directory would reuse each
  other's cached extractions. Use a separate working directory per condition,
  or prefer `addon_params` / a `PROMPTS` override, which change the prompt
  before hashing.

## Recommendation for the ontology condition

1. Entity classes: `addon_params["entity_types_guidance"]`. This is
   configuration only and is visible to the cache key.
2. Relation properties: override `PROMPTS["entity_extraction_system_prompt"]`,
   keeping the format rules and changing section 2 to list the allowed
   relation types.
3. Keep one working directory per condition under `runs/`.

## Open questions

- Nothing in LightRAG checks that extracted types or keywords come from the
  supplied vocabulary. Compliance has to be measured, not assumed.
- In the smoke run, stored entity types were lowercased (`person`) and 14 of
  47 entities had type `UNKNOWN`. I have not yet traced where the
  normalization happens or when `UNKNOWN` is assigned.
