---
id: jsc-anki-coverage-before-import
date: 2026-09-03
scope: project
projects: [japanese-story-coach]
environments: [macbook-pro-14-m3pro, python-3.11, sqlite, apkg]
symptoms: It was unclear whether expensive PDF extraction was necessary before lesson planning.
root_cause: Source formats were being considered equally before measuring their structured curriculum coverage.
fix_pattern: Generate a content-free structural coverage report from disposable read-only APKG databases before authorizing any corpus import or OCR.
verification: Hiragana and Genki reported intact relationships/media and combined vocabulary, reading, meaning, audio, and sequence coverage, with grammar as the explicit gap.
tags: [anki, coverage, privacy, lesson-planning]
---

# Measure Anki before processing PDFs

Use field/deck/media structure to decide which source deserves implementation effort. For the starter collection, Anki is sufficient to begin vocabulary-oriented lesson planning; grammar requires a separate curated source, while broad PDF OCR can wait.
