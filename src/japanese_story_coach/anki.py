from __future__ import annotations

import hashlib
import html
import json
import re
import sqlite3
import tempfile
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


class AnkiInspectionError(RuntimeError):
    pass


COLLECTION_NAMES = ("collection.anki21b", "collection.anki21", "collection.anki2")
FIELD_SEPARATOR = "\x1f"
MAX_COLLECTION_BYTES = 512 * 1024 * 1024
MAX_MANIFEST_BYTES = 32 * 1024 * 1024
TAG_RE = re.compile(r"\S+")
MEDIA_RE = re.compile(r"(?:\[sound:([^\]]+)\]|<(?:img|audio|source)[^>]+(?:src|href)=[\"']([^\"']+))", re.IGNORECASE)
HTML_RE = re.compile(r"<[^>]+>")

READING_NAMES = ("reading", "kana", "hiragana", "furigana", "romaji", "假名", "読み")
MEANING_NAMES = ("meaning", "english", "definition", "中文", "释义", "釋義", "翻译", "翻譯", "def")
VOCABULARY_NAMES = ("expression", "japanese", "kanji", "vocab", "word", "日文", "単語")
GRAMMAR_NAMES = ("grammar", "文法", "pattern", "construction")
AUDIO_NAMES = ("audio", "sound", "pronunciation", "音频", "音頻", "発音")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _matches(name: str, candidates: tuple[str, ...]) -> bool:
    folded = name.casefold()
    return any(candidate in folded for candidate in candidates)


def _clean(value: str) -> str:
    return html.unescape(HTML_RE.sub(" ", value)).strip()


def _media_references(fields: list[str]) -> set[str]:
    references = set()
    for value in fields:
        for match in MEDIA_RE.findall(value):
            reference = next((part for part in match if part), "")
            if reference:
                references.add(Path(reference).name)
    return references


def _load_json(value: str | bytes, label: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise AnkiInspectionError(f"Invalid {label} JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise AnkiInspectionError(f"Invalid {label}: expected an object")
    return parsed


def inspect_apkg(path: Path) -> dict[str, Any]:
    source = path.expanduser().resolve(strict=True)
    if not source.is_file() or source.is_symlink() or source.suffix.casefold() != ".apkg":
        raise AnkiInspectionError("Anki source must be a real .apkg file, not a symlink")
    before = (source.stat().st_size, source.stat().st_mtime_ns, _sha256(source))
    try:
        with zipfile.ZipFile(source) as archive:
            names = archive.namelist()
            if len(names) != len(set(names)):
                raise AnkiInspectionError("Anki package contains duplicate archive member names")
            collection_name = next((name for name in COLLECTION_NAMES if name in names), None)
            if collection_name is None:
                raise AnkiInspectionError("Anki package has no supported collection database")
            collection_info = archive.getinfo(collection_name)
            if collection_info.file_size > MAX_COLLECTION_BYTES:
                raise AnkiInspectionError("Anki collection database exceeds the inspection limit")
            manifest = {}
            warnings = []
            if "media" in names:
                info = archive.getinfo("media")
                if info.file_size > MAX_MANIFEST_BYTES:
                    raise AnkiInspectionError("Anki media manifest exceeds the inspection limit")
                manifest = _load_json(archive.read("media"), "media manifest")
            else:
                warnings.append("media manifest is missing")
            with tempfile.TemporaryDirectory(prefix="jsc-anki-inspection-") as directory:
                database = Path(directory) / "collection.sqlite3"
                database.write_bytes(archive.read(collection_name))
                report = _inspect_collection(database, collection_name, manifest, set(names), warnings)
    except zipfile.BadZipFile as exc:
        raise AnkiInspectionError(f"Malformed Anki package: {exc}") from exc
    after = (source.stat().st_size, source.stat().st_mtime_ns, _sha256(source))
    if before != after:
        raise AnkiInspectionError("Anki package changed during read-only inspection")
    return {"schema": "AnkiCoverageReport/v1", "source": {"name": source.name, "byte_size": before[0], "sha256": before[2]}, **report}


def _inspect_collection(database: Path, collection_name: str, manifest: dict[str, Any], archive_names: set[str], warnings: list[str]) -> dict[str, Any]:
    try:
        connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only = ON")
        connection.execute("PRAGMA trusted_schema = OFF")
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise AnkiInspectionError(f"Anki collection integrity check failed: {integrity}")
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        required = {"col", "notes", "cards"}
        if not required.issubset(tables):
            raise AnkiInspectionError(f"Anki collection is missing tables: {sorted(required - tables)}")
        col = connection.execute("SELECT models, decks FROM col LIMIT 1").fetchone()
        if col is None:
            raise AnkiInspectionError("Anki collection metadata is missing")
        models = _load_json(col["models"], "note models")
        decks = _load_json(col["decks"], "decks")
        model_fields = {int(identifier): [field.get("name", "") for field in model.get("flds", [])] for identifier, model in models.items()}
        field_counts: dict[tuple[int, str], list[int]] = defaultdict(lambda: [0, 0])
        tags = Counter()
        media_references = set()
        primary_values = Counter()
        notes_by_model = Counter()
        for note in connection.execute("SELECT id, mid, tags, flds FROM notes"):
            model_id = int(note["mid"])
            fields = str(note["flds"]).split(FIELD_SEPARATOR)
            names = model_fields.get(model_id, [])
            notes_by_model[model_id] += 1
            for index, name in enumerate(names):
                value = fields[index] if index < len(fields) else ""
                field_counts[(model_id, name)][1] += 1
                if _clean(value):
                    field_counts[(model_id, name)][0] += 1
            first = _clean(fields[0]) if fields else ""
            if first:
                primary_values[(model_id, first.casefold())] += 1
            tags.update(TAG_RE.findall(str(note["tags"])))
            media_references.update(_media_references(fields))
        note_count = sum(notes_by_model.values())
        card_count = connection.execute("SELECT count(*) FROM cards").fetchone()[0]
        orphan_cards = connection.execute("SELECT count(*) FROM cards c LEFT JOIN notes n ON n.id=c.nid WHERE n.id IS NULL").fetchone()[0]
        review_count = connection.execute("SELECT count(*) FROM revlog").fetchone()[0] if "revlog" in tables else 0
        connection.close()
    except sqlite3.DatabaseError as exc:
        raise AnkiInspectionError(f"Unreadable Anki collection database: {exc}") from exc

    media_files = {str(value) for value in manifest.values() if isinstance(value, str)}
    present_manifest_keys = {key for key in manifest if key in archive_names}
    missing_members = len(manifest) - len(present_manifest_keys)
    missing_references = sorted(reference for reference in media_references if reference not in media_files)
    if orphan_cards:
        warnings.append(f"{orphan_cards} cards reference missing notes")
    if missing_members:
        warnings.append(f"{missing_members} media manifest members are missing")
    if missing_references:
        warnings.append(f"{len(missing_references)} note media references are absent from the manifest")

    model_reports = []
    all_field_names = []
    for identifier, model in models.items():
        model_id = int(identifier)
        fields = model_fields[model_id]
        all_field_names.extend(fields)
        model_reports.append({
            "name": model.get("name", f"model-{identifier}"),
            "note_count": notes_by_model[model_id],
            "fields": [{"name": name, "nonempty": field_counts[(model_id, name)][0], "total": field_counts[(model_id, name)][1], "coverage": round(field_counts[(model_id, name)][0] / max(1, field_counts[(model_id, name)][1]), 4)} for name in fields],
            "templates": [template.get("name", "") for template in model.get("tmpls", [])],
        })
    dimensions = {
        "vocabulary": any(_matches(name, VOCABULARY_NAMES) for name in all_field_names),
        "reading": any(_matches(name, READING_NAMES) for name in all_field_names),
        "meaning": any(_matches(name, MEANING_NAMES) for name in all_field_names),
        "audio": bool(media_references) or any(_matches(name, AUDIO_NAMES) for name in all_field_names),
        "lesson_sequence": len(decks) > 2 or any("::" in deck.get("name", "") for deck in decks.values()),
        "grammar": any(_matches(name, GRAMMAR_NAMES) for name in all_field_names),
    }
    weights = {"vocabulary": 30, "reading": 25, "meaning": 25, "audio": 10, "lesson_sequence": 10}
    usefulness = sum(weight for dimension, weight in weights.items() if dimensions[dimension])
    return {
        "collection_format": collection_name,
        "integrity": "ok",
        "counts": {"notes": note_count, "cards": card_count, "decks": len(decks), "note_models": len(models), "review_events": review_count, "tags": sum(tags.values()), "unique_tags": len(tags)},
        "relationships": {"orphan_cards": orphan_cards, "duplicate_primary_notes": sum(count - 1 for count in primary_values.values() if count > 1)},
        "models": model_reports,
        "decks": sorted(deck.get("name", "") for deck in decks.values()),
        "media": {"manifest_entries": len(manifest), "referenced_names": len(media_references), "missing_archive_members": missing_members, "missing_note_references": len(missing_references)},
        "lesson_planning": {"dimensions": dimensions, "structured_usefulness_score": usefulness, "maximum_score": 100, "pdf_gap_recommended": not dimensions["grammar"], "reason": "Use Anki for structured vocabulary/readings/meaning; consult PDFs only for missing grammar or sequencing."},
        "warnings": warnings,
        "privacy": {"contains_note_text": False, "contains_source_paths": False, "external_provider_used": False, "temporary_database_removed": True},
    }


def combined_coverage(paths: list[Path]) -> dict[str, Any]:
    reports = [inspect_apkg(path) for path in paths]
    dimensions = {name: any(report["lesson_planning"]["dimensions"][name] for report in reports) for name in ("vocabulary", "reading", "meaning", "audio", "lesson_sequence", "grammar")}
    return {
        "schema": "CombinedAnkiCoverage/v1",
        "packages": reports,
        "totals": {key: sum(report["counts"][key] for report in reports) for key in ("notes", "cards", "review_events")},
        "combined_dimensions": dimensions,
        "recommendation": "Build the first lesson planner from Anki vocabulary/readings/meaning. Add curated grammar, and use selective PDF extraction only where the coverage report shows a gap.",
        "privacy": {"contains_note_text": False, "contains_source_paths": False, "external_provider_used": False},
    }
