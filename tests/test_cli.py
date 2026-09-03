import json
import os
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from japanese_story_coach.cli import main


class CliTests(unittest.TestCase):
    def test_init_and_metadata_only_inventory(self):
        with TemporaryDirectory() as directory:
            private = Path(directory) / "private"
            sources = Path(directory) / "sources"
            sources.mkdir()
            (sources / "lesson.txt").write_text("日本語", encoding="utf-8")
            with patch.dict(os.environ, {"JSC_DATA_DIR": str(private)}, clear=False):
                output = StringIO()
                with redirect_stdout(output):
                    main(["init"])
                self.assertTrue((private / "coach.sqlite3").exists())
                output = StringIO()
                with redirect_stdout(output):
                    main(["inventory", str(sources)])
                inventory = json.loads(output.getvalue())
                self.assertFalse(inventory["saved"])
                self.assertEqual(["lesson.txt"], [item["relative_path"] for item in inventory["files"]])


if __name__ == "__main__":
    unittest.main()
