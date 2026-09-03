from __future__ import annotations

import json
import sqlite3
import unicodedata
from pathlib import Path
from typing import Any


class GrammarSpineError(ValueError):
    pass


def bundled_spine_path() -> Path:
    return Path(__file__).with_name("curriculum") / "n5_grammar_v1.json"


def normalize_text(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).strip().split())


def read_spine(path: Path | None = None) -> dict[str, Any]:
    return json.loads((path or bundled_spine_path()).read_text(encoding="utf-8"))


def _validate(document: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    version = document.get("version")
    points = document.get("grammar_points")
    if not isinstance(version, str) or not version.strip() or not isinstance(points, list) or not points:
        raise GrammarSpineError("Grammar spine requires a version and non-empty grammar_points")
    slugs = [point.get("slug") for point in points]
    sequences = [point.get("sequence") for point in points]
    if any(not isinstance(slug, str) or not slug for slug in slugs) or len(slugs) != len(set(slugs)):
        raise GrammarSpineError("Grammar point slugs must be non-empty and unique")
    if any(not isinstance(seq, int) or seq < 1 for seq in sequences) or len(sequences) != len(set(sequences)):
        raise GrammarSpineError("Grammar point sequence values must be positive and unique")
    known = set(slugs)
    for point in points:
        required = {"pattern", "formation", "explanation_en", "explanation_zh_hant"}
        if any(not isinstance(point.get(field), str) or not point[field].strip() for field in required):
            raise GrammarSpineError(f"Grammar point {point['slug']} has incomplete guidance")
        unknown = set(point.get("prerequisites", [])) - known
        if unknown:
            raise GrammarSpineError(f"Grammar point {point['slug']} has unknown prerequisites: {sorted(unknown)}")
    return version, points


def _vocabulary_candidates(connection: sqlite3.Connection, surface: str, reading: str | None) -> list[int]:
    normalized = normalize_text(surface)
    rows = connection.execute(
        """SELECT DISTINCT c.id
           FROM concepts c LEFT JOIN concept_forms f ON f.concept_id=c.id
           WHERE c.concept_type IN ('lexeme','kana','kanji') AND c.status='active'
             AND (c.normalized_text=? OR f.normalized_surface=?)
             AND (? IS NULL OR f.reading=? OR c.canonical_key LIKE ?)""",
        (normalized, normalized, reading, reading, f"%|{reading}" if reading else None),
    ).fetchall()
    return [int(row[0]) for row in rows]


def load_grammar_spine(connection: sqlite3.Connection, document: dict[str, Any] | None = None) -> dict[str, int | str]:
    document = document or read_spine()
    version, points = _validate(document)
    grammar_ids: dict[str, int] = {}
    resolved = missing = ambiguous = prerequisite_count = requirement_count = 0
    with connection:
        for point in sorted(points, key=lambda item: item["sequence"]):
            key = f"curriculum:{version}:{point['slug']}"
            connection.execute(
                """INSERT INTO concepts(concept_type, canonical_key, display_text, normalized_text, jlpt_level)
                   VALUES ('grammar', ?, ?, ?, 'N5')
                   ON CONFLICT(concept_type, canonical_key) DO UPDATE SET
                     display_text=excluded.display_text, normalized_text=excluded.normalized_text,
                     jlpt_level='N5', status='active'""",
                (key, point["pattern"], normalize_text(point["pattern"])),
            )
            concept_id = int(connection.execute(
                "SELECT id FROM concepts WHERE concept_type='grammar' AND canonical_key=?", (key,)
            ).fetchone()[0])
            grammar_ids[point["slug"]] = concept_id
            connection.execute(
                """INSERT INTO grammar_details(concept_id, slug, sequence_index, pattern, formation,
                         explanation_en, explanation_zh_hant, curriculum_version)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(concept_id) DO UPDATE SET slug=excluded.slug,
                     sequence_index=excluded.sequence_index, pattern=excluded.pattern,
                     formation=excluded.formation, explanation_en=excluded.explanation_en,
                     explanation_zh_hant=excluded.explanation_zh_hant,
                     curriculum_version=excluded.curriculum_version""",
                (concept_id, point["slug"], point["sequence"], point["pattern"], point["formation"],
                 point["explanation_en"], point["explanation_zh_hant"], version),
            )

        ids = tuple(grammar_ids.values())
        placeholders = ",".join("?" for _ in ids)
        connection.execute(f"DELETE FROM concept_relations WHERE from_concept_id IN ({placeholders}) AND relation_type='prerequisite'", ids)
        connection.execute(f"DELETE FROM grammar_vocabulary_requirements WHERE grammar_concept_id IN ({placeholders})", ids)
        for point in points:
            grammar_id = grammar_ids[point["slug"]]
            for prerequisite in point.get("prerequisites", []):
                connection.execute(
                    "INSERT INTO concept_relations(from_concept_id, to_concept_id, relation_type) VALUES (?, ?, 'prerequisite')",
                    (grammar_id, grammar_ids[prerequisite]),
                )
                prerequisite_count += 1
            for item in point.get("vocabulary", []):
                candidates = _vocabulary_candidates(connection, item["surface"], item.get("reading"))
                status = "resolved" if len(candidates) == 1 else "missing" if not candidates else "ambiguous"
                vocabulary_id = candidates[0] if status == "resolved" else None
                connection.execute(
                    """INSERT INTO grammar_vocabulary_requirements(
                         grammar_concept_id, vocabulary_concept_id, surface, reading, role,
                         resolution_status, candidate_count) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (grammar_id, vocabulary_id, item["surface"], item.get("reading"), item["role"], status, len(candidates)),
                )
                requirement_count += 1
                resolved += status == "resolved"
                missing += status == "missing"
                ambiguous += status == "ambiguous"
    return {"schema": "GrammarSpineLoad/v1", "curriculum_version": version, "grammar_points": len(points),
            "prerequisites": prerequisite_count, "vocabulary_requirements": requirement_count,
            "resolved": resolved, "missing": missing, "ambiguous": ambiguous}
