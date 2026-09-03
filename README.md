# Japanese Story Coach

A planned adaptive Japanese-learning application built around short, original BL-themed stories and conversations, daily practice, learner memory, and motivating progress toward JLPT goals.

## Current stage

Stage 1 local foundation is implemented. It creates a private SQLite database outside Git, inventories supported files by metadata and SHA-256 without importing their contents, and defines privacy-safe interfaces for future Anki, selective PDF, FSRS, lesson-planning, and DeepSeek story/quiz work. No corpus, OCR, model call, complete UI, or deployment is connected yet.

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

## Tests

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```
