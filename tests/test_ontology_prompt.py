"""Tests for scripts/ontology_prompt.py (SCRUM-18).

    python -m unittest discover -s tests

The rendering tests use the standard library only. The condition tests read
LightRAG's installed templates and are skipped when lightrag is not importable.
"""

import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import ontology_prompt as op  # noqa: E402

try:
    from lightrag.prompt import PROMPTS
except ImportError:  # pragma: no cover
    PROMPTS = None


def lines_starting(text: str, prefix: str) -> list[str]:
    return [line for line in text.splitlines() if line.startswith(prefix)]


class RenderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ontology = op.load_ontology()
        cls.rendered = op.render(cls.ontology)

    def test_every_entity_type_exactly_once(self):
        text = self.rendered["entity_types_guidance"]
        listed = [re.match(r"- (.+?)(?: \(a kind of .+?\))?: ", line).group(1)
                  for line in lines_starting(text, "- ")]
        names = sorted(t["name"] for t in self.ontology["entity_types"])
        self.assertEqual(sorted(listed), names)
        self.assertEqual(len(listed), len(set(listed)))
        for t in self.ontology["entity_types"]:
            with self.subTest(entity_type=t["name"]):
                broader = f" (a kind of {t['broader']})" if t["broader"] else ""
                self.assertEqual(text.splitlines().count(f"- {t['name']}{broader}: {t['definition']}"), 1)

    def test_every_relation_exactly_once(self):
        text = self.rendered["relation_types_block"]
        listed = [re.match(r"- (.+?) \(", line).group(1) for line in lines_starting(text, "- ")]
        labels = sorted(r["relation"] for r in self.ontology["relation_types"])
        self.assertEqual(sorted(listed), labels)
        self.assertEqual(len(listed), len(set(listed)))
        for r in self.ontology["relation_types"]:
            with self.subTest(relation=r["relation"]):
                line = f"- {r['relation']} ({op._types(r['domain'])} -> {op._types(r['range'])}): {r['definition']}"
                self.assertEqual(lines_starting(text, f"- {r['relation']} (").count(line), 1)

    def test_nothing_but_types_and_relations(self):
        g = self.rendered["entity_types_guidance"].splitlines()
        b = self.rendered["relation_types_block"].splitlines()
        self.assertEqual(g[:2], [op.ENTITY_TYPES_INTRO, ""])
        self.assertEqual(b[:2], [op.RELATION_TYPES_INTRO, ""])
        self.assertEqual(len(g) - 2, len(self.ontology["entity_types"]))
        self.assertEqual(len(b) - 2, len(self.ontology["relation_types"]))

    def test_keywords_instruction(self):
        self.assertIn("must be exactly one label from this list", self.rendered["relation_types_block"])

    def test_dates_render_as_date(self):
        text = self.rendered["relation_types_block"]
        self.assertIn("- date of birth (Human -> date): ", text)
        self.assertNotIn("literal:date", text)

    def test_deterministic(self):
        again = op.render(json.loads(json.dumps(self.ontology)))
        self.assertEqual(again, self.rendered)
        shuffled = dict(self.ontology,
                        entity_types=list(reversed(self.ontology["entity_types"])),
                        relation_types=list(reversed(self.ontology["relation_types"])))
        self.assertEqual(op.render(shuffled), self.rendered)


@unittest.skipIf(PROMPTS is None, "lightrag not installed")
class ConditionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.condition = op.build_condition(op.load_ontology(), PROMPTS)
        cls.overrides = cls.condition["settings"]["prompt_overrides"]

    def test_condition_file_is_current(self):
        self.assertEqual(op.CONDITION_PATH.read_text(encoding="utf-8"), op.dump(self.condition))

    def test_only_allowed_settings(self):
        self.assertEqual(set(self.condition["settings"]), {"addon_params", "prompt_overrides"})
        self.assertEqual(set(self.overrides), {op.SYSTEM_KEY, op.USER_KEY})

    def test_placeholders_kept(self):
        for key, template in self.overrides.items():
            with self.subTest(key=key):
                self.assertEqual(op.placeholders(template), op.placeholders(PROMPTS[key]))

    def test_only_relationship_parts_change(self):
        block = op._escape(op.render(op.load_ontology())["relation_types_block"])
        section = "---Relation Types---\n" + block + "\n\n"
        system = self.overrides[op.SYSTEM_KEY].replace(section, "", 1)
        system = system.replace(op.ONTOLOGY_KEYWORDS_BULLET, op.KEYWORDS_BULLET, 1)
        self.assertEqual(system, PROMPTS[op.SYSTEM_KEY])
        self.assertEqual(self.overrides[op.USER_KEY].replace(section, "", 1), PROMPTS[op.USER_KEY])


if __name__ == "__main__":
    unittest.main()
