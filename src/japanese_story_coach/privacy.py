from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .contracts import LessonPacket


class PrivacyError(ValueError):
    pass


FORBIDDEN_PROVIDER_KEYS = {
    "source_path", "original_path", "source_fragment", "raw_source", "raw_text",
    "book", "pdf", "manga", "script", "anki", "review_history", "personal_history",
}


def _check_strings(value: Any, path: str = "payload") -> None:
    if isinstance(value, str) and len(value) > 500:
        raise PrivacyError(f"Provider field {path} exceeds the structured-target limit")
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).casefold() in FORBIDDEN_PROVIDER_KEYS:
                raise PrivacyError(f"Provider payload contains forbidden field: {key}")
            _check_strings(child, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _check_strings(child, f"{path}[{index}]")


def deepseek_story_payload(packet: LessonPacket) -> dict[str, Any]:
    if packet.content_boundary != "romance-only; non-explicit":
        raise PrivacyError("Stage 1 permits only the approved romance-only content boundary")
    if not 1 <= packet.quiz_question_count <= 8:
        raise PrivacyError("Quiz question count must be between 1 and 8")
    payload = {
        "task": "Create an original Japanese story and multiple-choice quiz",
        "level": packet.level,
        "duration_minutes": packet.duration_minutes,
        "grammar_targets": [asdict(item) for item in packet.grammar_targets],
        "vocabulary_targets": [asdict(item) for item in packet.vocabulary_targets],
        "review_targets": [asdict(item) for item in packet.review_targets],
        "known_support": [asdict(item) for item in packet.known_support],
        "confusion_targets": list(packet.confusion_targets),
        "theme": packet.theme,
        "content_boundary": packet.content_boundary,
        "quiz": {"format": "multiple_choice", "question_count": packet.quiz_question_count},
        "constraints": ["original content only", "do not quote or imitate source passages"],
    }
    _check_strings(payload)
    return payload
