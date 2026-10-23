"""Tests for the resumable query stage of scripts/run_condition.py (SCRUM-32).

    python -m unittest discover -s tests

No model is called: answer_questions takes the answering function as an
argument, and these tests pass a stub. run_condition imports lightrag, so the
tests are skipped when it is not installed.
"""

import asyncio
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

try:
    import run_condition as rc
except ImportError:  # pragma: no cover
    rc = None

QUESTIONS = [{"_id": f"q{i}", "question": f"Question {i}?"} for i in range(1, 5)]
KEYS = {"config_sha256": "c" * 64, "index_settings_sha256": "i" * 64, "seed": 694, "llm_cache": False}


def stub(calls: list[str], interrupt_at: str | None = None):
    async def answer(question):
        calls.append(question["_id"])
        if question["_id"] == interrupt_at:
            # What Ctrl+C delivers to the running query under asyncio.run.
            raise asyncio.CancelledError
        return {"question_id": question["_id"], "predicted_answer": f"answer {question['_id']}"}
    return answer


def run(path: Path, answer, keys=KEYS) -> dict:
    progress = {}
    asyncio.run(rc.answer_questions(QUESTIONS, path, keys, answer, progress))
    return progress


def lines(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


@unittest.skipIf(rc is None, "lightrag not installed")
class ResumeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "results.jsonl"

    def tearDown(self):
        self.tmp.cleanup()

    def test_interrupt_then_resume(self):
        calls = []
        progress = {}
        with self.assertRaises(asyncio.CancelledError):
            asyncio.run(rc.answer_questions(QUESTIONS, self.path, KEYS, stub(calls, "q3"), progress))
        # q1 and q2 are on disk as whole lines; q3 was interrupted and not written.
        self.assertEqual(calls, ["q1", "q2", "q3"])
        self.assertEqual(progress, {"already_answered": 0, "answered": 2})
        self.assertTrue(self.path.read_text(encoding="utf-8").endswith("\n"))
        self.assertEqual([r["question_id"] for r in lines(self.path)], ["q1", "q2"])

        calls = []
        progress = run(self.path, stub(calls))
        self.assertEqual(calls, ["q3", "q4"])
        self.assertEqual(progress, {"already_answered": 2, "answered": 2})
        rows = lines(self.path)
        self.assertEqual([r["question_id"] for r in rows], ["q1", "q2", "q3", "q4"])
        for row in rows:
            self.assertEqual({k: row[k] for k in rc.RESUME_KEYS}, KEYS)

    def test_complete_file_is_left_alone(self):
        run(self.path, stub([]))
        before = self.path.read_bytes()
        calls = []
        self.assertEqual(run(self.path, stub(calls)), {"already_answered": 4, "answered": 0})
        self.assertEqual(calls, [])
        self.assertEqual(self.path.read_bytes(), before)

    def test_refuses_other_settings_and_names_them(self):
        run(self.path, stub([]), KEYS)
        before = self.path.read_bytes()
        calls = []
        other = {**KEYS, "seed": 1, "llm_cache": True}
        with self.assertRaises(SystemExit) as ctx:
            run(self.path, stub(calls), other)
        message = str(ctx.exception)
        self.assertIn("seed: file has 694, this run has 1", message)
        self.assertIn("llm_cache: file has false, this run has true", message)
        self.assertNotIn("config_sha256:", message)
        self.assertEqual(calls, [])
        self.assertEqual(self.path.read_bytes(), before)

    def test_refuses_rows_without_provenance(self):
        self.path.write_text(json.dumps({"question_id": "q1"}) + "\n", encoding="utf-8")
        self.assertEqual(rc.resume_mismatches(rc.read_results(self.path), KEYS), [
            f"{key}: file has missing, this run has {json.dumps(KEYS[key])}" for key in rc.RESUME_KEYS
        ])
        with self.assertRaises(SystemExit):
            run(self.path, stub([]))

    def test_refuses_torn_last_line(self):
        self.path.write_text(json.dumps({"question_id": "q1", **KEYS}) + "\n{\"question_id\": \"q2",
                             encoding="utf-8")
        with self.assertRaises(SystemExit) as ctx:
            run(self.path, stub([]))
        self.assertIn("last line is incomplete", str(ctx.exception))

    def test_refuses_rows_from_another_subset(self):
        self.path.write_text(json.dumps({"question_id": "x9", **KEYS}) + "\n", encoding="utf-8")
        with self.assertRaises(SystemExit) as ctx:
            run(self.path, stub([]))
        self.assertIn("x9", str(ctx.exception))


@unittest.skipIf(rc is None, "lightrag not installed")
class SessionCountTest(unittest.TestCase):
    def test_start_record_counts_sessions(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "run_manifest.json"
            rc.start_record(path, {"subset": "mini"}, "query", {"seed": 694})
            manifest, record = rc.start_record(path, {"subset": "mini"}, "query", {"seed": 694})
            self.assertEqual(manifest["query_sessions"], 2)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["query_sessions"], 2)
            self.assertEqual(record["status"], "running")


if __name__ == "__main__":
    unittest.main()
