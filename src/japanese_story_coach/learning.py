from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any


class LearningLoopError(ValueError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_learner(connection: sqlite3.Connection, name: str) -> int:
    if not name.strip():
        raise LearningLoopError("Learner name cannot be empty")
    with connection:
        return int(connection.execute("INSERT INTO learners(display_name) VALUES (?)", (name.strip(),)).lastrowid)


def _rotate(correct: str, distractors: list[str], seed: int) -> tuple[list[str], int]:
    choices = [correct] + [item for item in distractors if item != correct][:3]
    if len(choices) != 4:
        raise LearningLoopError("A diagnostic question requires three distinct distractors")
    offset = seed % 4
    choices = choices[offset:] + choices[:offset]
    return choices, choices.index(correct)


def _diagnostic_candidates(connection: sqlite3.Connection, kana: int, vocabulary: int, grammar: int) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    kana_rows = connection.execute(
        """SELECT c.id, c.display_text, COALESCE(NULLIF(f.reading,''), f.surface) answer
           FROM concepts c JOIN concept_forms f ON f.concept_id=c.id
           WHERE c.concept_type='kana' AND c.status='active'
           GROUP BY c.id ORDER BY c.id LIMIT ?""", (kana,)
    ).fetchall()
    kana_answers = [row[0] for row in connection.execute(
        """SELECT DISTINCT COALESCE(NULLIF(f.reading,''), f.surface)
           FROM concepts c JOIN concept_forms f ON f.concept_id=c.id
           WHERE c.concept_type='kana' AND c.status='active' ORDER BY c.id LIMIT 40"""
    )]
    for row in kana_rows:
        choices, correct = _rotate(row[2], kana_answers, row[0])
        result.append({"concept_id": row[0], "skill": "reading", "prompt": f"Choose the reading for {row[1]}", "choices": choices, "correct_index": correct})

    vocabulary_rows = connection.execute(
        """SELECT c.id, c.display_text, MIN(s.meaning) answer
           FROM concepts c JOIN concept_senses s ON s.concept_id=c.id AND s.language='en'
           WHERE c.concept_type='lexeme' AND c.status='active'
           GROUP BY c.id HAVING answer<>'' ORDER BY c.id LIMIT ?""", (vocabulary,)
    ).fetchall()
    meanings = [row[0] for row in connection.execute(
        "SELECT DISTINCT meaning FROM concept_senses WHERE language='en' AND meaning<>'' ORDER BY id LIMIT 80"
    )]
    for row in vocabulary_rows:
        choices, correct = _rotate(row[2], meanings, row[0])
        result.append({"concept_id": row[0], "skill": "meaning", "prompt": f"Choose the meaning of {row[1]}", "choices": choices, "correct_index": correct})

    grammar_rows = connection.execute(
        """SELECT gd.concept_id, gd.explanation_en, gd.pattern
           FROM grammar_details gd JOIN concepts c ON c.id=gd.concept_id
           WHERE c.status='active' ORDER BY gd.sequence_index LIMIT ?""", (grammar,)
    ).fetchall()
    patterns = [row[0] for row in connection.execute("SELECT pattern FROM grammar_details ORDER BY sequence_index")]
    for row in grammar_rows:
        choices, correct = _rotate(row[2], patterns, row[0])
        result.append({"concept_id": row[0], "skill": "grammar", "prompt": row[1], "choices": choices, "correct_index": correct})
    return result


def start_diagnostic(connection: sqlite3.Connection, learner_id: int, kana: int = 8, vocabulary: int = 16, grammar: int = 12) -> dict[str, Any]:
    if connection.execute("SELECT 1 FROM learners WHERE id=?", (learner_id,)).fetchone() is None:
        raise LearningLoopError(f"Unknown learner: {learner_id}")
    candidates = _diagnostic_candidates(connection, kana, vocabulary, grammar)
    expected = kana + vocabulary + grammar
    if len(candidates) != expected:
        raise LearningLoopError(f"Curriculum can create only {len(candidates)} of {expected} requested questions")
    started = _now()
    with connection:
        previous = connection.execute("SELECT id FROM diagnostic_runs WHERE learner_id=? ORDER BY id DESC LIMIT 1", (learner_id,)).fetchone()
        run_id = int(connection.execute(
            "INSERT INTO diagnostic_runs(learner_id, level_scope, started_at, supersedes_id) VALUES (?, 'N5', ?, ?)",
            (learner_id, started, previous[0] if previous else None),
        ).lastrowid)
        for position, item in enumerate(candidates, 1):
            connection.execute(
                """INSERT INTO diagnostic_items(diagnostic_run_id, position, concept_id, skill, prompt, choices_json, correct_index)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (run_id, position, item["concept_id"], item["skill"], item["prompt"], json.dumps(item["choices"], ensure_ascii=False), item["correct_index"]),
            )
    return {"schema": "Diagnostic/v1", "run_id": run_id, "learner_id": learner_id, "level_scope": "N5", "question_count": len(candidates), "started_at": started}


def next_diagnostic_question(connection: sqlite3.Connection, run_id: int) -> dict[str, Any] | None:
    row = connection.execute(
        """SELECT id, position, prompt, choices_json, skill FROM diagnostic_items
           WHERE diagnostic_run_id=? AND answered_index IS NULL ORDER BY position LIMIT 1""", (run_id,)
    ).fetchone()
    if row is None:
        return None
    return {"item_id": row[0], "position": row[1], "prompt": row[2], "choices": json.loads(row[3]), "skill": row[4]}


def answer_diagnostic(connection: sqlite3.Connection, run_id: int, item_id: int, choice_index: int) -> dict[str, Any]:
    if choice_index not in range(4):
        raise LearningLoopError("choice_index must be between 0 and 3")
    row = connection.execute(
        """SELECT di.concept_id, di.skill, di.correct_index, di.answered_index, dr.learner_id
           FROM diagnostic_items di JOIN diagnostic_runs dr ON dr.id=di.diagnostic_run_id
           WHERE di.id=? AND di.diagnostic_run_id=?""", (item_id, run_id)
    ).fetchone()
    if row is None or row[3] is not None:
        raise LearningLoopError("Diagnostic item is unknown or already answered")
    correct = int(choice_index == row[2])
    answered_at = _now()
    mastery_skill = "comprehension" if row[1] == "grammar" else row[1]
    with connection:
        attempt_id = int(connection.execute(
            """INSERT INTO attempts(learner_id, diagnostic_run_id, concept_id, skill, response_kind, correct, answered_at)
               VALUES (?, ?, ?, ?, 'multiple_choice', ?, ?)""",
            (row[4], run_id, row[0], row[1], correct, answered_at),
        ).lastrowid)
        connection.execute("UPDATE diagnostic_items SET answered_index=?, attempt_id=? WHERE id=?", (choice_index, attempt_id, item_id))
        old = connection.execute("SELECT confidence, evidence_count FROM mastery_states WHERE learner_id=? AND concept_id=? AND skill=?", (row[4], row[0], mastery_skill)).fetchone()
        confidence = max(0.0, min(1.0, (old[0] if old else 0.35) + (0.2 if correct else -0.15)))
        evidence = (old[1] if old else 0) + 1
        connection.execute(
            """INSERT INTO mastery_states(learner_id, concept_id, skill, confidence, evidence_count, last_reviewed_at)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(learner_id, concept_id, skill) DO UPDATE SET
                 confidence=excluded.confidence, evidence_count=excluded.evidence_count,
                 last_reviewed_at=excluded.last_reviewed_at""",
            (row[4], row[0], mastery_skill, confidence, evidence, answered_at),
        )
    return {"correct": bool(correct), "confidence": confidence, "attempt_id": attempt_id}


def finish_diagnostic(connection: sqlite3.Connection, run_id: int) -> dict[str, Any]:
    run = connection.execute("SELECT learner_id, completed_at FROM diagnostic_runs WHERE id=?", (run_id,)).fetchone()
    if run is None:
        raise LearningLoopError(f"Unknown diagnostic run: {run_id}")
    counts = connection.execute(
        """SELECT count(*), count(answered_index), sum(CASE WHEN answered_index=correct_index THEN 1 ELSE 0 END)
           FROM diagnostic_items WHERE diagnostic_run_id=?""", (run_id,)
    ).fetchone()
    if counts[0] == 0 or counts[0] != counts[1]:
        raise LearningLoopError(f"Diagnostic is incomplete: {counts[1]} of {counts[0]} answered")
    skills = {row[0]: {"correct": row[1], "total": row[2]} for row in connection.execute(
        """SELECT skill, sum(CASE WHEN answered_index=correct_index THEN 1 ELSE 0 END), count(*)
           FROM diagnostic_items WHERE diagnostic_run_id=? GROUP BY skill""", (run_id,)
    )}
    score = counts[2] / counts[0]
    band = "N5-ready" if score >= 0.8 else "N5-developing" if score >= 0.5 else "N5-foundations"
    result = {"schema": "DiagnosticResult/v1", "run_id": run_id, "score": round(score, 4), "placement": band, "skills": skills}
    with connection:
        connection.execute("UPDATE diagnostic_runs SET completed_at=?, result_json=? WHERE id=?", (_now(), json.dumps(result), run_id))
    return result


def plan_lesson(connection: sqlite3.Connection, learner_id: int, duration_minutes: int = 15) -> dict[str, Any]:
    if duration_minutes < 5 or duration_minutes > 60:
        raise LearningLoopError("Lesson duration must be between 5 and 60 minutes")
    if connection.execute("SELECT 1 FROM learners WHERE id=?", (learner_id,)).fetchone() is None:
        raise LearningLoopError(f"Unknown learner: {learner_id}")
    grammar_rows = connection.execute(
        """SELECT gd.concept_id, gd.pattern, gd.sequence_index, COALESCE(ms.confidence,0)
           FROM grammar_details gd
           LEFT JOIN mastery_states ms ON ms.learner_id=? AND ms.concept_id=gd.concept_id AND ms.skill='comprehension'
           ORDER BY gd.sequence_index""", (learner_id,)
    ).fetchall()
    target = None
    for row in grammar_rows:
        if row[3] >= 0.8:
            continue
        unmet = connection.execute(
            """SELECT count(*) FROM concept_relations cr
               LEFT JOIN mastery_states ms ON ms.learner_id=? AND ms.concept_id=cr.to_concept_id AND ms.skill='comprehension'
               WHERE cr.from_concept_id=? AND cr.relation_type='prerequisite' AND COALESCE(ms.confidence,0)<0.6""",
            (learner_id, row[0]),
        ).fetchone()[0]
        if unmet == 0:
            target = row
            break
    if target is None:
        target = next((row for row in grammar_rows if row[3] < 0.8), None)
    if target is None:
        raise LearningLoopError("No active grammar target remains")
    vocabulary = [dict(row) for row in connection.execute(
        """SELECT c.id concept_id, c.display_text surface, f.reading, MIN(s.meaning) meaning_hint
           FROM grammar_vocabulary_requirements gvr JOIN concepts c ON c.id=gvr.vocabulary_concept_id
           LEFT JOIN concept_forms f ON f.concept_id=c.id LEFT JOIN concept_senses s ON s.concept_id=c.id AND s.language='en'
           WHERE gvr.grammar_concept_id=? AND gvr.resolution_status='resolved'
           GROUP BY c.id ORDER BY gvr.role, c.id LIMIT 6""", (target[0],)
    )]
    review = [dict(row) for row in connection.execute(
        """SELECT c.id concept_id, c.display_text surface, f.reading, MIN(s.meaning) meaning_hint
           FROM mastery_states ms JOIN concepts c ON c.id=ms.concept_id
           LEFT JOIN concept_forms f ON f.concept_id=c.id LEFT JOIN concept_senses s ON s.concept_id=c.id AND s.language='en'
           WHERE ms.learner_id=? AND ms.confidence<0.6 AND c.concept_type IN ('kana','lexeme')
           GROUP BY c.id ORDER BY ms.confidence, ms.last_reviewed_at LIMIT 4""", (learner_id,)
    )]
    packet = {"schema": "LessonPacket/v1", "level": "N5", "duration_minutes": duration_minutes,
              "grammar_targets": [{"concept_id": str(target[0]), "surface": target[1], "skill": "grammar"}],
              "vocabulary_targets": [{**item, "concept_id": str(item["concept_id"]), "skill": "meaning"} for item in vocabulary],
              "review_targets": [{**item, "concept_id": str(item["concept_id"]), "skill": "review"} for item in review],
              "theme": "romance", "content_boundary": "romance-only; non-explicit", "quiz_question_count": 4}
    started = _now()
    with connection:
        session_id = int(connection.execute(
            "INSERT INTO learning_sessions(learner_id, session_type, lesson_packet_json, started_at) VALUES (?, 'lesson', ?, ?)",
            (learner_id, json.dumps(packet, ensure_ascii=False), started),
        ).lastrowid)
    packet["session_id"] = session_id
    return packet
