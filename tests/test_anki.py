import json
import sqlite3
import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

from japanese_story_coach.anki import AnkiInspectionError, combined_coverage, inspect_apkg
from japanese_story_coach.anki_importer import AnkiImportError, ensure_inventoried_source, import_apkg
from japanese_story_coach.database import connect, migrate
from japanese_story_coach.inventory import inventory_source


def make_apkg(path: Path, *, include_collection: bool = True, broken_card: bool = False, model_name: str = "Vocabulary") -> None:
    database = path.with_suffix(".sqlite3")
    connection = sqlite3.connect(database)
    connection.executescript("""
        CREATE TABLE col (models TEXT NOT NULL, decks TEXT NOT NULL);
        CREATE TABLE notes (id INTEGER PRIMARY KEY, mid INTEGER NOT NULL, tags TEXT NOT NULL, flds TEXT NOT NULL, csum INTEGER);
        CREATE TABLE cards (id INTEGER PRIMARY KEY, nid INTEGER NOT NULL, did INTEGER NOT NULL, ord INTEGER NOT NULL DEFAULT 0, queue INTEGER NOT NULL DEFAULT 0, type INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE revlog (id INTEGER PRIMARY KEY);
    """)
    field_names = ["kanjis", "japanese_kana", "english", "sound"] if model_name == "Simple Model+++++++++++++" else ["Expression", "Reading", "English", "Audio"]
    model = {"1": {"name": model_name, "flds": [{"name": name} for name in field_names], "tmpls": [{"name": "Recognition"}]}}
    decks = {"1": {"name": "N5::Lesson 1"}}
    connection.execute("INSERT INTO col(models, decks) VALUES (?, ?)", (json.dumps(model), json.dumps(decks)))
    fields = "見る\x1fみる\x1fto see\x1f[sound:miru.mp3]"
    connection.execute("INSERT INTO notes(id, mid, tags, flds) VALUES (10, 1, ' n5 verb ', ?)", (fields,))
    connection.execute("INSERT INTO notes(id, mid, tags, flds) VALUES (11, 1, ' n5 ', ?)", (fields,))
    connection.execute("INSERT INTO cards(id, nid, did) VALUES (20, ?, 1)", (999 if broken_card else 10,))
    connection.commit()
    connection.close()
    with zipfile.ZipFile(path, "w") as archive:
        if include_collection:
            archive.write(database, "collection.anki21")
        archive.writestr("media", json.dumps({"0": "miru.mp3"}))
        archive.writestr("0", b"audio")
    database.unlink()


class AnkiInspectionTests(unittest.TestCase):
    def test_report_covers_structure_without_note_text_or_paths(self):
        with TemporaryDirectory() as directory:
            package = Path(directory) / "n5.apkg"
            make_apkg(package)
            before = package.read_bytes()
            report = inspect_apkg(package)
            self.assertEqual(before, package.read_bytes())
            self.assertEqual({"notes": 2, "cards": 1, "decks": 1, "note_models": 1, "review_events": 0, "tags": 3, "unique_tags": 2}, report["counts"])
            self.assertEqual(1, report["relationships"]["duplicate_primary_notes"])
            self.assertEqual(0, report["relationships"]["orphan_cards"])
            self.assertEqual(100, report["lesson_planning"]["structured_usefulness_score"])
            self.assertTrue(report["lesson_planning"]["pdf_gap_recommended"])
            encoded = json.dumps(report, ensure_ascii=False)
            self.assertNotIn("見る", encoded)
            self.assertNotIn(str(package.parent), encoded)
            self.assertFalse(report["privacy"]["external_provider_used"])

    def test_relationship_and_media_warnings_are_reported_as_counts(self):
        with TemporaryDirectory() as directory:
            package = Path(directory) / "broken-links.apkg"
            make_apkg(package, broken_card=True)
            report = inspect_apkg(package)
            self.assertEqual(1, report["relationships"]["orphan_cards"])
            self.assertTrue(any("missing notes" in warning for warning in report["warnings"]))

    def test_malformed_or_collectionless_packages_fail_closed(self):
        with TemporaryDirectory() as directory:
            malformed = Path(directory) / "bad.apkg"
            malformed.write_bytes(b"not a zip")
            with self.assertRaisesRegex(AnkiInspectionError, "Malformed"):
                inspect_apkg(malformed)
            missing = Path(directory) / "missing.apkg"
            make_apkg(missing, include_collection=False)
            with self.assertRaisesRegex(AnkiInspectionError, "no supported"):
                inspect_apkg(missing)

    def test_combined_report_sums_packages_without_provider_use(self):
        with TemporaryDirectory() as directory:
            first, second = Path(directory) / "one.apkg", Path(directory) / "two.apkg"
            make_apkg(first); make_apkg(second)
            report = combined_coverage([first, second])
            self.assertEqual(4, report["totals"]["notes"])
            self.assertFalse(report["privacy"]["external_provider_used"])

    def test_import_is_idempotent_and_preserves_provenance(self):
        with TemporaryDirectory() as directory:
            root = Path(directory) / "sources"; root.mkdir()
            package = root / "genki.apkg"
            make_apkg(package, model_name="Simple Model+++++++++++++")
            connection = connect(Path(directory) / "private" / "coach.sqlite3")
            migrate(connection)
            record = inventory_source(root, {".apkg"})[0]
            source_id = ensure_inventoried_source(connection, "test", root, record)
            first = import_apkg(connection, source_id, package)
            second = import_apkg(connection, source_id, package)
            self.assertEqual(first, second)
            self.assertEqual(2, connection.execute("SELECT count(*) FROM anki_notes").fetchone()[0])
            self.assertEqual(1, connection.execute("SELECT count(*) FROM concepts").fetchone()[0])
            self.assertEqual(4, connection.execute("SELECT count(*) FROM source_assertions").fetchone()[0])
            self.assertEqual(2, connection.execute("SELECT count(*) FROM anki_note_media").fetchone()[0])
            self.assertEqual(2, connection.execute("SELECT count(*) FROM source_imports WHERE status='completed'").fetchone()[0])
            connection.close()

    def test_broken_relationship_rolls_back_all_curriculum_rows(self):
        with TemporaryDirectory() as directory:
            root = Path(directory) / "sources"; root.mkdir()
            package = root / "broken.apkg"; make_apkg(package, broken_card=True, model_name="Simple Model+++++++++++++")
            connection = connect(Path(directory) / "private" / "coach.sqlite3"); migrate(connection)
            source_id = ensure_inventoried_source(connection, "test", root, inventory_source(root, {".apkg"})[0])
            with self.assertRaisesRegex(AnkiImportError, "unresolved"):
                import_apkg(connection, source_id, package)
            for table in ("anki_notes", "anki_cards", "concepts", "source_assertions"):
                self.assertEqual(0, connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0])
            connection.close()

    def test_unsupported_model_fails_before_curriculum_rows_are_written(self):
        with TemporaryDirectory() as directory:
            root = Path(directory) / "sources"; root.mkdir()
            package = root / "unknown.apkg"; make_apkg(package)
            connection = connect(Path(directory) / "private" / "coach.sqlite3"); migrate(connection)
            source_id = ensure_inventoried_source(connection, "test", root, inventory_source(root, {".apkg"})[0])
            with self.assertRaisesRegex(AnkiImportError, "normalization profile"):
                import_apkg(connection, source_id, package)
            self.assertEqual(0, connection.execute("SELECT count(*) FROM anki_notes").fetchone()[0])
            self.assertEqual(0, connection.execute("SELECT count(*) FROM concepts").fetchone()[0])
            connection.close()


if __name__ == "__main__":
    unittest.main()
