---
id: evidence-before-adaptation
date: 2026-09-03
scope: project
projects: [japanese-story-coach]
environments: [macbook-pro-14-m3pro, sqlite]
symptoms: [placement retakes could overwrite conclusions, lesson targets could skip prerequisites]
root_cause: adaptive decisions need durable answer evidence and an explicit readiness graph
fix_pattern: append attempts, derive current confidence, link retakes, and gate new grammar by prerequisite mastery
verification: 24 unit tests including full correct diagnostic, incomplete-run rejection, retake linkage, and prerequisite unlocking
tags: [diagnostic, learner-memory, prerequisites, lesson-planning]
---

# Evidence before adaptation

Keep assessment evidence append-only and treat current confidence as a derived operational state. A retake should supersede a prior conclusion without deleting it. Lesson selection should traverse explicit curriculum prerequisites rather than assume that numeric sequence alone proves readiness.
