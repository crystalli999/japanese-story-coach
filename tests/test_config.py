import os
import stat
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from japanese_story_coach.config import AppPaths


class AppPathsTests(unittest.TestCase):
    def test_private_directories_are_outside_repo_and_owner_only(self):
        with TemporaryDirectory() as directory, patch.dict(os.environ, {"JSC_DATA_DIR": str(Path(directory) / "private")}, clear=False):
            paths = AppPaths.from_environment()
            paths.assert_outside_repository(Path(directory) / "repo")
            paths.create_private_directories()
            self.assertEqual(0o700, stat.S_IMODE(paths.root.stat().st_mode))

    def test_repository_data_directory_is_rejected(self):
        with TemporaryDirectory() as directory:
            repo = Path(directory) / "repo"
            paths = AppPaths(repo / "data", repo / "data/db.sqlite3", repo / "data/staging", repo / "data/ocr", repo / "data/media")
            with self.assertRaisesRegex(ValueError, "outside"):
                paths.assert_outside_repository(repo)


if __name__ == "__main__":
    unittest.main()
