from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppPaths:
    root: Path
    database: Path
    import_staging: Path
    ocr_output: Path
    source_media: Path

    @classmethod
    def from_environment(cls) -> "AppPaths":
        configured = os.getenv("JSC_DATA_DIR")
        root = Path(configured).expanduser() if configured else Path.home() / "Library" / "Application Support" / "Japanese Story Coach"
        root = root.resolve(strict=False)
        return cls(root, root / "coach.sqlite3", root / "import-staging", root / "ocr-output", root / "source-media")

    def create_private_directories(self) -> None:
        for path in (self.root, self.import_staging, self.ocr_output, self.source_media):
            path.mkdir(mode=0o700, parents=True, exist_ok=True)
            path.chmod(0o700)

    def assert_outside_repository(self, repository: Path) -> None:
        repo = repository.resolve()
        root = self.root.resolve(strict=False)
        if root == repo or repo in root.parents:
            raise ValueError("Private application data must be outside the Git repository")
