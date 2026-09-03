from __future__ import annotations

from typing import Any, Protocol

from .contracts import LessonPacket, StoryQuiz
from .privacy import deepseek_story_payload


class JsonTransport(Protocol):
    def complete_json(self, payload: dict[str, Any]) -> dict[str, Any]: ...


class DeepSeekStoryQuizGenerator:
    """Provider-neutral DeepSeek boundary. No network transport is supplied in Stage 1."""

    def __init__(self, transport: JsonTransport):
        self.transport = transport

    def generate_raw(self, packet: LessonPacket) -> dict[str, Any]:
        return self.transport.complete_json(deepseek_story_payload(packet))

    def generate(self, packet: LessonPacket) -> StoryQuiz:
        raise NotImplementedError("Story response validation is scheduled for a later build stage")
