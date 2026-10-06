"""Share of a run's graph relations that use an ontology relation label (SCRUM-18).

    python scripts/relation_conformance.py --condition ontology --subset mini
    python scripts/relation_conformance.py --condition baseline --subset smoke10 --json

Reads runs/<condition>/<subset>/lightrag/graph_chunk_entity_relation.graphml
and ontology/ontology.json. Nothing is written.

Rule. A relation (graph edge) conforms when its `keywords` string, normalized,
equals one ontology relation label, normalized. Normalization: lowercase,
underscores to spaces, runs of whitespace collapsed to one space, outer
whitespace stripped. Nothing else is done: no synonyms, no splitting. LightRAG
merges repeated edges by joining their keywords with commas
(lightrag/operate.py:3012-3018), so an edge carrying two different labels, e.g.
"father,mother", does not conform; the report counts such edges separately.

Entity types are reported alongside: LightRAG stores them lowercased, so a node
type is "in the ontology" when it equals an ontology type name under the same
normalization. SCRUM-21 extends this measurement.

Standard library only.
"""

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS_DIR = ROOT / "runs"
ONTOLOGY_PATH = ROOT / "ontology" / "ontology.json"
GRAPH_FILE = "graph_chunk_entity_relation.graphml"
NS = {"g": "http://graphml.graphdrawing.org/xmlns"}


def normalize(text: str | None) -> str:
    return re.sub(r"\s+", " ", (text or "").lower().replace("_", " ")).strip()


def read_graph(path: Path) -> tuple[list[dict], list[dict]]:
    """Nodes and edges of a GraphML file as attribute dicts."""
    root = ET.parse(path).getroot()
    names = {k.get("id"): k.get("attr.name") for k in root.findall("g:key", NS)}
    graph = root.find("g:graph", NS)

    def attrs(el):
        return {names[d.get("key")]: d.text for d in el.findall("g:data", NS)}

    return [attrs(n) for n in graph.findall("g:node", NS)], [attrs(e) for e in graph.findall("g:edge", NS)]


def measure(nodes: list[dict], edges: list[dict], ontology: dict) -> dict:
    labels = {normalize(r["relation"]) for r in ontology["relation_types"]}
    types = {normalize(t["name"]) for t in ontology["entity_types"]}
    keywords = [normalize(e.get("keywords")) for e in edges]
    conforming = [k for k in keywords if k in labels]
    nonconforming = Counter(k for k in keywords if k not in labels)
    node_types = Counter(normalize(n.get("entity_type")) for n in nodes)
    outside = {t: n for t, n in node_types.items() if t not in types}
    return {
        "relations": len(edges),
        "conforming": len(conforming),
        "conformance": len(conforming) / len(edges) if edges else None,
        "multi_keyword_relations": sum("," in k for k in keywords),
        "labels_used": dict(sorted(Counter(conforming).items())),
        "nonconforming_keywords": dict(nonconforming.most_common()),
        "entities": len(nodes),
        "entity_types": dict(node_types.most_common()),
        "entities_outside_ontology_types": sum(outside.values()),
        "entity_types_outside_ontology": dict(sorted(outside.items(), key=lambda kv: (-kv[1], kv[0]))),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--condition", required=True)
    parser.add_argument("--subset", required=True)
    parser.add_argument("--json", action="store_true", help="print the full result as JSON")
    args = parser.parse_args()
    path = RUNS_DIR / args.condition / args.subset / "lightrag" / GRAPH_FILE
    if not path.exists():
        raise SystemExit(f"No graph: {path.relative_to(ROOT)}")
    result = measure(*read_graph(path), json.loads(ONTOLOGY_PATH.read_text(encoding="utf-8")))
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    share = "n/a" if result["conformance"] is None else f"{100 * result['conformance']:.1f}%"
    print(f"{args.condition}/{args.subset}: {result['conforming']} of {result['relations']} relations "
          f"conform ({share}); {result['multi_keyword_relations']} carry several comma-separated keywords")
    print(f"entities: {result['entities']}, {result['entities_outside_ontology_types']} with a type "
          f"outside the ontology {result['entity_types_outside_ontology']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
