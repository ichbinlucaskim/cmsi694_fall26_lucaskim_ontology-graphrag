"""Tests for run labels, results tags and score output paths (SCRUM-33).

    python -m unittest discover -s tests

No model is called. The run_condition tests are skipped when lightrag is not
installed; the score tests use the hand-built fixture from test_score.py.
"""

import argparse
import asyncio
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import score  # noqa: E402
from test_score import ALIASES, META, ROWS  # noqa: E402

try:
    import run_condition as rc
except ImportError:  # pragma: no cover
    rc = None

KEYS = {"config_sha256": "c" * 64, "index_settings_sha256": "i" * 64, "seed": 694, "llm_cache": False}
QUESTIONS = [{"_id": f"q{i}"} for i in range(1, 4)]


def stub(calls: list[str]):
    async def answer(question):
        calls.append(question["_id"])
        return {"question_id": question["_id"]}
    return answer


@unittest.skipIf(rc is None, "lightrag not installed")
class RunPathTest(unittest.TestCase):
    def test_unlabelled_run_dir_is_unchanged(self):
        self.assertEqual(rc.run_dir_for("baseline", "smoke10"), rc.RUNS_DIR / "baseline" / "smoke10")

    def test_labelled_run_dir(self):
        self.assertEqual(rc.run_dir_for("ontology", "study50", "v2"),
                         rc.RUNS_DIR / "ontology-v2" / "study50")

    def test_results_names(self):
        self.assertEqual(rc.results_name(), "results.jsonl")
        self.assertEqual(rc.results_name("r2"), "results-r2.jsonl")

    def test_label_characters(self):
        for good in ["v2", "r-2", "2026-10-29"]:
            self.assertEqual(rc.label(good), good)
        for bad in ["", "V2", "v_2", "v2/x", "../v2", "v 2"]:
            with self.subTest(label=bad), self.assertRaises(argparse.ArgumentTypeError):
                rc.label(bad)

    def test_resume_is_per_results_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            first = run_dir / rc.results_name()
            asyncio.run(rc.answer_questions(QUESTIONS, first, KEYS, stub([]), {}))
            before = first.read_bytes()
            # A repeat with another seed under a tag is not refused and leaves
            # the first results alone.
            calls = []
            repeat = run_dir / rc.results_name("r2")
            other = {**KEYS, "seed": 1}
            asyncio.run(rc.answer_questions(QUESTIONS, repeat, other, stub(calls), {}))
            self.assertEqual(calls, ["q1", "q2", "q3"])
            self.assertEqual(first.read_bytes(), before)
            # Each file resumes on its own, and each refuses the other's settings.
            calls = []
            asyncio.run(rc.answer_questions(QUESTIONS, repeat, other, stub(calls), {}))
            self.assertEqual(calls, [])
            with self.assertRaises(SystemExit):
                asyncio.run(rc.answer_questions(QUESTIONS, first, other, stub([]), {}))
            with self.assertRaises(SystemExit):
                asyncio.run(rc.answer_questions(QUESTIONS, repeat, KEYS, stub([]), {}))


class ScorePathTest(unittest.TestCase):
    def test_default_paths(self):
        run_dir = score.RUNS_DIR / "ontology-v2" / "smoke10"
        self.assertEqual(score.output_paths(run_dir), {
            "results": run_dir / "results.jsonl",
            "scores": run_dir / "scores.json",
            "summary": score.RESULTS_DOCS_DIR / "ontology-v2-smoke10-scores.md",
        })

    def test_tagged_paths(self):
        run_dir = score.RUNS_DIR / "ontology-v2" / "study50"
        self.assertEqual(score.output_paths(run_dir, "r2"), {
            "results": run_dir / "results-r2.jsonl",
            "scores": run_dir / "scores-r2.json",
            "summary": score.RESULTS_DOCS_DIR / "ontology-v2-study50-r2-scores.md",
        })

    def test_out_dir(self):
        run_dir, out = Path("/x/runs/baseline/study50"), Path("/y")
        paths = score.output_paths(run_dir, out_dir=out)
        self.assertEqual(paths["results"], run_dir / "results.jsonl")
        self.assertEqual(paths["scores"], out / "scores.json")
        self.assertEqual(paths["summary"], out / "baseline-study50-scores.md")


class ScoreMainTest(unittest.TestCase):
    """score.main on a temporary run directory built from the fixture rows."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.run_dir = base / "runs" / "ontology-v2" / "smoke10"
        self.run_dir.mkdir(parents=True)
        self.docs = base / "docs"
        self.docs.mkdir()
        aliases = base / "id_aliases.json"
        aliases.write_text("".join(
            json.dumps({"Q_id": q, "aliases": a, "demonyms": []}) + "\n" for q, a in ALIASES.items()
        ), encoding="utf-8")
        query_runs = []
        for tag, rows in [(None, ROWS), ("r2", ROWS[:3])]:
            path = self.run_dir / ("results.jsonl" if tag is None else f"results-{tag}.jsonl")
            path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
            record = {"status": "completed", "started_at": "2026-10-29T00:00:00+00:00",
                      "ended_at": "2026-10-29T01:00:00+00:00", "git": {"commit": "abc"},
                      "config_sha256": "c" * 64, "results_sha256": score.sha256_of(path)}
            if tag is not None:
                record["results_tag"] = tag
            query_runs.append(record)
        (self.run_dir / "run_manifest.json").write_text(json.dumps({
            "condition": "ontology", "subset": "smoke10", "query": query_runs,
        }), encoding="utf-8")
        for patch in [
            mock.patch.object(score, "RESULTS_DOCS_DIR", self.docs),
            mock.patch.object(score, "ALIASES_PATH", aliases),
            mock.patch.object(score, "load_question_meta", return_value=META),
        ]:
            patch.start()
            self.addCleanup(patch.stop)

    def tearDown(self):
        self.tmp.cleanup()

    def main(self, *argv: str) -> str:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(score.main(["--run-dir", str(self.run_dir), *argv]), 0)
        return out.getvalue()

    def test_writes_next_to_results_and_to_docs(self):
        self.main()
        report = json.loads((self.run_dir / "scores.json").read_text(encoding="utf-8"))
        self.assertEqual(report["overall"]["n"], 6)
        self.assertEqual(report["run"], "ontology-v2")
        summary = (self.docs / "ontology-v2-smoke10-scores.md").read_text(encoding="utf-8")
        self.assertTrue(summary.startswith("# Scores: ontology-v2, smoke10\n"))

    def test_results_tag_scores_its_own_file(self):
        self.main("--results-tag", "r2")
        report = json.loads((self.run_dir / "scores-r2.json").read_text(encoding="utf-8"))
        self.assertEqual(report["overall"]["n"], 3)
        self.assertTrue((self.docs / "ontology-v2-smoke10-r2-scores.md").exists())
        self.assertFalse((self.run_dir / "scores.json").exists())

    def test_refuses_to_overwrite_and_names_the_file(self):
        self.main()
        summary = self.docs / "ontology-v2-smoke10-scores.md"
        summary.write_text("hand edit\n", encoding="utf-8")
        scores_before = (self.run_dir / "scores.json").read_bytes()
        with self.assertRaises(SystemExit) as ctx:
            score.main(["--run-dir", str(self.run_dir)])
        self.assertIn("ontology-v2-smoke10-scores.md", str(ctx.exception))
        self.assertIn("scores.json", str(ctx.exception))
        self.assertEqual(summary.read_text(encoding="utf-8"), "hand edit\n")
        self.assertEqual((self.run_dir / "scores.json").read_bytes(), scores_before)
        self.main("--overwrite")
        self.assertNotEqual(summary.read_text(encoding="utf-8"), "hand edit\n")

    def test_refuses_when_only_one_output_exists(self):
        (self.docs / "ontology-v2-smoke10-scores.md").write_text("x\n", encoding="utf-8")
        with self.assertRaises(SystemExit) as ctx:
            score.main(["--run-dir", str(self.run_dir)])
        self.assertIn("ontology-v2-smoke10-scores.md", str(ctx.exception))
        self.assertFalse((self.run_dir / "scores.json").exists())

    def test_out_dir_leaves_the_run_dir_alone(self):
        out = Path(self.tmp.name) / "out"
        self.main("--out-dir", str(out))
        self.assertTrue((out / "scores.json").exists())
        self.assertTrue((out / "ontology-v2-smoke10-scores.md").exists())
        self.assertFalse((self.run_dir / "scores.json").exists())
        self.assertEqual(list(self.docs.iterdir()), [])

    def test_condition_and_subset_use_the_same_paths_and_refusal(self):
        with mock.patch.object(score, "RUNS_DIR", self.run_dir.parent.parent):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                score.main(["--condition", "ontology-v2", "--subset", "smoke10"])
            self.assertTrue((self.run_dir / "scores.json").exists())
            self.assertTrue((self.docs / "ontology-v2-smoke10-scores.md").exists())
            with self.assertRaises(SystemExit) as ctx:
                score.main(["--condition", "ontology-v2", "--subset", "smoke10"])
            self.assertIn("Refusing to overwrite", str(ctx.exception))

    def test_tag_without_a_matching_query_run_is_refused(self):
        (self.run_dir / "results-r3.jsonl").write_text(json.dumps(ROWS[0]) + "\n", encoding="utf-8")
        with self.assertRaises(SystemExit) as ctx:
            score.main(["--run-dir", str(self.run_dir), "--results-tag", "r3"])
        self.assertIn("results tag r3", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
