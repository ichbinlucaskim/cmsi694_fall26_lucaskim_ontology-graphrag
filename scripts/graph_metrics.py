"""Entity-type conformance, relation conformance, and duplicate-entity rate of a graph (SCRUM-21).

    python scripts/graph_metrics.py --run-dir runs/ontology/smoke10
    python scripts/graph_metrics.py --run-dir runs/baseline/smoke10 --ontology ontology/ontology.json --json
    python scripts/graph_metrics.py --subset smoke10 \\
        --run baseline=runs/baseline/smoke10 --run ontology=runs/ontology/smoke10 \\
        --out docs/results/graph-metrics-smoke10.md \\
        --sample-out docs/results/duplicate-sample-smoke10.md

A run directory holds lightrag/graph_chunk_entity_relation.graphml. The script
reads it and the ontology file and writes nothing unless --out or --sample-out
is given. Standard library only.

Entity-type conformance and relation conformance are the rules in
scripts/relation_conformance.py, unchanged and not repeated here:

- An entity conforms when its type, lowercased with whitespace and underscores
  removed (the form LightRAG stores), equals an ontology entity type name in
  the same form. The comparison is case-insensitive.
- A relation conforms when its keywords, normalized, equal one ontology
  relation label, normalized. Comma-joined keywords from merged edges do not
  conform.

A baseline graph was extracted with LightRAG's default prompt, which never
shows the ontology, so its entity-type conformance only measures how close
LightRAG's default type names are to the ontology's.

Duplicates. Two entities are flagged as likely naming the same thing when
either rule below links them; clusters are the connected components of those
links, and a cluster has two or more entities.

1. Normalized match. Both names have the same key. The key of a name is made
   by these steps, in order:
   a. Unicode NFKD, then drop combining marks (diacritics): "Björk" -> "Bjork".
   b. Case-fold.
   c. Drop one trailing parenthetical: "Joystick (song)" -> "joystick".
   d. Replace every character that is not a letter or digit with a space
      (punctuation, including apostrophes and "&"). Letters that have no
      decomposition, such as "ł" in "Płock", are kept.
   e. Split on whitespace and drop one leading article ("the", "a", "an").
   The key is the remaining tokens. Two names match when their tokens joined
   without spaces are equal, so "DieTotenHosen" matches "Die Toten Hosen".
2. Containment. A key of at least two tokens is a contiguous run of tokens in
   a longer key: "cleopatra iv" in "cleopatra iv of egypt". It links only
   when unambiguous: among the longer keys that contain it, the minimal ones
   (those containing no other container) must be exactly one. So "richard
   burke" is not linked when both "richard burke 2nd earl of clanricarde" and
   "richard burke 4th earl of clanricarde" exist.

duplicate rate = (entities in clusters - clusters) / entities, the share of
entities that would disappear if each cluster were merged into one.

A flagged pair is any two entities in the same cluster. Its reason is
"normalized match", "containment", or "same cluster" (linked only through
other members).

Hand-check sample (--sample-out). 20 clusters are drawn without replacement
from the clusters of all given graphs with random.Random(694), then one pair
is drawn from each drawn cluster with the same generator. Drawing clusters
first keeps one large cluster from filling the sample.
"""

import argparse
import hashlib
import itertools
import json
import random
import re
import sys
import unicodedata
from pathlib import Path

import relation_conformance as rcf

ROOT = Path(__file__).resolve().parent.parent
ARTICLES = {"the", "a", "an"}
TRAILING_PAREN = re.compile(r"\s*\([^()]*\)\s*$")
NON_ALNUM = re.compile(r"[\W_]+")
SAMPLE_SIZE = 20
SAMPLE_SEED = 694


def name_tokens(name: str) -> tuple[str, ...]:
    """The duplicate key of an entity name, as tokens (rule 1, steps a to e)."""
    text = unicodedata.normalize("NFKD", name or "")
    text = "".join(c for c in text if not unicodedata.combining(c)).casefold()
    text = TRAILING_PAREN.sub("", text)
    tokens = NON_ALNUM.sub(" ", text).split()
    if len(tokens) > 1 and tokens[0] in ARTICLES:
        tokens = tokens[1:]
    return tuple(tokens)


def _contains(longer: tuple[str, ...], shorter: tuple[str, ...]) -> bool:
    n = len(shorter)
    return len(longer) > n and any(longer[i:i + n] == shorter for i in range(len(longer) - n + 1))


def duplicate_clusters(names: list[str]) -> tuple[list[list[str]], dict[tuple[str, str], str]]:
    """Clusters of names (sorted) and the reason for every flagged pair (a < b)."""
    by_key: dict[str, list[str]] = {}
    tokens_of: dict[str, tuple[str, ...]] = {}
    for name in sorted(set(names)):
        tokens = name_tokens(name)
        key = "".join(tokens)
        if not key:
            continue
        by_key.setdefault(key, []).append(name)
        tokens_of.setdefault(key, tokens)

    parent = {name: name for group in by_key.values() for name in group}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    direct: dict[tuple[str, str], str] = {}
    for group in by_key.values():
        for a, b in itertools.combinations(group, 2):
            union(a, b)
            direct[(a, b)] = "normalized match"

    keys = sorted(by_key)
    for short in keys:
        st = tokens_of[short]
        if len(st) < 2:
            continue
        containers = [k for k in keys if _contains(tokens_of[k], st)]
        minimal = [k for k in containers if not any(_contains(tokens_of[k], tokens_of[o]) for o in containers if o != k)]
        if len(minimal) != 1:
            continue
        for a in by_key[short]:
            for b in by_key[minimal[0]]:
                union(a, b)
                direct.setdefault(tuple(sorted((a, b))), "containment")

    members: dict[str, list[str]] = {}
    for name in parent:
        members.setdefault(find(name), []).append(name)
    clusters = sorted((sorted(m) for m in members.values() if len(m) > 1), key=lambda c: (-len(c), c))
    reasons = {}
    for cluster in clusters:
        for a, b in itertools.combinations(cluster, 2):
            reasons[(a, b)] = direct.get((a, b), "same cluster")
    return clusters, reasons


def metrics(nodes: list[dict], edges: list[dict], ontology: dict) -> dict:
    result = rcf.measure(nodes, edges, ontology)
    clusters, reasons = duplicate_clusters([n.get("entity_id") or "" for n in nodes])
    in_clusters = sum(len(c) for c in clusters)
    result.update({
        "duplicate_clusters": len(clusters),
        "entities_in_duplicate_clusters": in_clusters,
        "duplicate_rate": (in_clusters - len(clusters)) / len(nodes) if nodes else None,
        "flagged_pairs": len(reasons),
        "clusters": clusters,
        "pairs": [{"a": a, "b": b, "reason": r} for (a, b), r in sorted(reasons.items())],
    })
    return result


def graph_path(run_dir: Path) -> Path:
    path = run_dir / "lightrag" / rcf.GRAPH_FILE
    if not path.exists():
        raise SystemExit(f"No graph: {path}")
    return path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pct(v: float | None) -> str:
    return "n/a" if v is None else f"{100 * v:.1f}%"


def report(runs: list[tuple[str, Path, dict]], ontology_path: Path, subset: str) -> str:
    labels = [label for label, _, _ in runs]
    head = "| Measure | " + " | ".join(labels) + " |"
    rule = "|---|" + "---|" * len(runs)

    def row(name, f):
        return f"| {name} | " + " | ".join(f(m) for _, _, m in runs) + " |"

    lines = [
        f"# Graph metrics, {subset} (SCRUM-21)",
        "",
        "Written by `scripts/graph_metrics.py`, which documents every rule in its docstring. "
        "Each measure is shown with the counts behind it.",
        "",
        "## Inputs",
        "",
        f"Ontology: `{ontology_path.relative_to(ROOT) if ontology_path.is_relative_to(ROOT) else ontology_path}` "
        f"(sha256 `{sha256(ontology_path)[:12]}…`).",
        "",
        "| Graph | Run directory | GraphML sha256 |",
        "|---|---|---|",
    ]
    for label, run_dir, _ in runs:
        lines.append(f"| {label} | `runs/{run_dir.parent.name}/{run_dir.name}` | `{sha256(graph_path(run_dir))[:12]}…` |")
    lines += [
        "",
        "## Metrics",
        "",
        head,
        rule,
        row("Entities", lambda m: str(m["entities"])),
        row("Relations", lambda m: str(m["relations"])),
        row("Entity-type conformance", lambda m: f"{m['entities_in_ontology_types']} / {m['entities']} ({pct(m['entity_type_conformance'])})"),
        row("Relation conformance", lambda m: f"{m['conforming']} / {m['relations']} ({pct(m['conformance'])})"),
        row("Relations with comma-joined keywords", lambda m: str(m["multi_keyword_relations"])),
        row("Duplicate clusters", lambda m: str(m["duplicate_clusters"])),
        row("Entities in duplicate clusters", lambda m: str(m["entities_in_duplicate_clusters"])),
        row("Duplicate rate", lambda m: f"({m['entities_in_duplicate_clusters']} - {m['duplicate_clusters']}) / {m['entities']} ({pct(m['duplicate_rate'])})"),
        row("Flagged duplicate pairs", lambda m: str(m["flagged_pairs"])),
        "",
        "The baseline prompt never showed the ontology, so the baseline's entity-type conformance "
        "reflects only how close LightRAG's default type names (person, organization, location, ...) "
        "are to the ontology's type names. It is not a measure of the baseline following the ontology.",
        "",
        "## Entity types",
        "",
    ]
    for label, _, m in runs:
        outside = ", ".join(f"{t or '(empty)'} {n}" for t, n in m["entity_types_outside_ontology"].items()) or "none"
        lines += [
            f"{label}, all types: " + ", ".join(f"{t or '(empty)'} {n}" for t, n in m["entity_types"].items()) + ".",
            "",
            f"{label}, types outside the ontology: {outside}.",
            "",
        ]
    lines += ["## Duplicate clusters", ""]
    for label, _, m in runs:
        lines += [f"### {label}", ""]
        lines += [f"- " + "; ".join(f"`{n}`" for n in c) for c in m["clusters"]] or ["None."]
        lines.append("")
    return "\n".join(lines)


def sample_pairs(runs: list[tuple[str, Path, dict]]) -> list[tuple[str, str, str, str]]:
    """SAMPLE_SIZE flagged pairs: seeded draw of clusters across graphs, then one pair from each."""
    rng = random.Random(SAMPLE_SEED)
    clusters = [(label, c) for label, _, m in runs for c in m["clusters"]]
    reasons = {(label, p["a"], p["b"]): p["reason"] for label, _, m in runs for p in m["pairs"]}
    drawn = []
    for label, cluster in rng.sample(clusters, min(SAMPLE_SIZE, len(clusters))):
        a, b = rng.choice(list(itertools.combinations(cluster, 2)))
        drawn.append((label, a, b, reasons[(label, a, b)]))
    return sorted(drawn)


def sample_checklist(runs: list[tuple[str, Path, dict]], subset: str) -> str:
    drawn = sample_pairs(runs)
    lines = [
        f"# Duplicate sample, {subset} (SCRUM-21)",
        "",
        f"Written by `scripts/graph_metrics.py`. {len(drawn)} of the "
        + " and ".join(f"{m['duplicate_clusters']} {label}" for label, _, m in runs)
        + f" duplicate clusters were drawn without replacement with `random.Random({SAMPLE_SEED})`, "
        "and one flagged pair was drawn from each with the same generator. Drawing clusters first "
        "keeps a large cluster from filling the sample: the largest has "
        f"{max(len(c) for _, _, m in runs for c in m['clusters'])} entities and would contribute "
        f"{max(len(c) * (len(c) - 1) // 2 for _, _, m in runs for c in m['clusters'])} of the "
        f"{sum(m['flagged_pairs'] for _, _, m in runs)} flagged pairs to a uniform draw. A pair is "
        "two entities in the same duplicate cluster; the reason is the rule that linked them (see "
        "the script docstring).",
        "",
        "Fill in the last column with y if both names refer to the same real-world entity in the "
        "source paragraphs, n otherwise. Precision = y / (y + n).",
        "",
        "| # | Graph | Entity A | Entity B | Reason | Same entity? (y/n) |",
        "|---|---|---|---|---|---|",
    ]
    for i, (label, a, b, reason) in enumerate(drawn, 1):
        a, b = (x.replace("|", "\\|") for x in (a, b))
        lines.append(f"| {i} | {label} | {a} | {b} | {reason} |  |")
    lines += ["", "Precision: _ / " + str(len(drawn)), ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--run-dir", type=Path, help="one run directory; prints its metrics")
    parser.add_argument("--run", action="append", default=[], metavar="LABEL=DIR",
                        help="a labeled run directory for --out and --sample-out (repeatable)")
    parser.add_argument("--ontology", type=Path, default=rcf.ONTOLOGY_PATH)
    parser.add_argument("--subset", default="", help="subset name for report titles")
    parser.add_argument("--out", type=Path, help="write the metrics report here")
    parser.add_argument("--sample-out", type=Path, help="write the duplicate sample checklist here")
    parser.add_argument("--json", action="store_true", help="print the full result as JSON")
    args = parser.parse_args()
    ontology = json.loads(args.ontology.read_text(encoding="utf-8"))

    runs = []
    for spec in args.run + ([f"run={args.run_dir}"] if args.run_dir else []):
        label, _, run_dir = spec.partition("=")
        run_dir = Path(run_dir).resolve()
        runs.append((label, run_dir, metrics(*rcf.read_graph(graph_path(run_dir)), ontology)))
    if not runs:
        parser.error("give --run-dir or --run")

    if args.out:
        args.out.write_text(report(runs, args.ontology.resolve(), args.subset), encoding="utf-8")
    if args.sample_out:
        args.sample_out.write_text(sample_checklist(runs, args.subset), encoding="utf-8")
    for label, run_dir, m in runs:
        if args.json:
            print(json.dumps({"run": label, "run_dir": str(run_dir), **m}, ensure_ascii=False, indent=2))
            continue
        print(f"{label} ({run_dir}): entity types {m['entities_in_ontology_types']}/{m['entities']} "
              f"({pct(m['entity_type_conformance'])}); relations {m['conforming']}/{m['relations']} "
              f"({pct(m['conformance'])}); duplicates {m['duplicate_clusters']} clusters, "
              f"{m['entities_in_duplicate_clusters']} entities, rate {pct(m['duplicate_rate'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
