import sqlite3
import stat
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from japanese_story_coach.database import connect, migrate


class DatabaseTests(unittest.TestCase):
    def test_migration_is_complete_and_idempotent(self):
        with TemporaryDirectory() as directory:
            connection = connect(Path(directory) / "coach.sqlite3")
            self.assertEqual(["001_foundation.sql", "002_anki_import.sql"], migrate(connection))
            self.assertEqual([], migrate(connection))
            tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertTrue({"source_files", "source_assertions", "concepts", "mastery_states", "diagnostic_runs", "attempts", "review_events"}.issubset(tables))
            self.assertEqual(1, connection.execute("PRAGMA foreign_keys").fetchone()[0])
            self.assertEqual(0o600, stat.S_IMODE((Path(directory) / "coach.sqlite3").stat().st_mode))
            connection.close()

    def test_source_can_be_inactivated_without_deleting_learner_history(self):
        with TemporaryDirectory() as directory:
            connection = connect(Path(directory) / "coach.sqlite3")
            migrate(connection)
            with connection:
                collection = connection.execute("INSERT INTO source_collections(name, root_path) VALUES ('test', '/private/test')").lastrowid
                source = connection.execute("INSERT INTO source_files(collection_id, original_path, relative_path, source_kind, media_type, byte_size, sha256) VALUES (?, '/private/test/a.apkg', 'a.apkg', 'anki', 'application/octet-stream', 1, ?)", (collection, "a" * 64)).lastrowid
                concept = connection.execute("INSERT INTO concepts(concept_type, canonical_key, display_text, normalized_text) VALUES ('lexeme', '見る|みる', '見る', '見る')").lastrowid
                learner = connection.execute("INSERT INTO learners(display_name) VALUES ('Learner')").lastrowid
                connection.execute("INSERT INTO mastery_states(learner_id, concept_id, skill) VALUES (?, ?, 'recognition')", (learner, concept))
                connection.execute("UPDATE source_files SET status='inactive' WHERE id=?", (source,))
            self.assertEqual("inactive", connection.execute("SELECT status FROM source_files WHERE id=?", (source,)).fetchone()[0])
            self.assertEqual(1, connection.execute("SELECT count(*) FROM mastery_states").fetchone()[0])
            connection.close()


if __name__ == "__main__":
    unittest.main()
