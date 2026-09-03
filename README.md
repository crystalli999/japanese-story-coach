# Japanese Story Coach

A planned adaptive Japanese-learning application built around short, original BL-themed stories and conversations, daily practice, learner memory, and motivating progress toward JLPT goals.

## Current stage

Stage 3 is implemented. The private database contains the approved Hiragana and Genki imports, a versioned 24-point N5 grammar spine, repeatable 36-question placement diagnostics, learner-memory updates, and prerequisite-aware local lesson planning. No PDF/OCR import, model call, complete learning UI, or deployment is connected yet.

## Initial scope

- Hiragana and katakana assessment
- N5 placement and adaptive daily practice
- Learner memory for strengths, mistakes, confidence, and review history
- Original short stories and conversations targeting current grammar and vocabulary
- Comprehension, recall, and memorization quizzes
- Weekly progress and manga-readiness motivation

See `docs/product-brief.md`, `docs/architecture.md`, and `docs/current-state.md`.

## Local setup

Requires Python 3.11 or newer and has no runtime package dependencies.

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e .
cp .env.example .env
python3 -m japanese_story_coach init
```

By default private state is created at `~/Library/Application Support/Japanese Story Coach`. Set `JSC_DATA_DIR` in your shell to use another location outside this repository. Never commit `.env`, SQLite databases, OCR derivatives, source media, or import staging data.

Preview a read-only metadata inventory without saving it:

```bash
python3 -m japanese_story_coach inventory "/path/to/your/materials"
```

Add `--save` only when you intentionally want the hashes and file metadata recorded in the private database. This still does not extract Anki notes, PDF text, or scripts.

Create a read-only, content-free Anki coverage report:

```bash
python3 -m japanese_story_coach anki-report \
  "/path/to/Japanese_Hiragana.apkg" \
  "/path/to/Genki_1_3rd_edition_with_sound_files.apkg"
```

The command opens a disposable copy of each Anki collection in SQLite query-only mode, validates its structure and media relationships, and removes the copy afterward. The JSON report includes counts, deck/model/field structure, field completeness, duplicates, warnings, and lesson-planning coverage. It excludes note text and source paths and never calls an external provider.

Import approved, supported starter decks into the private database:

```bash
python3 -m japanese_story_coach anki-import \
  "/path/to/Japanese_Hiragana.apkg" \
  "/path/to/Genki_1_3rd_edition_with_sound_files.apkg"
```

Import is automatic after structural validation; there is no manual review gate. It is transactional and idempotent: reimporting refreshes the source-specific Anki rows and provenance without duplicating canonical concepts. Unsupported note models fail before curriculum rows are written. Media metadata and note relationships are imported, but media binaries remain inside the original package.

Load or refresh the bundled N5 grammar spine after importing vocabulary:

```bash
python3 -m japanese_story_coach grammar-seed
```

This is a practical app-curated beginner sequence, not an official JLPT syllabus. The command is transactional and idempotent. Each grammar point records English and Traditional Chinese guidance, grammar prerequisites, and required vocabulary. Vocabulary is linked only when exactly one imported concept matches; missing and ambiguous requirements remain visible for later gap filling.

Create your local learner, take the placement diagnostic, and preview a lesson:

```bash
python3 -m japanese_story_coach learner-create "Li"
python3 -m japanese_story_coach diagnostic-start 1
python3 -m japanese_story_coach diagnostic-next 1
python3 -m japanese_story_coach diagnostic-answer 1 ITEM_ID CHOICE_INDEX
python3 -m japanese_story_coach diagnostic-finish 1
python3 -m japanese_story_coach lesson-plan 1
```

`diagnostic-next` returns four choices indexed `0` through `3`. Repeat `diagnostic-next` and `diagnostic-answer` until all 36 questions are answered, then finish the run. A later retake automatically retains a link to the previous result. Lesson planning is entirely local and saves the structured packet in learner history; it does not call DeepSeek.

## Tests

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```
