from __future__ import annotations

import hashlib
import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


SUPPORTED_SUFFIXES = {".apkg", ".pdf", ".txt", ".md"}


@dataclass(frozen=True)
class SourceFileRecord:
    path: Path
    relative_path: str
    byte_size: int
    sha256: str
    media_type: str
    source_kind: str


def hash_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inventory_source(root: Path, suffixes: set[str] | None = None) -> list[SourceFileRecord]:
    root = root.expanduser().resolve(strict=True)
    if not root.is_dir() or root.is_symlink():
        raise ValueError("Source root must be a real directory, not a symlink")
    allowed = suffixes or SUPPORTED_SUFFIXES
    records = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink() or not path.is_file() or path.suffix.casefold() not in allowed:
            continue
        resolved = path.resolve(strict=True)
        if root not in resolved.parents:
            raise ValueError(f"Source escaped its inventory root: {path}")
        suffix = path.suffix.casefold()
        records.append(SourceFileRecord(
            path=resolved,
            relative_path=resolved.relative_to(root).as_posix(),
            byte_size=resolved.stat().st_size,
            sha256=hash_file(resolved),
            media_type=mimetypes.guess_type(resolved.name)[0] or "application/octet-stream",
            source_kind={".apkg": "anki", ".pdf": "pdf", ".txt": "script", ".md": "script"}[suffix],
        ))
    return records


def save_inventory(connection, collection_id: int, records: Iterable[SourceFileRecord]) -> int:
    count = 0
    with connection:
        for record in records:
            connection.execute(
                """INSERT INTO source_files(collection_id, original_path, relative_path, source_kind, media_type, byte_size, sha256)
                   VALUES (?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(collection_id, relative_path) DO UPDATE SET
                     original_path=excluded.original_path, source_kind=excluded.source_kind,
                     media_type=excluded.media_type, byte_size=excluded.byte_size, sha256=excluded.sha256,
                     status='active', last_seen_at=CURRENT_TIMESTAMP""",
                (collection_id, str(record.path), record.relative_path, record.source_kind, record.media_type, record.byte_size, record.sha256),
            )
            count += 1
    return count
