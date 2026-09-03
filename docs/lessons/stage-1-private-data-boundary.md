---
id: jsc-stage1-private-data-boundary
date: 2026-09-03
scope: project
projects: [japanese-story-coach]
environments: [macbook-pro-14-m3pro, python-3.11, sqlite]
symptoms: Private learning sources and provider-generated stories need different trust boundaries.
root_cause: A generic content pipeline could accidentally place source material in Git or external-model payloads.
fix_pattern: Keep runtime data outside Git, inventory metadata separately, and serialize external payloads through an explicit structured-target whitelist.
verification: Unit tests cover repository-path rejection, owner-only storage, read-only hashing, symlink exclusion, and forbidden provider fields.
tags: [privacy, provenance, local-first, deepseek]
---

# Stage 1 private data boundary

Treat source ingestion and story generation as separate systems. A lesson planner may select canonical targets locally, while an external generator receives only a bounded lesson packet and never receives source files or personal history.
