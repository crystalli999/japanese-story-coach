import unittest

from japanese_story_coach.contracts import LessonPacket, LessonTarget
from japanese_story_coach.privacy import PrivacyError, _check_strings, deepseek_story_payload
from japanese_story_coach.providers import DeepSeekStoryQuizGenerator


def packet(**changes):
    values = {
        "level": "N5", "duration_minutes": 15,
        "grammar_targets": (LessonTarget("grammar-want", "～たい", meaning_hint="want to"),),
        "vocabulary_targets": (LessonTarget("vocab-movie", "映画", "えいが", "movie"),),
        "theme": "two classmates arranging a first date",
        "content_boundary": "romance-only; non-explicit", "quiz_question_count": 4,
    }
    values.update(changes)
    return LessonPacket(**values)


class RecordingTransport:
    def __init__(self):
        self.payload = None

    def complete_json(self, payload):
        self.payload = payload
        return {"story": "generated"}


class PrivacyTests(unittest.TestCase):
    def test_deepseek_receives_only_structured_lesson_targets(self):
        transport = RecordingTransport()
        result = DeepSeekStoryQuizGenerator(transport).generate_raw(packet())
        encoded = repr(transport.payload).casefold()
        self.assertEqual({"story": "generated"}, result)
        for forbidden in ("source_path", "raw_source", "review_history", "/users/"):
            self.assertNotIn(forbidden, encoded)
        self.assertEqual("multiple_choice", transport.payload["quiz"]["format"])

    def test_unapproved_content_boundary_and_raw_source_fields_are_rejected(self):
        with self.assertRaisesRegex(PrivacyError, "romance-only"):
            deepseek_story_payload(packet(content_boundary="explicit"))
        with self.assertRaisesRegex(PrivacyError, "forbidden"):
            _check_strings({"raw_source": "private passage"})

    def test_long_passage_cannot_hide_in_structured_field(self):
        with self.assertRaisesRegex(PrivacyError, "structured-target limit"):
            deepseek_story_payload(packet(theme="長" * 501))


if __name__ == "__main__":
    unittest.main()
