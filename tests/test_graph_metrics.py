"""Tests for scripts/graph_metrics.py on a hand-built graph (SCRUM-21).

    python -m unittest discover -s tests

Every expected value below was worked out by hand from the rules in the
script docstring; see the comment on each fixture row.
"""

import sys
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import graph_metrics as gm  # noqa: E402
import relation_conformance as rcf  # noqa: E402

ONTOLOGY = {
    "entity_types": [{"name": "Human"}, {"name": "Settlement or region"}],
    "relation_types": [{"relation": "father"}, {"relation": "place of birth"}],
}

NODES = [
    # Containment: "cleopatra iv" is a run in "cleopatra iv of egypt". Both Human.
    {"entity_id": "Cleopatra IV", "entity_type": "Human"},
    {"entity_id": "Cleopatra IV of Egypt", "entity_type": "human"},
    # Normalized match after diacritics and case. Type "person" is outside.
    {"entity_id": "Björk", "entity_type": "person"},
    {"entity_id": "bjork", "entity_type": "PERSON"},
    # Normalized match after the trailing parenthetical. Type outside.
    {"entity_id": "Joystick (song)", "entity_type": "content"},
    {"entity_id": "Joystick", "entity_type": "content"},
    # "richard burke" is in two longer keys, neither containing the other:
    # ambiguous, so no link. The two earls are not linked to each other.
    {"entity_id": "Richard Burke", "entity_type": "Human"},
    {"entity_id": "Richard Burke, 2nd Earl of Clanricarde", "entity_type": "Human"},
    {"entity_id": "Richard Burke, 4th Earl of Clanricarde", "entity_type": "Human"},
    # One-token key: containment needs two tokens, so no link to "Duke of Płock".
    # "settlementorregion" is the stored form of "Settlement or region".
    {"entity_id": "Płock", "entity_type": "settlementorregion"},
    {"entity_id": "Duke of Płock", "entity_type": "title"},
]
# Entity types in the ontology: rows 1, 2, 7, 8, 9, 10 -> 6 of 11.
# Clusters: {Cleopatra IV, Cleopatra IV of Egypt}, {Björk, bjork},
# {Joystick, Joystick (song)} -> 3 clusters, 6 entities, rate (6 - 3) / 11.

EDGES = [
    {"keywords": "father"},          # conforms
    {"keywords": "Father"},          # conforms after lowercasing
    {"keywords": "place_of_birth"},  # conforms after underscores to spaces
    {"keywords": "father,mother"},   # merged edge: does not conform
    {"keywords": "son"},             # not an ontology label
]


class NameTokensTest(unittest.TestCase):
    def test_steps(self):
        self.assertEqual(gm.name_tokens("Björk Guðmundsdóttir"), ("bjork", "guðmundsdottir"))
        self.assertEqual(gm.name_tokens("Joystick (song)"), ("joystick",))
        self.assertEqual(gm.name_tokens("Kool& The Gang"), ("kool", "the", "gang"))
        self.assertEqual(gm.name_tokens("The Dazz Band"), ("dazz", "band"))
        self.assertEqual(gm.name_tokens("Płock"), ("płock",))
        self.assertEqual(gm.name_tokens("Hashim Ibn' Abd Manaf"), ("hashim", "ibn", "abd", "manaf"))
        # A lone article is kept, so "The" still has a key.
        self.assertEqual(gm.name_tokens("The"), ("the",))


class DuplicateClustersTest(unittest.TestCase):
    def test_joined_tokens_match(self):
        clusters, reasons = gm.duplicate_clusters(["DieTotenHosen", "Die Toten Hosen"])
        self.assertEqual(clusters, [["Die Toten Hosen", "DieTotenHosen"]])
        self.assertEqual(reasons, {("Die Toten Hosen", "DieTotenHosen"): "normalized match"})

    def test_nested_containers_link_through_the_minimal_one(self):
        names = ["Cleopatra IV", "Cleopatra IV of Egypt", "Queen Cleopatra IV of Egypt"]
        clusters, reasons = gm.duplicate_clusters(names)
        self.assertEqual(clusters, [sorted(names)])
        self.assertEqual(reasons, {
            ("Cleopatra IV", "Cleopatra IV of Egypt"): "containment",
            ("Cleopatra IV", "Queen Cleopatra IV of Egypt"): "same cluster",
            ("Cleopatra IV of Egypt", "Queen Cleopatra IV of Egypt"): "containment",
        })

    def test_ambiguous_containment_does_not_link(self):
        clusters, _ = gm.duplicate_clusters(["Siemowit V", "Siemowit V of Masovia", "Siemowit V of Rawa"])
        self.assertEqual(clusters, [])


class MetricsTest(unittest.TestCase):
    def setUp(self):
        self.m = gm.metrics(NODES, EDGES, ONTOLOGY)

    def test_entity_type_conformance(self):
        self.assertEqual(self.m["entities"], 11)
        self.assertEqual(self.m["entities_in_ontology_types"], 6)
        self.assertEqual(self.m["entities_outside_ontology_types"], 5)
        self.assertEqual(Fraction(self.m["entity_type_conformance"]).limit_denominator(), Fraction(6, 11))
        self.assertEqual(self.m["entity_types_outside_ontology"], {"content": 2, "person": 2, "title": 1})

    def test_relation_conformance(self):
        self.assertEqual(self.m["relations"], 5)
        self.assertEqual(self.m["conforming"], 3)
        self.assertEqual(self.m["conformance"], 0.6)
        self.assertEqual(self.m["multi_keyword_relations"], 1)
        self.assertEqual(self.m["labels_used"], {"father": 2, "place of birth": 1})

    def test_duplicates(self):
        self.assertEqual(self.m["clusters"], [
            ["Björk", "bjork"],
            ["Cleopatra IV", "Cleopatra IV of Egypt"],
            ["Joystick", "Joystick (song)"],
        ])
        self.assertEqual(self.m["duplicate_clusters"], 3)
        self.assertEqual(self.m["entities_in_duplicate_clusters"], 6)
        self.assertEqual(Fraction(self.m["duplicate_rate"]).limit_denominator(), Fraction(3, 11))
        self.assertEqual(self.m["flagged_pairs"], 3)
        self.assertEqual({p["reason"] for p in self.m["pairs"]}, {"normalized match", "containment"})

    def test_reads_graphml(self):
        graphml = """<?xml version="1.0" encoding="utf-8"?>
<graphml xmlns="http://graphml.graphdrawing.org/xmlns">
  <key id="d0" for="node" attr.name="entity_id" attr.type="string"/>
  <key id="d1" for="node" attr.name="entity_type" attr.type="string"/>
  <key id="d2" for="edge" attr.name="keywords" attr.type="string"/>
  <graph edgedefault="undirected">
    <node id="Joystick"><data key="d0">Joystick</data><data key="d1">human</data></node>
    <node id="Joystick (song)"><data key="d0">Joystick (song)</data><data key="d1">content</data></node>
    <edge source="Joystick" target="Joystick (song)"><data key="d2">father</data></edge>
  </graph>
</graphml>"""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "lightrag" / rcf.GRAPH_FILE
            path.parent.mkdir()
            path.write_text(graphml, encoding="utf-8")
            m = gm.metrics(*rcf.read_graph(gm.graph_path(Path(tmp))), ONTOLOGY)
        self.assertEqual((m["entities_in_ontology_types"], m["conforming"], m["duplicate_clusters"]), (1, 1, 1))
        self.assertEqual(m["duplicate_rate"], 0.5)


class SampleTest(unittest.TestCase):
    def test_one_pair_per_drawn_cluster(self):
        runs = [("g1", Path("."), gm.metrics(NODES, EDGES, ONTOLOGY)),
                ("g2", Path("."), gm.metrics(NODES[:2], [], ONTOLOGY))]
        drawn = gm.sample_pairs(runs)
        # 4 clusters in all, fewer than the sample size, so every cluster once.
        self.assertEqual(len(drawn), 4)
        self.assertEqual(sorted((g, a) for g, a, _, _ in drawn),
                         [("g1", "Björk"), ("g1", "Cleopatra IV"), ("g1", "Joystick"), ("g2", "Cleopatra IV")])
        self.assertEqual(drawn, gm.sample_pairs(runs))


if __name__ == "__main__":
    unittest.main()
