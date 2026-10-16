"""Tests for the definition rule of scripts/derive_ontology.py (SCRUM-18, D7).

    python -m unittest discover -s tests

The inputs are English Wikidata property descriptions as cached on 2026-10-06.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import derive_ontology as do  # noqa: E402


class DefinitionTest(unittest.TestCase):
    def check(self, description, expected):
        self.assertEqual(do.definition_of(description), expected)

    def test_editor_sentences_dropped(self):
        self.check(
            "underlying or immediate cause of death. Underlying cause (e.g. car accident, stomach "
            "cancer) preferred. Use 'manner of death' (P1196) for broadest category, e.g. natural "
            "causes, accident, homicide, suicide",
            "underlying or immediate cause of death",
        )

    def test_editor_clauses_dropped(self):
        self.check("time when an entity begins to exist; for date of official opening use P1619",
                   "time when an entity begins to exist")
        self.check('part of this subject; inverse property of "part of" (P361). See also "has parts '
                   'of the class" (P2670).', "part of this subject")

    def test_editor_brackets_dropped_descriptive_ones_kept(self):
        self.check('person(s) who wrote the music [for lyricist, use "lyrics by" (P676)]',
                   "person(s) who wrote the music")
        self.check("sovereign state that this subject item is in (not to be used for human beings)",
                   "sovereign state that this subject item is in")
        self.check("country of origin of this item (creative work, food, phrase, product, etc.)",
                   "country of origin of this item (creative work, food, phrase, product, etc.)")

    def test_unchanged_description_keeps_its_period(self):
        text = ("person who checks and corrects a work. Also applies to person who establishes "
                "the text of an ancient written work or manuscript.")
        self.check(text, text)

    def test_all_notes_keeps_description(self):
        self.check("Use P123.", "Use P123.")


if __name__ == "__main__":
    unittest.main()
