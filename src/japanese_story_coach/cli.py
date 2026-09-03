from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import AppPaths
from .anki import combined_coverage
from .anki_importer import ensure_inventoried_source, import_apkg
from .database import connect, migrate
from .inventory import inventory_source, save_inventory
from .grammar import load_grammar_spine


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="japanese-story-coach")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init", help="Create private directories and apply database migrations")
    inventory = commands.add_parser("inventory", help="Hash supported source files without importing their contents")
    inventory.add_argument("source", type=Path)
    inventory.add_argument("--name", default="Japanese study materials")
    inventory.add_argument("--save", action="store_true", help="Save metadata to the private database")
    anki = commands.add_parser("anki-report", help="Inspect Anki structure and print a content-free coverage report")
    anki.add_argument("packages", nargs="+", type=Path)
    anki_import = commands.add_parser("anki-import", help="Normalize approved Anki packages into the private curriculum database")
    anki_import.add_argument("packages", nargs="+", type=Path)
    anki_import.add_argument("--collection", default="Japanese study materials")
    commands.add_parser("grammar-seed", help="Load the curated N5 grammar spine and link imported vocabulary")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    paths = AppPaths.from_environment()
    repository = Path(__file__).resolve().parents[2]
    paths.assert_outside_repository(repository)
    if args.command == "init":
        paths.create_private_directories()
        connection = connect(paths.database)
        applied = migrate(connection)
        connection.close()
        print(json.dumps({"data_root": str(paths.root), "database": str(paths.database), "migrations_applied": applied}, indent=2))
        return
    if args.command == "anki-report":
        print(json.dumps(combined_coverage(args.packages), ensure_ascii=False, indent=2))
        return
    if args.command == "anki-import":
        paths.create_private_directories()
        connection = connect(paths.database)
        migrate(connection)
        roots = {package.expanduser().resolve(strict=True).parent for package in args.packages}
        if len(roots) != 1:
            raise ValueError("All packages in one import command must share a source directory")
        root = roots.pop()
        inventoried = {record.path: record for record in inventory_source(root, {".apkg"})}
        results = []
        for package in args.packages:
            resolved = package.expanduser().resolve(strict=True)
            record = inventoried[resolved]
            source_file_id = ensure_inventoried_source(connection, args.collection, root, record)
            results.append(import_apkg(connection, source_file_id, resolved))
        connection.close()
        print(json.dumps({"schema": "AnkiImportBatch/v1", "database": str(paths.database), "results": results}, ensure_ascii=False, indent=2))
        return
    if args.command == "grammar-seed":
        paths.create_private_directories()
        connection = connect(paths.database)
        migrate(connection)
        result = load_grammar_spine(connection)
        connection.close()
        result["database"] = str(paths.database)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    records = inventory_source(args.source)
    result = {"source": str(args.source.resolve()), "files": [{"relative_path": item.relative_path, "kind": item.source_kind, "byte_size": item.byte_size, "sha256": item.sha256} for item in records], "saved": False}
    if args.save:
        paths.create_private_directories()
        connection = connect(paths.database)
        migrate(connection)
        with connection:
            connection.execute("INSERT INTO source_collections(name, root_path) VALUES (?, ?) ON CONFLICT(name) DO UPDATE SET root_path=excluded.root_path, status='active'", (args.name, str(args.source.resolve())))
            collection_id = connection.execute("SELECT id FROM source_collections WHERE name=?", (args.name,)).fetchone()[0]
        save_inventory(connection, collection_id, records)
        connection.close()
        result["saved"] = True
    print(json.dumps(result, indent=2))
