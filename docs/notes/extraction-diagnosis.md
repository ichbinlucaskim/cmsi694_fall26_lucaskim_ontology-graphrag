# Extraction quality and speed diagnosis (SCRUM-29 spike)

Follow-up to SCRUM-14. The smoke run produced entity names and descriptions
with words run together ("ChristianeWartenberg", "competedmainlyinthe1500metres")
and indexed at 106 s per paragraph. This spike locates the cause and measures
the alternatives.

Setup: `lightrag-hku==1.5.7`, Ollama 0.34.3, Apple M1 16 GB (see `MODELS.md`).
Raw outputs are in `runs/diagnosis/` (git-ignored). Commands:

```
python scripts/diagnose_extraction.py d2
python scripts/diagnose_extraction.py d3
python scripts/lightrag_smoke.py --use-json --max-gleaning 0 --runs-dir runs/diagnosis/d4
python scripts/diagnose_extraction.py d6
python scripts/lightrag_smoke.py --tuple-delimiter "<|SEP|>" --max-gleaning 0 --runs-dir runs/diagnosis/d7
```

Model runtime used, including warm-up and embeddings:

| Step | Runtime |
|---|---|
| D2 | 16.6 s |
| D3 | 351.4 s |
| D4 | 379 s |
| D6 | 83.7 s |
| D7 | 820 s, of which 480 s was one timed-out call |
| **Total** | **1,650.7 s (27.5 minutes of the 60-minute time box)** |

## Observed results

### D1. Raw cached response (no model calls)

The smoke run's LLM cache (`kv_store_llm_response_cache.json`, key
`default:extract:72105fa8f9b3ffbba241d34c154728ef`, chunk
`2wiki-smoke-1-chunk-000`) holds this response to the initial extraction call:

```
entity<|#|>ChristianeWartenberg<|#|>Person<|#|>Germanathlete,competedmainlyinthe1500metres,competedforeastGermaniamintheim1980SummerOlympicsinMoscow,Russia,wherehewonthesilverbmedal
relation<|#|>ChristianeWartenberg<|#|>ChristianeWartenberg<|#|>Stoll<|#|>born<|#|>born27October1956inPrenzlau
relation<|#|>ChristianeWartenberg<|#|>Germany<|#|>competedforeastGermaniamintheim1980SummerOlympicsinMoscow,Russia
relation<|#|>ChristianeWartenberg<|#|>1500metres<|#|>competedin<|#|>competedmainlyinthe1500metres
relation<|#|>ChristianeWartenberg<|#|>Moscow,Russia<|#|>competedin<|#|>competedforeastGermaniamintheim1980SummerOlympicsinMoscow,Russia
relation<|#|>ChristianeWartenberg<|#|>Silvermedal<|#|>won<|#|>wonthesilverbmedal
<|COMPLETE|>
```

The input chunk has normal spacing: "Christiane Wartenberg (Stoll, born 27 October
1956 in Prenzlau) is a German athlete who competed mainly in the 1500 metres. ..."

**The missing spaces are already present in the raw model output.** LightRAG's
post-processing did not remove them.

### D2. Model sanity (plain chat, no LightRAG)

Prompt: "In one sentence, who was Alfonso VII of León?"

| Options | Wall (s) | Output |
|---|---|---|
| Ollama defaults | 9.03 | Alfonso VII of León was the King of León, Castile, Galicia, and Navarre from 1126 to 1157, known for his role in the Reconquista and expansion of Christian territories in the Iberian Peninsula. |
| Smoke options (`num_ctx` 32768) | 7.61 | Alfonso VII of León was a Spanish king who ruled during the High Middle Ages, expanding the Christian kingdoms' territory and claiming the title of Emperor of all Spain. |

Both outputs have normal spacing.

### D3. One extraction call per variant, same chunk

The prompts are rebuilt the way `operate.extract_entities` builds them, including
the `sanitize_text_for_encoding` step LightRAG applies before sending
(`utils.py:5214-5217`). The script refuses to run unless the rebuilt
`user + "\n" + system` equals the `original_prompt` stored in the smoke cache
byte for byte; it matched. The smoke run's options were exactly
`{"num_ctx": 32768}`; extraction adds no `num_predict`, and
`qwen2.5:7b-instruct` sets no Modelfile parameters, so other sampling settings
were Ollama defaults. Parsing uses LightRAG's own `_process_extraction_result`
(text) and `_process_json_extraction_result` (JSON).

"Run-together names" is my classification of the parsed names: multi-word names
emitted without spaces. One-word names such as `Prenzlau` are not counted.

| Variant | Wall (s) | prompt_eval_count | prompt_eval (s) | eval_count | eval (s) | Gen tok/s | Names with a space | Run-together names | Parsed entities + relations |
|---|---|---|---|---|---|---|---|---|---|
| V0 qwen2.5, original, smoke options | 45.49 | 1849 | 17.36 | 328 | 28.05 | 11.7 | 0/7 | 4/7 | 7 + 0 |
| V1 qwen2.5, original, temperature 0 | 29.29 | 1849 | 0.08 | 349 | 29.14 | 12.0 | 0/9 | 5/9 | 9 + 0 |
| V2 qwen2.5, delimiter `" \| "` | 62.37 | 1801 | 14.04 | 509 | 48.23 | 10.6 | 7/9 | 0/9 | 9 + 6 |
| V3 qwen2.5, JSON-mode prompts, `format=json` | 95.33 | 1866 | 19.86 | 747 | 75.30 | 9.9 | 4/7 | 0/7 | 7 + 6 |
| V4 llama3.1, original, smoke options | 62.51 | 1836 | 22.98 | 286 | 33.78 | 8.5 | 2/5 | 0/5 | 5 + 4 |
| V5 qwen2.5, original, `num_ctx` 8192 | 56.67 | 1849 | 20.34 | 340 | 32.35 | 10.5 | 1/5 | 3/5 | 5 + 3 |

Notes on the table:

- V1's prompt evaluation took 0.08 s because Ollama reused the cached prompt
  from V0, which was identical. Its wall-clock is not comparable to the others.
- V4 and V5 include a model load (5.63 s and 3.92 s).
- V0 and V1 parse 0 relations. Every relation row they emitted either had the
  same source and target (`ChristianeWartenberg` to `ChristianeWartenberg`),
  which LightRAG drops, or had the wrong number of fields.
- In V0, V1, and V5, descriptions also run together
  ("Germanathletewho-competedmainlyinthe1500metres"), not only names.
- Full outputs are in `runs/diagnosis/d3.json`.

### D4. Five-paragraph smoke set with the chosen configuration

Configuration: V3 (`entity_extraction_use_json=True`) with gleaning disabled
(`entity_extract_max_gleaning=0`). Everything else is as in the SCRUM-14 smoke
run. Working directory: `runs/diagnosis/d4/20260924T001642Z`. The directory
name is the start time in UTC; the run started 2026-09-23 17:16
(America/Los_Angeles).

| Measure | SCRUM-14 smoke (text mode, gleaning 1) | D4 (JSON mode, gleaning 0) |
|---|---|---|
| Documents processed | 5/5 | 5/5 |
| Extraction LLM calls (cache entries) | 10 | 5 |
| Indexing wall-clock | 529.9 s | 371.6 s |
| Seconds per paragraph | 106.0 | 74.3 |
| Entities | 47 | 37 |
| Relations | 24 | 29 |
| Entity names containing a space | 0/47 | 26/37 |
| Entity types `UNKNOWN` | 14 | 1 |
| ERROR lines in the log | 0 | 0 |

All 11 D4 names without a space are single words: Alice, Commodus, Devonshire,
Essex, Moscow, Northamptonshire, Oxfordshire, Prenzlau, Russia, Stogursey,
Wiltshire. D4 also produced types outside the default list (`role`, `date`).

Parameter locations in the installed source:

- Gleaning: `entity_extract_max_gleaning`, `lightrag.py:470-472` (env
  `MAX_GLEANING`, default `DEFAULT_MAX_GLEANING = 1` in `constants.py:17`).
  The gate is `run_gleaning = entity_extract_max_gleaning > 0` at
  `operate.py:4218`.
- JSON mode: `entity_extraction_use_json`, `lightrag.py:743-745` (env
  `ENTITY_EXTRACTION_USE_JSON`). The Ollama binding maps
  `response_format={"type": "json_object"}` to `format="json"`
  (`llm/ollama.py:142-167`).

### D6. Delimiter in the documented form, `<|SEP|>`

Purpose: test whether the `<|...|>` shape itself causes the damage, or only
the string `<|#|>`. `<|SEP|>` follows the form required at `prompt.py:13`
("All delimiters must be formatted as `<|UPPER_CASE_STRING|>`").

**Pre-check of the delimiter repair step (no model calls).** No part of it
assumes `#`:

- The parser derives the core with `delimiter_core = tuple_delimiter[2:-2]`
  (`operate.py:1587`). That gives `SEP`.
- Every core-dependent pattern in `fix_tuple_delimiter_corruption`
  (`utils.py:6680-6806`) is built from `re.escape(delimiter_core)`.
- The only `#` literals are the default argument at `operate.py:1512` and
  comments.
- Because `SEP` is uppercase, a second pass with the lowercase core also runs
  (`operate.py:1596-1600`). It repairs `<|sep|>`.
- An offline check through `_process_extraction_result` confirmed this.
  `<|SEP|>`, `<|sep|>`, and `<SEP>` rows all parsed into 3 entities and 1
  relation.
- One delimiter-independent quirk: `operate.py:1562` prefixes stray fragments
  with a hard-coded `entity<|`. It behaves the same for any delimiter.

**Method.** `PROMPTS["DEFAULT_TUPLE_DELIMITER"]` is assigned `"<|SEP|>"`. The
completion delimiter is unchanged. The prompt is rebuilt as in D3 and sent
twice with the smoke options. V6b reused Ollama's prompt cache, so compare
`eval_count` and `eval_duration`, not wall-clock.

| Variant | Wall (s) | prompt_eval_count | prompt_eval (s) | eval_count | eval (s) | Gen tok/s | Names with a space | Run-together names | Parsed entities + relations |
|---|---|---|---|---|---|---|---|---|---|
| V6a qwen2.5, `<\|SEP\|>`, smoke options | 57.33 | 1877 | 18.97 | 375 | 33.44 | 11.2 | 2/3 | 0/3 | 3 + 4 |
| V6b qwen2.5, `<\|SEP\|>`, smoke options (prompt cached) | 26.43 | 1877 | 0.09 | 295 | 26.29 | 11.2 | 5/6 | 0/6 | 6 + 1 |

Both runs have normal spacing in names and descriptions. V6a also includes a
4.86 s model load.

V6a's format is unstable:

- It emits relations before the entities they refer to.
- It ends with `relation<SEP>|COMPLETE|` instead of `<|COMPLETE|>`.
- 4 of its 5 relation rows point to entities that never get an entity row.

V6b is well formed. Of its two relation rows, one is a self-loop that LightRAG
drops, which leaves one parsed relation. Full outputs are in
`runs/diagnosis/d6.json`.

### D7. Five-paragraph smoke set, `<|SEP|>` text mode, gleaning 0

D6 met the condition for this run: no run-together names and at least one
parsed relation in both calls. Working directory:
`runs/diagnosis/d7/20260925T010241Z`. The directory name is the start time in
UTC; the run started 2026-09-24 18:02 (America/Los_Angeles).

| Measure | D4 (JSON mode, gleaning 0) | D7 (`<\|SEP\|>` text mode, gleaning 0) |
|---|---|---|
| Documents processed | 5/5 | **4/5** |
| Extraction LLM calls | 5 | 5 (1 timed out, 4 cached) |
| Indexing wall-clock | 371.6 s | 815.6 s |
| Seconds per paragraph | 74.3 | 163.1 |
| Entities | 37 | 31 |
| Relations | 29 | 26 |
| Entity names containing a space | 26/37 | 2/31 |
| Entity types `UNKNOWN` | 1 | 2 |
| ERROR lines in the log | 0 | 6 (all from the timeout) |

The failure was on paragraph [1], Christiane Wartenberg, the same chunk that
was clean in both D6 calls. The extraction call hit LightRAG's 480 s worker
timeout (Ollama `/api/chat` returned 500 after 8m0s). The output was not
cached, so it cannot be inspected.

Per-call extraction time from the Ollama server log, in seconds:

| Document | D4 | D7 |
|---|---|---|
| doc0 | 47.0 | 15.3 |
| doc1 | 70 | 480, timeout |
| doc2 | 120 | 200 |
| doc3 | 76 | 68 |
| doc4 | 56.4 | 50.7 |

On the four documents that succeeded in both runs, D7 took 334 s against
D4's 299 s.

The raw cached outputs show multi-word entity names in CamelCase in 3 of the 4
successful chunks: `WilliamDeCourcy`, `AviceDeRumilly`, `SignOfThePagan`,
`JeffChandler`, `ConstanceOfCastile`, `AlfonsoVIIofLeón`. The descriptions in
the same rows have normal spacing, for example "William de Courcy, an
Anglo-Norman nobleman and baron who lived in the 12th century." Chunk 0 used
spaced title case (`Dolichianus Of Jerusalem`).

## Where the spaces disappear, and why

**Where (proven).** In the model's output. D1 shows the run-together text in
the raw cached response, and D3 reproduces it outside LightRAG with the exact
prompt. D7's CamelCase names are likewise present in the raw cached responses.

**Observed with `<|#|>` (one call per variant).**

- Names and descriptions both run together with qwen2.5 in text mode (V0, V1,
  V5). Temperature 0 and a smaller context do not change this.
- The damage disappears with `" | "` (V2) or JSON output (V3).
- llama3.1 with the same prompt is unaffected (V4).
- qwen2.5 with the same options writes normally in plain chat (D2).

**Observed with `<|SEP|>`.**

- On the Christiane Wartenberg chunk, two calls (V6a, V6b) produced normally
  spaced names and descriptions.
- On the five-paragraph set (D7), descriptions were normally spaced in every
  successful chunk. Multi-word entity names were written in CamelCase in 3 of
  the 4 successful chunks, and in spaced title case in the fourth.
- One chunk (Christiane Wartenberg, clean in D6) ran until the 480 s timeout.
- V6a ended with a malformed completion marker.

**Interpretation of the shape hypothesis (not proven).**

- **Partly supported for names; not supported for descriptions.**
  - `<|SEP|>` removed the run-together descriptions that `<|#|>` produced. So
    the description damage is tied to the specific string `<|#|>`, not to the
    `<|...|>` shape.
  - Run-together names persisted with `<|SEP|>` on other chunks, and only the
    formats without `<|...|>` (`" | "` and JSON) gave spaced names. So name
    damage correlates with the shape.
- **The name damage now looks different.** With `<|#|>` it was lowercase
  gluing that also dropped letters ("silverbmedal"). With `<|SEP|>` it is
  consistent CamelCase ("WilliamDeCourcy").
  - One untested explanation: the model treats names inside `<|...|>` rows as
    identifiers. The prompt also asks for title case on names
    (`entity_extraction_system_prompt`, section 1). Title case without spaces
    is CamelCase.
- **I did not isolate the cause of the timeout.** The output was not saved.
  V6a's malformed completion marker and out-of-order rows point to the same
  format instability; a missing completion marker would let generation run
  until the timeout.
- **Why this cannot be treated as proven:**
  - The variants are single samples, and D6 and D7 disagree on the same kind
    of input.
  - The `" | "` and JSON prompts differ from the `<|...|>` prompts in more than
    the delimiter shape.
  - I have not examined Qwen's tokenization of either delimiter.

## Recommended configuration

For qwen2.5:7b-instruct on this machine:

```python
LightRAG(
    ...,
    entity_extraction_use_json=True,   # spaced names and descriptions (D3 V3, D4)
    entity_extract_max_gleaning=0,     # halves extraction calls (D4)
)
```

**Choice: JSON mode over `<|SEP|>` text mode.** Output quality came first,
then seconds per paragraph:

- **Quality: JSON mode wins.**

  | Measure | D4 (JSON) | D7 (`<\|SEP\|>`) |
  |---|---|---|
  | Documents processed | 5/5 | 4/5 (1 timeout) |
  | Multi-word names run together | 0 | 3 of 4 successful chunks |
  | `UNKNOWN` types | 1 | 2 |

- **Speed: JSON mode also wins.**

  | Measure | D4 (JSON) | D7 (`<\|SEP\|>`) |
  |---|---|---|
  | Seconds per paragraph, as run | 74.3 | 163.1 |
  | The same four successful documents | 299 s | 334 s |

  The single-call advantage of text mode (fewer output tokens, D3) did not
  carry over to the full set.

- **Supported.** JSON mode is a documented LightRAG option
  (`entity_extraction_use_json`) and needs no prompt edits.

Other alternatives:

- **`" | "` (V2) is not supported.** It also fixed the output, and LightRAG can
  use it without library edits: `operate.py` reads
  `PROMPTS["DEFAULT_TUPLE_DELIMITER"]` at call time (lines 4027, 4036, 4213,
  4287), and for a delimiter without `<|...|>` form the repair step returns
  early (`utils.py:6698`). However, it breaks the rule at `prompt.py:13`,
  disables delimiter repair, and can collide with `" | "` in the text. I do not
  consider it supported.
- **`<|SEP|>` is supported but inadequate.** It follows the documented form and
  parses correctly, but did not fix the output (D7).

Open items:

- **Runaway generation.** Runaway output is possible in any mode. LightRAG
  documents `OLLAMA_LLM_NUM_PREDICT` as the way to "stop runaway extraction
  output" (`docs/LLMProviderOptions.md`, section 4.1). A cap in
  `llm_model_kwargs["options"]["num_predict"]` would bound the damage to one
  chunk well before 480 s. Not tested.
- **Gleaning's effect on quality was not measured.** It was disabled for speed
  only.
- **Types outside the vocabulary.** D4 produced types outside the default list.
  The ontology condition will need to measure type compliance.
- **Configuration record.** `MODELS.md` still records the SCRUM-14 settings.
  Update it when this configuration is adopted.

## Indexing time projection (no model calls)

The D4 rate of 74.3 s per paragraph is applied to unique paragraphs
(deduplicated on `(title, text)`). The estimate is for one condition; two
conditions double it. The rate is unchanged by D6 and D7, because the
recommendation is still JSON mode.

| Sample | Source | Context paragraphs (unique) | Mean words | Projected indexing time |
|---|---|---|---|---|
| smoke20 | Frozen subset, SCRUM-15 (`data/subsets/manifest.json`) | 187 | 69.9 | 13,894 s (3.9 h) |
| study50 | Frozen subset, SCRUM-15 | 427 | 64.4 | 31,726 s (8.8 h) |
| 300 questions | `random.Random(694).sample(dev, 300)` | 2,111 | 69 | 156,847 s (43.6 h) |

The smoke20 row replaces an earlier estimate of 184 paragraphs, which was
computed from `random.Random(694).sample(dev, 20)` before the subset was
frozen.

For comparison, indexing only the paragraphs named in `supporting_facts`
would give 54 paragraphs (1.1 h) for 20 questions and 725 paragraphs (15.0 h)
for 300. This removes the distractor paragraphs, which changes the retrieval
task. It is listed as an option, not a recommendation.

Limits of the projection:

- The rate comes from 5 paragraphs averaging 72 words, one run.
- Time is dominated by generation at about 10-12 tokens/s, so it scales with
  output length more than with paragraph count.
- It assumes one request at a time (`OLLAMA_NUM_PARALLEL=1`,
  `llm_model_max_async=1`).
