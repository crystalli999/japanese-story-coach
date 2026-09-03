import json
import sqlite3
import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

from japanese_story_coach.anki import AnkiInspectionError, combined_coverage, inspect_apkg


def make_apkg(path: Path, *, include_collection: bool = True, broken_card: bool = False) -> None:
    database = path.with_suffix(".sqlite3")
    connection = sqlite3.connect(database)
    connection.executescript("""
        CREATE TABLE col (models TEXT NOT NULL, decks TEXT NOT NULL);
        CREATE TABLE notes (id INTEGER PRIMARY KEY, mid INTEGER NOT NULL, tags TEXT NOT NULL, flds TEXT NOT NULL);
        CREATE TABLE cards (id INTEGER PRIMARY KEY, nid INTEGER NOT NULL, did INTEGER NOT NULL);
        CREATE TABLE revlog (id INTEGER PRIMARY KEY);
    """)
    model = {"1": {"name": "Vocabulary", "flds": [{"name": "Expression"}, {"name": "Reading"}, {"name": "English"}, {"name": "Audio"}], "tmpls": [{"name": "Recognition"}]}}
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


if __name__ == "__main__":
    unittest.main()
