# Grammar spine versioning

Keep curriculum order and learner evidence as separate concerns. Grammar points use stable versioned canonical keys, while mastery and attempts reference concept IDs. A future curriculum revision should receive a new version when meaning or sequencing changes materially; wording corrections within the same approved version may be refreshed idempotently.

Prerequisite direction is from the grammar point being taught to the grammar concept it requires. Vocabulary links are created only for a unique normalized match. Missing or ambiguous requirements are useful import-gap signals and must not be silently assigned to a plausible-looking concept.

The bundled spine is an app-curated practical N5 sequence, not an official JLPT list. Keep that label visible in documentation and future UI.
