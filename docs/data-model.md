# Data model through Stage 3A

## Source knowledge

- `source_collections` records roots and rights classifications.
- `source_files` records original paths, hashes, type, size, and active/inactive state.
- `source_imports` records importer versions, outcomes, and warnings.
- `source_locators` preserves Anki note/card/deck, PDF page/chapter, or script line/page identity.
- `concepts`, `concept_forms`, and `concept_senses` hold canonical curriculum knowledge.
- `source_assertions` preserves each source's claim instead of overwriting conflicting meanings.
- `concept_relations` represents prerequisites, conjugations, confusions, and semantic relationships.
- `anki_note_models` and `anki_decks` preserve source structure.
- `anki_notes` stores private source fields and tags; `anki_cards` preserves note/deck/template relationships.
- `anki_media` and `anki_note_media` preserve manifest and note references without copying media binaries.
- `grammar_details` stores the version, sequence, pattern, formation, and bilingual guidance for each app-curated grammar concept.
- `concept_relations` links each grammar point to its grammar prerequisites using directed `prerequisite` edges.
- `grammar_vocabulary_requirements` records the surface form, reading, teaching role, and deterministic resolution result for vocabulary needed by a grammar point. Missing or ambiguous matches are retained as gaps, not guessed.

## Learner memory

- `learners` stores the local profile and approved content boundary.
- `diagnostic_runs` supports retesting and historical linkage.
- `mastery_states` tracks skill-specific difficulty, stability, retrievability, confidence, evidence, due time, and scheduler version.
- `learning_sessions`, `attempts`, and `mistake_events` preserve learning evidence.
- `confusion_pairs` records repeatedly confused concepts.
- `review_events` preserves auditable scheduler transitions.
- `learner_preferences` stores theme and explanation preferences separately from source knowledge.

Source deactivation does not cascade into concepts or learner history. Later importers must attach every derived assertion to a source locator.

The grammar spine is internally curated application data rather than a claim extracted from a private source. Its `curriculum_version` and `internal_curated` provenance distinguish it from imported Anki assertions. It is a practical N5-oriented sequence, not an official JLPT syllabus.
