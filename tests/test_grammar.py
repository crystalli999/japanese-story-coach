import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from japanese_story_coach.database import connect, migrate
from japanese_story_coach.grammar import GrammarSpineError, load_grammar_spine, read_spine


class GrammarSpineTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.connection = connect(Path(self.temp.name) / "coach.sqlite3")
        migrate(self.connection)
        with self.connection:
            self.connection.execute("INSERT INTO concepts(concept_type, canonical_key, display_text, normalized_text) VALUES ('lexeme','学生|がくせい','学生','学生')")
            self.connection.execute("INSERT INTO concepts(concept_type, canonical_key, display_text, normalized_text) VALUES ('lexeme','見る|みる','見る','見る')")

    def tearDown(self):
        self.connection.close()
        self.temp.cleanup()

    def test_bundled_spine_is_substantial_idempotent_and_linked(self):
        document = read_spine()
        first = load_grammar_spine(self.connection, document)
        second = load_grammar_spine(self.connection, document)
        self.assertGreaterEqual(first["grammar_points"], 20)
        self.assertEqual(first, second)
        self.assertGreater(first["prerequisites"], 0)
        self.assertGreater(first["vocabulary_requirements"], 0)
        self.assertGreaterEqual(first["resolved"], 2)
        self.assertEqual(first["grammar_points"], self.connection.execute("SELECT count(*) FROM grammar_details").fetchone()[0])
        self.assertEqual(first["prerequisites"], self.connection.execute("SELECT count(*) FROM concept_relations WHERE relation_type='prerequisite'").fetchone()[0])

    def test_missing_vocabulary_is_recorded_without_guessing(self):
        load_grammar_spine(self.connection)
        row = self.connection.execute("SELECT vocabulary_concept_id, resolution_status FROM grammar_vocabulary_requirements WHERE surface='猫' LIMIT 1").fetchone()
        self.assertIsNotNone(row)
        self.assertIsNone(row[0])
        self.assertEqual("missing", row[1])

    def test_unknown_prerequisite_is_rejected_before_writes(self):
        document = {"version": "bad", "grammar_points": [{"slug": "x", "sequence": 1, "pattern": "x", "formation": "x", "explanation_en": "x", "explanation_zh_hant": "x", "prerequisites": ["missing"]}]}
        with self.assertRaises(GrammarSpineError):
            load_grammar_spine(self.connection, document)
        self.assertEqual(0, self.connection.execute("SELECT count(*) FROM grammar_details").fetchone()[0])


if __name__ == "__main__":
    unittest.main()
