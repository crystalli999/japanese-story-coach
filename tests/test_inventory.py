import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from japanese_story_coach.database import connect, migrate
from japanese_story_coach.inventory import inventory_source, save_inventory


class InventoryTests(unittest.TestCase):
    def test_inventory_hashes_supported_files_without_modifying_sources(self):
        with TemporaryDirectory() as directory:
            root = Path(directory) / "sources"
            root.mkdir()
            source = root / "deck.apkg"
            source.write_bytes(b"example")
            ignored = root / "cover.jpg"
            ignored.write_bytes(b"image")
            before = (source.stat().st_size, source.stat().st_mtime_ns, source.read_bytes())
            records = inventory_source(root)
            after = (source.stat().st_size, source.stat().st_mtime_ns, source.read_bytes())
            self.assertEqual(before, after)
            self.assertEqual(["deck.apkg"], [item.relative_path for item in records])
            self.assertEqual("50d858e0985ecc7f60418aaf0cc5ab587f42c2570a884095a9e8ccacd0f6545c", records[0].sha256)

    def test_inventory_skips_symlinks_and_saves_idempotently(self):
        with TemporaryDirectory() as directory:
            root = Path(directory) / "sources"
            root.mkdir()
            (root / "lesson.txt").write_text("日本語", encoding="utf-8")
            os.symlink(root / "lesson.txt", root / "linked.txt")
            records = inventory_source(root)
            connection = connect(Path(directory) / "coach.sqlite3")
            migrate(connection)
            collection = connection.execute("INSERT INTO source_collections(name, root_path) VALUES ('test', ?)", (str(root),)).lastrowid
            self.assertEqual(1, save_inventory(connection, collection, records))
            self.assertEqual(1, save_inventory(connection, collection, records))
            self.assertEqual(1, connection.execute("SELECT count(*) FROM source_files").fetchone()[0])
            connection.close()


if __name__ == "__main__":
    unittest.main()
