import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from japanese_story_coach.database import connect, migrate
from japanese_story_coach.grammar import load_grammar_spine
from japanese_story_coach.learning import (LearningLoopError, answer_diagnostic,
                                            create_learner, finish_diagnostic,
                                            next_diagnostic_question, plan_lesson,
                                            start_diagnostic)


class LearningLoopTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.connection = connect(Path(self.temp.name) / "coach.sqlite3")
        migrate(self.connection)
        with self.connection:
            for number in range(12):
                cid = self.connection.execute("INSERT INTO concepts(concept_type, canonical_key, display_text, normalized_text) VALUES ('kana',?,?,?)", (f"kana-{number}", f"か{number}", f"か{number}")).lastrowid
                self.connection.execute("INSERT INTO concept_forms(concept_id, form_type, surface, reading, normalized_surface) VALUES (?, 'primary', ?, ?, ?)", (cid, f"か{number}", f"ka{number}", f"か{number}"))
            for number in range(24):
                cid = self.connection.execute("INSERT INTO concepts(concept_type, canonical_key, display_text, normalized_text) VALUES ('lexeme',?,?,?)", (f"word-{number}", f"語{number}", f"語{number}")).lastrowid
                self.connection.execute("INSERT INTO concept_forms(concept_id, form_type, surface, reading, normalized_surface) VALUES (?, 'primary', ?, ?, ?)", (cid, f"語{number}", f"ご{number}", f"語{number}"))
                self.connection.execute("INSERT INTO concept_senses(concept_id, language, meaning) VALUES (?, 'en', ?)", (cid, f"meaning {number}"))
        load_grammar_spine(self.connection)
        self.learner_id = create_learner(self.connection, "Learner")

    def tearDown(self):
        self.connection.close()
        self.temp.cleanup()

    def test_complete_diagnostic_updates_memory_and_can_be_retaken(self):
        started = start_diagnostic(self.connection, self.learner_id)
        self.assertEqual(36, started["question_count"])
        while question := next_diagnostic_question(self.connection, started["run_id"]):
            stored = self.connection.execute("SELECT correct_index FROM diagnostic_items WHERE id=?", (question["item_id"],)).fetchone()[0]
            answer_diagnostic(self.connection, started["run_id"], question["item_id"], stored)
        result = finish_diagnostic(self.connection, started["run_id"])
        self.assertEqual("N5-ready", result["placement"])
        self.assertEqual(1.0, result["score"])
        self.assertEqual(36, self.connection.execute("SELECT count(*) FROM mastery_states WHERE learner_id=?", (self.learner_id,)).fetchone()[0])
        retake = start_diagnostic(self.connection, self.learner_id)
        supersedes = self.connection.execute("SELECT supersedes_id FROM diagnostic_runs WHERE id=?", (retake["run_id"],)).fetchone()[0]
        self.assertEqual(started["run_id"], supersedes)

    def test_incomplete_diagnostic_cannot_finish(self):
        started = start_diagnostic(self.connection, self.learner_id)
        with self.assertRaises(LearningLoopError):
            finish_diagnostic(self.connection, started["run_id"])

    def test_lesson_plan_uses_first_ready_grammar_and_structured_targets(self):
        packet = plan_lesson(self.connection, self.learner_id)
        self.assertEqual("Nです", packet["grammar_targets"][0]["surface"])
        self.assertEqual("romance-only; non-explicit", packet["content_boundary"])
        self.assertNotIn("source", str(packet).lower())
        self.assertEqual(1, self.connection.execute("SELECT count(*) FROM learning_sessions WHERE learner_id=?", (self.learner_id,)).fetchone()[0])

    def test_mastered_root_unlocks_next_grammar(self):
        first = self.connection.execute("SELECT concept_id FROM grammar_details WHERE sequence_index=1").fetchone()[0]
        with self.connection:
            self.connection.execute("INSERT INTO mastery_states(learner_id, concept_id, skill, confidence, evidence_count) VALUES (?, ?, 'comprehension', .9, 2)", (self.learner_id, first))
        packet = plan_lesson(self.connection, self.learner_id)
        self.assertEqual("Nは～です", packet["grammar_targets"][0]["surface"])


if __name__ == "__main__":
    unittest.main()
