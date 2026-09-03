---
id: jsc-profile-before-normalization
date: 2026-09-03
scope: project
projects: [japanese-story-coach]
environments: [macbook-pro-14-m3pro, python-3.11, sqlite, apkg]
symptoms: Anki field names and meanings vary by note model, so generic positional import can silently misclassify learning data.
root_cause: APKG defines structure but not a universal semantic mapping for note fields.
fix_pattern: Require an explicit note-model normalization profile and fail before curriculum writes when a model is unsupported.
verification: Supported Hiragana and Genki models import transactionally and idempotently; an unknown synthetic model leaves curriculum tables empty.
tags: [anki, normalization, provenance, fail-closed]
---

# Profile Anki models before normalization

Preserve all source fields, but create canonical curriculum concepts only through a reviewed model-name/field mapping encoded in the importer. This prevents a convenient generic parser from turning unknown fields into incorrect teaching facts.
