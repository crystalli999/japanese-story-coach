from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol, Sequence


@dataclass(frozen=True)
class ImportPlan:
    source_file_id: int
    source_kind: str
    supported: bool
    warnings: tuple[str, ...] = ()


class CurriculumImporter(Protocol):
    """Anki-first importer boundary; implementations must preserve provenance."""

    def inspect(self, source: Path, source_file_id: int) -> ImportPlan: ...
    def import_into(self, source: Path, source_file_id: int, connection: Any) -> dict[str, int]: ...


@dataclass(frozen=True)
class PdfGapRequest:
    source_file_id: int
    missing_concepts: tuple[str, ...]
    page_ranges: tuple[tuple[int, int], ...] = ()


class SelectivePdfGapFiller(Protocol):
    """Plans bounded page extraction; it does not authorize whole-book OCR."""

    def plan(self, request: PdfGapRequest) -> ImportPlan: ...


@dataclass(frozen=True)
class ReviewState:
    difficulty: float
    stability: float
    retrievability: float
    due_at: datetime
    scheduler: str = "fsrs"
    scheduler_version: str = "unconfigured"


class ReviewScheduler(Protocol):
    """FSRS-compatible boundary; scheduler state remains versioned and replaceable."""

    def review(self, state: ReviewState | None, rating: int, reviewed_at: datetime) -> ReviewState: ...


@dataclass(frozen=True)
class LessonTarget:
    concept_id: str
    surface: str
    reading: str | None = None
    meaning_hint: str | None = None
    skill: str = "recognition"


@dataclass(frozen=True)
class LessonPacket:
    level: str
    duration_minutes: int
    grammar_targets: tuple[LessonTarget, ...]
    vocabulary_targets: tuple[LessonTarget, ...]
    review_targets: tuple[LessonTarget, ...] = ()
    known_support: tuple[LessonTarget, ...] = ()
    confusion_targets: tuple[str, ...] = ()
    theme: str = "romance"
    content_boundary: str = "romance-only; non-explicit"
    quiz_question_count: int = 4


@dataclass(frozen=True)
class QuizQuestion:
    prompt: str
    choices: tuple[str, ...]
    correct_index: int
    explanation: str
    concept_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class StoryQuiz:
    title: str
    story: str
    target_usage: dict[str, tuple[str, ...]]
    questions: tuple[QuizQuestion, ...]


class LessonPlanner(Protocol):
    def plan(self, learner_id: int, at: datetime) -> LessonPacket: ...


class StoryQuizGenerator(Protocol):
    def generate(self, packet: LessonPacket) -> StoryQuiz: ...
