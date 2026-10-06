"""Tests for scripts/score.py on a hand-built fixture (SCRUM-19).

    python -m unittest discover -s tests

Every expected value below was worked out by hand from the official v1.1
definitions; see the comment on each fixture row.
"""

import json
import sys
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import score  # noqa: E402


def row(qid, qtype, predicted, raw, gold, retrieved, gold_ids):
    return {
        "question_id": qid,
        "type": qtype,
        "gold_answer": gold,
        "predicted_answer": predicted,
        "predicted_answer_raw": raw,
        "retrieved_paragraph_ids": retrieved,
        "gold_paragraph_ids": gold_ids,
    }


ROWS = [
    # Article and case removed: EM 1, F1 1. Both gold paragraphs among 3 retrieved.
    row("q1", "comparison", "The Eiffel Tower", "The Eiffel Tower", "Eiffel Tower",
        ["a", "b", "x"], ["a", "b"]),
    # Tokens {paris, france} vs {paris}: P 1/2, R 1, F1 2/3. The alias
    # "Paris, France" normalizes to "paris france": EM and F1 1 with aliases.
    # One of two gold paragraphs retrieved. Raw output needed the fallback.
    row("q2", "compositional", "Paris France", "Paris France [1].", "Paris",
        ["a"], ["a", "c"]),
    # Wrong yes/no: everything 0. Nothing retrieved.
    row("q3", "comparison", "yes", "yes", "no", [], ["d"]),
    # Punctuation and case removed: EM 1, F1 1. Three of four gold paragraphs.
    # Raw output had a References section: fallback.
    row("q4", "bridge_comparison", "no", "no\n\n### References\n- [1] X", "No.",
        ["e", "f", "g", "z", "y"], ["e", "f", "g", "h"]),
    # Tokens {john, smith, jr} vs {john, smith}: P 2/3, R 1, F1 4/5. EM 0.
    row("q5", "inference", "John Smith Jr", " John Smith Jr\n", "John Smith",
        ["i", "j"], ["i", "j"]),
    # Official special case: a "yes" prediction that differs from the
    # normalized gold scores F1 0, although one token overlaps.
    row("q6", "inference", "yes", "yes", "yes it is", ["k"], ["k", "l"]),
]
META = {
    "q1": {"answer": "Eiffel Tower", "answer_id": "Q1"},
    "q2": {"answer": "Paris", "answer_id": "Q2"},
    "q3": {"answer": "no", "answer_id": ""},
    "q4": {"answer": "No.", "answer_id": ""},
    "q5": {"answer": "John Smith", "answer_id": "Q5"},
    "q6": {"answer": "yes it is", "answer_id": ""},
}
ALIASES = {"Q2": ["Paris, France", "Parisian"], "Q5": ["J. Smith"]}

EXPECTED = {
    #        em  em_alias  f1             f1_alias       recall
    "q1": (1, 1, Fraction(1), Fraction(1), Fraction(1)),
    "q2": (0, 1, Fraction(2, 3), Fraction(1), Fraction(1, 2)),
    "q3": (0, 0, Fraction(0), Fraction(0), Fraction(0)),
    "q4": (1, 1, Fraction(1), Fraction(1), Fraction(3, 4)),
    "q5": (0, 0, Fraction(4, 5), Fraction(4, 5), Fraction(1)),
    "q6": (0, 0, Fraction(0), Fraction(0), Fraction(1, 2)),
}
RETRIEVED = {"q1": 3, "q2": 1, "q3": 0, "q4": 5, "q5": 2, "q6": 1}
FALLBACK = {"q2", "q4"}


class OfficialMetricsTest(unittest.TestCase):
    def test_normalize_answer(self):
        self.assertEqual(score.normalize_answer("  The  Eiffel-Tower, an icon. "), "eiffeltower icon")

    def test_f1_special_tokens(self):
        self.assertEqual(score.f1_score("no", "no answer"), 0.0)
        self.assertEqual(score.f1_score("no answer", "no"), 0.0)
        self.assertEqual(score.f1_score("No.", "no"), 1.0)


class FixtureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = score.score_rows(ROWS, META, ALIASES)

    def test_per_question(self):
        for s in self.report["per_question"]:
            em, em_alias, f1, f1_alias, recall = EXPECTED[s["question_id"]]
            with self.subTest(question=s["question_id"]):
                self.assertEqual(s["em"], em)
                self.assertEqual(s["em_alias"], em_alias)
                self.assertEqual(s["f1"], float(f1))
                self.assertEqual(s["f1_alias"], float(f1_alias))
                self.assertEqual(s["retrieval_recall"], float(recall))
                self.assertEqual(s["paragraphs_retrieved"], RETRIEVED[s["question_id"]])
                self.assertEqual(s["fallback_used"], s["question_id"] in FALLBACK)

    def test_overall(self):
        overall = self.report["overall"]
        self.assertEqual(overall["n"], 6)
        for i, metric in enumerate(score.METRICS):
            expected = sum(Fraction(v[i]) for v in EXPECTED.values()) / 6
            with self.subTest(metric=metric):
                self.assertAlmostEqual(overall[metric]["mean"], float(expected), places=12)
        # Hand totals: EM 2/6, EM aliases 3/6, F1 (1 + 2/3 + 1 + 4/5)/6 = 26/45,
        # F1 aliases (1 + 1 + 1 + 4/5)/6 = 19/30, recall (1 + 1/2 + 3/4 + 1 + 1/2)/6 = 5/8.
        self.assertAlmostEqual(overall["em"]["mean"], 1 / 3, places=12)
        self.assertAlmostEqual(overall["em_alias"]["mean"], 1 / 2, places=12)
        self.assertAlmostEqual(overall["f1"]["mean"], 26 / 45, places=12)
        self.assertAlmostEqual(overall["f1_alias"]["mean"], 19 / 30, places=12)
        self.assertAlmostEqual(overall["retrieval_recall"]["mean"], 5 / 8, places=12)
        self.assertAlmostEqual(overall["mean_paragraphs_retrieved"], 2.0, places=12)
        self.assertEqual(overall["fallback_rows"], 2)
        self.assertEqual(self.report["fallback_question_ids"], ["q2", "q4"])

    def test_by_type(self):
        by_type = self.report["by_type"]
        self.assertEqual(
            list(by_type), ["inference", "compositional", "comparison", "bridge_comparison"]
        )
        self.assertEqual({t: a["n"] for t, a in by_type.items()},
                         {"inference": 2, "compositional": 1, "comparison": 2, "bridge_comparison": 1})
        self.assertAlmostEqual(by_type["inference"]["f1"]["mean"], 2 / 5, places=12)
        self.assertAlmostEqual(by_type["comparison"]["em"]["mean"], 1 / 2, places=12)
        self.assertAlmostEqual(by_type["comparison"]["retrieval_recall"]["mean"], 1 / 2, places=12)
        self.assertAlmostEqual(by_type["inference"]["retrieval_recall"]["mean"], 3 / 4, places=12)

    def test_confidence_intervals(self):
        for group in [self.report["overall"], *self.report["by_type"].values()]:
            for metric in score.METRICS:
                low, high = group[metric]["ci95"]
                self.assertLessEqual(low, group[metric]["mean"] + 1e-12)
                self.assertGreaterEqual(high, group[metric]["mean"] - 1e-12)
        # A single question, or identical values, gives a zero-width interval.
        self.assertEqual(self.report["by_type"]["compositional"]["f1"]["ci95"], [2 / 3, 2 / 3])
        self.assertEqual(score.bootstrap_ci([0.25] * 7), [0.25, 0.25])
        # Seeded: the same input always gives the same interval.
        values = [1, 0, 0, 1, 0, 1, 1, 0, 0, 0]
        self.assertEqual(score.bootstrap_ci(values), score.bootstrap_ci(values))

    def test_gold_answer_mismatch_is_refused(self):
        bad = [dict(ROWS[0], gold_answer="Louvre")]
        with self.assertRaises(ValueError):
            score.score_rows(bad, META, ALIASES)


class AliasFileTest(unittest.TestCase):
    def test_aliases_and_demonyms_are_merged(self):
        lines = [
            {"Q_id": "Q2", "aliases": ["Paris, France"], "demonyms": ["Parisian"]},
            {"Q_id": "Q9", "aliases": ["Elsewhere"], "demonyms": []},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "id_aliases.json"
            path.write_text("\n".join(json.dumps(x) for x in lines) + "\n", encoding="utf-8")
            self.assertEqual(score.load_aliases(path, {"Q2"}), {"Q2": ["Paris, France", "Parisian"]})


if __name__ == "__main__":
    unittest.main()
