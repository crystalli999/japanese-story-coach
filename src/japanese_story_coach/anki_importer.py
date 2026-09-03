from __future__ import annotations

import json
import sqlite3
import tempfile
import unicodedata
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .anki import COLLECTION_NAMES, FIELD_SEPARATOR, MAX_COLLECTION_BYTES, _clean, _load_json, _media_references, inspect_apkg
from .inventory import SourceFileRecord


class AnkiImportError(RuntimeError):
    pass


@dataclass(frozen=True)
class FieldProfile:
    concept_type: str
    surface: tuple[str, ...]
    reading: tuple[str, ...]
    meaning: tuple[str, ...]
    alternate: tuple[str, ...] = ()


PROFILES = {
    "Hiragana Note": FieldProfile("kana", ("Hiragana",), ("Romaji",), ()),
    "Simple Model+++++++++++++": FieldProfile("lexeme", ("kanjis", "japanese_kana"), ("japanese_kana",), ("english", "kanji_meaning")),
}


def normalize_text(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", _clean(value)).split())


def _first(fields: dict[str, str], names: tuple[str, ...]) -> str:
    return next((fields[name] for name in names if normalize_text(fields.get(name, ""))), "")


def _concept_key(kind: str, surface: str, reading: str) -> str:
    return f"{kind}:{normalize_text(surface).casefold()}|{normalize_text(reading).casefold()}"


def _read_records(path: Path) -> dict[str, Any]:
    report = inspect_apkg(path)
    source = path.resolve(strict=True)
    with zipfile.ZipFile(source) as archive:
        collection_name = next(name for name in COLLECTION_NAMES if name in archive.namelist())
        info = archive.getinfo(collection_name)
        if info.file_size > MAX_COLLECTION_BYTES:
            raise AnkiImportError("Anki collection exceeds import limit")
        manifest = _load_json(archive.read("media"), "media manifest") if "media" in archive.namelist() else {}
        media = [{"archive_member": member, "original_name": name, "byte_size": archive.getinfo(member).file_size} for member, name in manifest.items() if member in archive.namelist() and isinstance(name, str)]
        with tempfile.TemporaryDirectory(prefix="jsc-anki-import-") as directory:
            database = Path(directory) / "collection.sqlite3"
            database.write_bytes(archive.read(collection_name))
            connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA query_only=ON")
            col = connection.execute("SELECT models, decks FROM col LIMIT 1").fetchone()
            models = _load_json(col["models"], "note models")
            decks = _load_json(col["decks"], "decks")
            field_names = {str(mid): [field.get("name", "") for field in model.get("flds", [])] for mid, model in models.items()}
            notes = []
            for row in connection.execute("SELECT id, mid, tags, flds, csum FROM notes ORDER BY id"):
                values = str(row["flds"]).split(FIELD_SEPARATOR)
                fields = {name: values[index] if index < len(values) else "" for index, name in enumerate(field_names[str(row["mid"])])}
                notes.append({"id": str(row["id"]), "mid": str(row["mid"]), "fields": fields, "tags": str(row["tags"]).split(), "checksum": row["csum"], "media": sorted(_media_references(list(fields.values())))})
            cards = [dict(row) for row in connection.execute("SELECT id, nid, did, ord, queue, type FROM cards ORDER BY id")]
            connection.close()
    return {"coverage": report, "models": models, "decks": decks, "notes": notes, "cards": cards, "media": media}


def import_apkg(connection: sqlite3.Connection, source_file_id: int, path: Path) -> dict[str, Any]:
    source_row = connection.execute("SELECT sha256, status FROM source_files WHERE id=?", (source_file_id,)).fetchone()
    if source_row is None or source_row["status"] != "active":
        raise AnkiImportError("Source file must be inventoried and active before import")
    records = _read_records(path)
    if records["coverage"]["source"]["sha256"] != source_row["sha256"]:
        raise AnkiImportError("Inventoried source hash does not match the Anki package")
    unsupported = sorted({model.get("name", "") for model in records["models"].values()} - set(PROFILES))
    if unsupported:
        raise AnkiImportError(f"No normalization profile for note models: {unsupported}")
    summary = {"models": 0, "decks": 0, "notes": 0, "cards": 0, "media": 0, "concepts_linked": 0, "assertions": 0}
    try:
        with connection:
            connection.execute("DELETE FROM source_assertions WHERE locator_id IN (SELECT id FROM source_locators WHERE source_file_id=?)", (source_file_id,))
            connection.execute("DELETE FROM concept_senses WHERE NOT EXISTS (SELECT 1 FROM source_assertions WHERE source_assertions.sense_id=concept_senses.id)")
            connection.execute("DELETE FROM concept_forms WHERE NOT EXISTS (SELECT 1 FROM source_assertions WHERE source_assertions.concept_id=concept_forms.concept_id)")
            connection.execute("DELETE FROM concepts WHERE NOT EXISTS (SELECT 1 FROM source_assertions WHERE source_assertions.concept_id=concepts.id)")
            connection.execute("DELETE FROM source_locators WHERE source_file_id=?", (source_file_id,))
            connection.execute("DELETE FROM anki_note_media WHERE note_id IN (SELECT id FROM anki_notes WHERE source_file_id=?)", (source_file_id,))
            connection.execute("DELETE FROM anki_cards WHERE source_file_id=?", (source_file_id,))
            connection.execute("DELETE FROM anki_notes WHERE source_file_id=?", (source_file_id,))
            connection.execute("DELETE FROM anki_decks WHERE source_file_id=?", (source_file_id,))
            connection.execute("DELETE FROM anki_note_models WHERE source_file_id=?", (source_file_id,))
            connection.execute("DELETE FROM anki_media WHERE source_file_id=?", (source_file_id,))
            model_ids = {}
            for external_id, model in records["models"].items():
                model_ids[str(external_id)] = connection.execute("INSERT INTO anki_note_models(source_file_id, external_id, name, fields_json, templates_json) VALUES (?, ?, ?, ?, ?)", (source_file_id, str(external_id), model.get("name", ""), json.dumps([field.get("name", "") for field in model.get("flds", [])], ensure_ascii=False), json.dumps([template.get("name", "") for template in model.get("tmpls", [])], ensure_ascii=False))).lastrowid
            summary["models"] = len(model_ids)
            deck_ids = {}
            for external_id, deck in records["decks"].items():
                name = deck.get("name", "")
                deck_ids[int(external_id)] = connection.execute("INSERT INTO anki_decks(source_file_id, external_id, name, parent_name) VALUES (?, ?, ?, ?)", (source_file_id, str(external_id), name, name.rsplit("::", 1)[0] if "::" in name else None)).lastrowid
                connection.execute("INSERT INTO source_locators(source_file_id, locator_kind, external_id, metadata_json) VALUES (?, 'deck', ?, ?)", (source_file_id, str(external_id), json.dumps({"name": name}, ensure_ascii=False)))
            summary["decks"] = len(deck_ids)
            media_ids = {}
            for item in records["media"]:
                media_ids[item["original_name"]] = connection.execute("INSERT INTO anki_media(source_file_id, archive_member, original_name, byte_size) VALUES (?, ?, ?, ?)", (source_file_id, item["archive_member"], item["original_name"], item["byte_size"])).lastrowid
            summary["media"] = len(media_ids)
            note_ids = {}
            for note in records["notes"]:
                model = records["models"][note["mid"]]
                profile = PROFILES[model.get("name", "")]
                fields = note["fields"]
                note_id = connection.execute("INSERT INTO anki_notes(source_file_id, external_id, note_model_id, fields_json, tags_json, source_checksum) VALUES (?, ?, ?, ?, ?, ?)", (source_file_id, note["id"], model_ids[note["mid"]], json.dumps(fields, ensure_ascii=False), json.dumps(note["tags"], ensure_ascii=False), note["checksum"])).lastrowid
                note_ids[int(note["id"])] = note_id
                locator = connection.execute("INSERT INTO source_locators(source_file_id, locator_kind, external_id, metadata_json) VALUES (?, 'anki_note', ?, ?)", (source_file_id, note["id"], json.dumps({"tags": note["tags"], "model": model.get("name", "")}, ensure_ascii=False))).lastrowid
                surface, reading = _first(fields, profile.surface), _first(fields, profile.reading)
                if not normalize_text(surface):
                    continue
                display, normalized = normalize_text(surface), normalize_text(surface)
                key = _concept_key(profile.concept_type, surface, reading)
                connection.execute("INSERT INTO concepts(concept_type, canonical_key, display_text, normalized_text) VALUES (?, ?, ?, ?) ON CONFLICT(concept_type, canonical_key) DO NOTHING", (profile.concept_type, key, display, normalized))
                concept_id = connection.execute("SELECT id FROM concepts WHERE concept_type=? AND canonical_key=?", (profile.concept_type, key)).fetchone()[0]
                connection.execute("INSERT INTO concept_forms(concept_id, form_type, surface, reading, normalized_surface) SELECT ?, ?, ?, ?, ? WHERE NOT EXISTS (SELECT 1 FROM concept_forms WHERE concept_id=? AND form_type=? AND surface=? AND ifnull(reading,'')=ifnull(?,''))", (concept_id, "primary", surface, reading or None, normalized, concept_id, "primary", surface, reading or None))
                for language, name in (("en", meaning_name) for meaning_name in profile.meaning):
                    meaning = normalize_text(fields.get(name, ""))
                    if not meaning:
                        continue
                    connection.execute("INSERT INTO concept_senses(concept_id, language, meaning) SELECT ?, ?, ? WHERE NOT EXISTS (SELECT 1 FROM concept_senses WHERE concept_id=? AND language=? AND meaning=?)", (concept_id, language, meaning, concept_id, language, meaning))
                    sense_id = connection.execute("SELECT id FROM concept_senses WHERE concept_id=? AND language=? AND meaning=?", (concept_id, language, meaning)).fetchone()[0]
                    inserted = connection.execute("INSERT OR IGNORE INTO source_assertions(locator_id, concept_id, sense_id, assertion_type, confidence, original_value) VALUES (?, ?, ?, 'meaning', 1.0, ?)", (locator, concept_id, sense_id, fields.get(name, "")))
                    summary["assertions"] += inserted.rowcount
                connection.execute("INSERT INTO source_assertions(locator_id, concept_id, assertion_type, confidence, original_value) VALUES (?, ?, 'anki_note', 1.0, ?)", (locator, concept_id, surface))
                summary["assertions"] += 1
                for media_name in note["media"]:
                    if media_name in media_ids:
                        connection.execute("INSERT OR IGNORE INTO anki_note_media(note_id, media_id) VALUES (?, ?)", (note_id, media_ids[media_name]))
                summary["concepts_linked"] += 1
            summary["notes"] = len(note_ids)
            for card in records["cards"]:
                if int(card["nid"]) not in note_ids or int(card["did"]) not in deck_ids:
                    raise AnkiImportError(f"Card {card['id']} has an unresolved note or deck")
                connection.execute("INSERT INTO anki_cards(source_file_id, external_id, note_id, deck_id, template_ordinal, source_queue, source_type) VALUES (?, ?, ?, ?, ?, ?, ?)", (source_file_id, str(card["id"]), note_ids[int(card["nid"])], deck_ids[int(card["did"])], card["ord"], card["queue"], card["type"]))
                connection.execute("INSERT INTO source_locators(source_file_id, locator_kind, external_id, metadata_json) VALUES (?, 'anki_card', ?, ?)", (source_file_id, str(card["id"]), json.dumps({"note_id": str(card["nid"]), "deck_id": str(card["did"])})))
            summary["cards"] = len(records["cards"])
            connection.execute("INSERT INTO source_imports(source_file_id, importer, importer_version, status, warning_json, started_at, finished_at) VALUES (?, 'anki', '2B', 'completed', ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)", (source_file_id, json.dumps(records["coverage"]["warnings"]),))
    except (sqlite3.DatabaseError, KeyError, TypeError) as exc:
        raise AnkiImportError(f"Anki import rolled back: {exc}") from exc
    return {"schema": "AnkiImportResult/v1", "source": path.name, "status": "completed", **summary, "external_provider_used": False}


def ensure_inventoried_source(connection: sqlite3.Connection, collection_name: str, root: Path, record: SourceFileRecord) -> int:
    with connection:
        connection.execute("INSERT INTO source_collections(name, root_path) VALUES (?, ?) ON CONFLICT(name) DO UPDATE SET root_path=excluded.root_path, status='active'", (collection_name, str(root.resolve())))
        collection_id = connection.execute("SELECT id FROM source_collections WHERE name=?", (collection_name,)).fetchone()[0]
        connection.execute("""INSERT INTO source_files(collection_id, original_path, relative_path, source_kind, media_type, byte_size, sha256)
            VALUES (?, ?, ?, 'anki', ?, ?, ?) ON CONFLICT(collection_id, relative_path) DO UPDATE SET
            original_path=excluded.original_path, media_type=excluded.media_type, byte_size=excluded.byte_size,
            sha256=excluded.sha256, status='active', last_seen_at=CURRENT_TIMESTAMP""", (collection_id, str(record.path), record.relative_path, record.media_type, record.byte_size, record.sha256))
        return connection.execute("SELECT id FROM source_files WHERE collection_id=? AND relative_path=?", (collection_id, record.relative_path)).fetchone()[0]
