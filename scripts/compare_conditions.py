"""Compare two scored conditions on one subset (SCRUM-18).

    python scripts/compare_conditions.py --baseline baseline --treatment ontology --subset smoke10

Reads, for each condition, runs/<condition>/<subset>/scores.json (written by
scripts/score.py), results.jsonl, run_manifest.json, and the LightRAG graph,
and writes docs/results/<treatment>-vs-<baseline>-<subset>.md. It reads runs/
only; it never writes there.

"Right" means official EM with aliases (em_alias in scores.json) equals 1.

A graph node is a date when its name is a date: a bare year (3 or 4 digits),
or a day, month name, and year in either order, or a month name and year
(DATE_NAME below). The type the model gave the node is not used, so the count
is comparable across conditions. A date relation is an edge with a date node
at either end.

Standard library only.
"""

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import relation_conformance as rcf

ROOT = Path(__file__).resolve().parent.parent
RUNS_DIR = ROOT / "runs"
DOCS_DIR = ROOT / "docs" / "results"
METRICS = [("em", "EM"), ("em_alias", "EM (aliases)"), ("f1", "F1"), ("f1_alias", "F1 (aliases)"),
           ("retrieval_recall", "Retrieval recall")]
MONTHS = "january|february|march|april|may|june|july|august|september|october|november|december"
LIMITATIONS = """## Limitations

- **n = 10.** Every interval above is wide, and a difference of a few questions
  is within noise. For scale: the SCRUM-30 answer-template change alone, with
  the same index, changed 3 of the 10 baseline answers.
- **One run per condition.** Each condition was indexed and queried once, with
  seed 694. Run-to-run variation has not been measured (SCRUM-22).
- **No entity type for dates.** Dates are literal attributes in the ontology
  (SCRUM-17, D4), so a date the model extracts as a node gets a type outside
  the ontology (`date`, `other`, or `unknown`).
- **The base prompt still calls relationships undirected.** The ontology
  relations are directional, but the unchanged LightRAG instruction says to
  treat relationships as undirected, and the graph is stored undirected.
- **Relation definitions include Wikidata editor notes.** The definitions are
  English Wikidata property descriptions, copied verbatim, and some carry
  editing guidance such as "Use 'manner of death' (P1196)".
- **Conformance counts merged edges strictly.** An edge that LightRAG merged
  from two extractions with different labels carries both, comma-joined, and
  does not conform.
"""
DATE_NAME = re.compile(
    rf"^(?:\d{{3,4}}"
    rf"|\d{{1,2}}\s+(?:{MONTHS}),?\s+\d{{3,4}}"
    rf"|(?:{MONTHS})\s+\d{{1,2}},?\s+\d{{3,4}}"
    rf"|(?:{MONTHS})\s+\d{{3,4}})$",
    re.IGNORECASE,
)


def load(condition: str, subset: str) -> dict:
    run_dir = RUNS_DIR / condition / subset
    scores = json.loads((run_dir / "scores.json").read_text(encoding="utf-8"))
    with (run_dir / "results.jsonl").open(encoding="utf-8") as f:
        results = [json.loads(line) for line in f]
    manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
    nodes, edges = rcf.read_graph(run_dir / "lightrag" / rcf.GRAPH_FILE)
    ontology = json.loads(rcf.ONTOLOGY_PATH.read_text(encoding="utf-8"))
    date_nodes = {n["entity_id"] for n in nodes if DATE_NAME.match((n.get("entity_id") or "").strip())}
    endpoints = _edge_endpoints(run_dir / "lightrag" / rcf.GRAPH_FILE)
    return {
        "condition": condition,
        "scores": scores,
        "results": results,
        "index": [r for r in manifest["index"] if r.get("status") == "completed"][-1],
        "query": [r for r in manifest["query"] if r.get("status") == "completed"][-1],
        "graph": rcf.measure(nodes, edges, ontology),
        "nodes": len(nodes),
        "date_nodes": sorted(date_nodes),
        "date_relations": sum(s in date_nodes or t in date_nodes for s, t in endpoints),
    }


def _edge_endpoints(path: Path) -> list[tuple[str, str]]:
    graph = ET.parse(path).getroot().find("g:graph", rcf.NS)
    return [(e.get("source"), e.get("target")) for e in graph.findall("g:edge", rcf.NS)]


def pct(v: float) -> str:
    return f"{100 * v:.1f}"


def cell(agg: dict, metric: str) -> str:
    m = agg[metric]
    return f"{pct(m['mean'])} [{pct(m['ci95'][0])}, {pct(m['ci95'][1])}]"


def markdown(base: dict, treat: dict, subset: str) -> str:
    b, t = base["condition"], treat["condition"]
    lines = [
        f"# {t.capitalize()} vs {b}, {subset} (SCRUM-18)",
        "",
        f"Written by `scripts/compare_conditions.py`. Both conditions answer the same {subset} "
        "questions with the same shared configuration, answer template, query settings, and seed; "
        "they differ only in the extraction prompt (see "
        "`docs/results/prompt-diff-baseline-vs-ontology.diff`).",
        "",
        "## Provenance",
        "",
        "| | " + " | ".join([b, t]) + " |",
        "|---|---|---|",
    ]
    rows = [
        ("Index commit", lambda c: f"`{c['index']['git']['commit'][:7]}`" + (" (dirty)" if c["index"]["git"]["dirty"] else "")),
        ("Index wall-clock", lambda c: f"{c['index']['indexing_wall_s']:,.1f} s ({c['index']['seconds_per_processed_document']} s per paragraph)"),
        ("Query commit", lambda c: f"`{c['query']['git']['commit'][:7]}`" + (" (dirty)" if c["query"]["git"]["dirty"] else "")),
        ("Query LLM cache", lambda c: "on" if c["query"]["llm_cache"] else "off"),
        ("Shared config sha256", lambda c: f"`{c['query']['config_sha256'][:12]}…`"),
        ("Condition config sha256", lambda c: f"`{c['query']['condition_config_sha256'][:12]}…`"),
        ("Answer template sha256", lambda c: f"`{c['query']['answer_template']['template_sha256'][:12]}…`"),
        ("Results sha256", lambda c: f"`{c['scores']['provenance']['results_sha256'][:12]}…`"),
        ("Fallback rows changed", lambda c: str(c["query"]["normalization_fallback"]["rows_changed"])),
    ]
    for name, f in rows:
        lines.append(f"| {name} | {f(base)} | {f(treat)} |")

    lines += [
        "",
        "## Scores",
        "",
        "Percentages, with the bootstrap 95% intervals from `scripts/score.py` (1,000 resamples, "
        "seed 694). EM and F1 compare with the gold answer only; the alias columns also accept the "
        "answer entity's aliases, as the official 2WikiMultiHopQA v1.1 script does.",
        "",
        "| Group | n | Condition | " + " | ".join(label for _, label in METRICS) + " |",
        "|---|---|---|" + "---|" * len(METRICS),
    ]
    groups = [("overall", base["scores"]["overall"], treat["scores"]["overall"])]
    groups += [(g, base["scores"]["by_type"][g], treat["scores"]["by_type"][g]) for g in base["scores"]["by_type"]]
    for name, ba, ta in groups:
        for cond, agg in ((b, ba), (t, ta)):
            lines.append(f"| {name} | {agg['n']} | {cond} | " + " | ".join(cell(agg, m) for m, _ in METRICS) + " |")

    by_b = {s["question_id"]: s for s in base["scores"]["per_question"]}
    by_t = {s["question_id"]: s for s in treat["scores"]["per_question"]}
    if list(by_b) != list(by_t):
        raise SystemExit("The two runs answer different questions")
    counts = {"both right": 0, f"{b} only": 0, f"{t} only": 0, "both wrong": 0}
    lines += [
        "",
        "## Per question",
        "",
        "\"Right\" is official EM with aliases.",
        "",
        f"| # | Question ID | Type | Gold | {b} answer | {t} answer | Right |",
        "|---|---|---|---|---|---|---|",
    ]
    for n, qid in enumerate(by_b, start=1):
        sb, st = by_b[qid], by_t[qid]
        rb, rt = sb["em_alias"] == 1, st["em_alias"] == 1
        key = "both right" if rb and rt else f"{b} only" if rb else f"{t} only" if rt else "both wrong"
        counts[key] += 1
        lines.append(f"| {n} | `{qid}` | {sb['type']} | {sb['gold_answer']} | {sb['predicted_answer']} | "
                     f"{st['predicted_answer']} | {key} |")
    lines += ["", "Paired counts:", "", "| Outcome | Questions |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in counts.items()]
    ob, ot = base["scores"]["overall"]["em_alias"]["mean"], treat["scores"]["overall"]["em_alias"]["mean"]
    lines += [
        "",
        f"Overall EM with aliases is {pct(ob)} for {b} and {pct(ot)} for {t}. The conditions "
        f"disagree on {counts[f'{b} only'] + counts[f'{t} only']} of {len(by_b)} questions "
        f"({counts[f'{b} only']} {b} only, {counts[f'{t} only']} {t} only). At this sample size these "
        "numbers do not show that either condition answers better; see Limitations.",
    ]

    gb, gt = base["graph"], treat["graph"]

    def types_line(g):
        return ", ".join(f"{k} {v}" for k, v in g["entity_types"].items())

    lines += [
        "",
        "## Graphs",
        "",
        "Relation conformance and entity types are from `scripts/relation_conformance.py`. A date "
        "relation is an edge with a date-named node at either end (see the script docstring). "
        f"The {b} prompt never names the ontology types, so its count of types outside the "
        "ontology only shows how far LightRAG's default type names are from the ontology's.",
        "",
        f"| Measure | {b} | {t} |",
        "|---|---|---|",
        f"| Nodes | {base['nodes']} | {treat['nodes']} |",
        f"| Edges | {gb['relations']} | {gt['relations']} |",
        f"| Relation conformance | {gb['conforming']} / {gb['relations']} ({pct(gb['conformance'])}%) | "
        f"{gt['conforming']} / {gt['relations']} ({pct(gt['conformance'])}%) |",
        f"| Edges with several comma-joined keywords | {gb['multi_keyword_relations']} | {gt['multi_keyword_relations']} |",
        f"| Distinct entity types | {len(gb['entity_types'])} | {len(gt['entity_types'])} |",
        f"| Entities with a type outside the ontology | {gb['entities_outside_ontology_types']} of {gb['entities']} | "
        f"{gt['entities_outside_ontology_types']} of {gt['entities']} |",
        f"| Date nodes | {len(base['date_nodes'])} | {len(treat['date_nodes'])} |",
        f"| Date relations | {base['date_relations']} | {treat['date_relations']} |",
        "",
        f"Entity types, {b}: {types_line(gb)}.",
        "",
        f"Entity types, {t}: {types_line(gt)}.",
        "",
        f"Date nodes, {b}: " + ", ".join(base["date_nodes"]) + ".",
        "",
        f"Date nodes, {t}: " + ", ".join(treat["date_nodes"]) + ".",
        "",
        f"Most common non-conforming keywords, {t}: "
        + ", ".join(f"`{k}` ({v})" for k, v in list(gt["nonconforming_keywords"].items())[:15]) + ".",
    ]
    return "\n".join(lines) + "\n\n" + LIMITATIONS


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--treatment", required=True)
    parser.add_argument("--subset", required=True)
    args = parser.parse_args()
    base, treat = load(args.baseline, args.subset), load(args.treatment, args.subset)
    path = DOCS_DIR / f"{args.treatment}-vs-{args.baseline}-{args.subset}.md"
    path.write_text(markdown(base, treat, args.subset), encoding="utf-8")
    print(f"Wrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
