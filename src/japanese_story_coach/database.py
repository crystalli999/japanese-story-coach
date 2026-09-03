from __future__ import annotations

import sqlite3
from pathlib import Path


class MigrationError(RuntimeError):
    pass


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    path.chmod(0o600)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    return connection


def migrate(connection: sqlite3.Connection, migrations_dir: Path | None = None) -> list[str]:
    directory = migrations_dir or Path(__file__).with_name("migrations")
    connection.execute("CREATE TABLE IF NOT EXISTS schema_migrations (name TEXT PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
    applied = {row[0] for row in connection.execute("SELECT name FROM schema_migrations")}
    completed = []
    for migration in sorted(directory.glob("*.sql")):
        if migration.name in applied:
            continue
        sql = migration.read_text(encoding="utf-8")
        try:
            with connection:
                connection.executescript(sql)
                connection.execute("INSERT INTO schema_migrations(name) VALUES (?)", (migration.name,))
        except sqlite3.DatabaseError as exc:
            raise MigrationError(f"Migration {migration.name} failed: {exc}") from exc
        completed.append(migration.name)
    return completed
