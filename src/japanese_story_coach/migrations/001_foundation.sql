CREATE TABLE source_collections (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    root_path TEXT NOT NULL,
    rights_classification TEXT NOT NULL DEFAULT 'private_personal' CHECK (rights_classification IN ('private_personal', 'licensed', 'public_domain', 'unknown')),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE source_files (
    id INTEGER PRIMARY KEY,
    collection_id INTEGER NOT NULL REFERENCES source_collections(id),
    original_path TEXT NOT NULL,
    relative_path TEXT NOT NULL,
    source_kind TEXT NOT NULL CHECK (source_kind IN ('anki', 'pdf', 'script')),
    media_type TEXT NOT NULL,
    byte_size INTEGER NOT NULL CHECK (byte_size >= 0),
    sha256 TEXT NOT NULL CHECK (length(sha256) = 64),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'invalid')),
    first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(collection_id, relative_path)
);

CREATE TABLE source_imports (
    id INTEGER PRIMARY KEY,
    source_file_id INTEGER NOT NULL REFERENCES source_files(id),
    importer TEXT NOT NULL,
    importer_version TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('planned', 'running', 'completed', 'failed')),
    warning_json TEXT NOT NULL DEFAULT '[]',
    started_at TEXT,
    finished_at TEXT
);

CREATE TABLE source_locators (
    id INTEGER PRIMARY KEY,
    source_file_id INTEGER NOT NULL REFERENCES source_files(id),
    locator_kind TEXT NOT NULL CHECK (locator_kind IN ('anki_note', 'anki_card', 'deck', 'pdf_page', 'pdf_chapter', 'script_line', 'script_page')),
    external_id TEXT,
    page_number INTEGER,
    chapter TEXT,
    line_number INTEGER,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    UNIQUE(source_file_id, locator_kind, external_id, page_number, line_number)
);

CREATE TABLE concepts (
    id INTEGER PRIMARY KEY,
    concept_type TEXT NOT NULL CHECK (concept_type IN ('kana', 'lexeme', 'kanji', 'grammar', 'example')),
    canonical_key TEXT NOT NULL,
    display_text TEXT NOT NULL,
    normalized_text TEXT NOT NULL,
    jlpt_level TEXT,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'review')),
    UNIQUE(concept_type, canonical_key)
);

CREATE TABLE concept_forms (
    id INTEGER PRIMARY KEY,
    concept_id INTEGER NOT NULL REFERENCES concepts(id),
    form_type TEXT NOT NULL,
    surface TEXT NOT NULL,
    reading TEXT,
    normalized_surface TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE concept_senses (
    id INTEGER PRIMARY KEY,
    concept_id INTEGER NOT NULL REFERENCES concepts(id),
    language TEXT NOT NULL CHECK (language IN ('ja', 'en', 'zh-hans', 'zh-hant')),
    meaning TEXT NOT NULL,
    part_of_speech TEXT,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'conflicting', 'review'))
);

CREATE TABLE source_assertions (
    id INTEGER PRIMARY KEY,
    locator_id INTEGER NOT NULL REFERENCES source_locators(id),
    concept_id INTEGER NOT NULL REFERENCES concepts(id),
    sense_id INTEGER REFERENCES concept_senses(id),
    assertion_type TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 1.0 CHECK (confidence >= 0 AND confidence <= 1),
    original_value TEXT,
    UNIQUE(locator_id, concept_id, sense_id, assertion_type)
);

CREATE TABLE concept_relations (
    id INTEGER PRIMARY KEY,
    from_concept_id INTEGER NOT NULL REFERENCES concepts(id),
    to_concept_id INTEGER NOT NULL REFERENCES concepts(id),
    relation_type TEXT NOT NULL CHECK (relation_type IN ('prerequisite', 'conjugation', 'synonym', 'antonym', 'confusion', 'contains')),
    confidence REAL NOT NULL DEFAULT 1.0 CHECK (confidence >= 0 AND confidence <= 1),
    UNIQUE(from_concept_id, to_concept_id, relation_type)
);

CREATE TABLE learners (
    id INTEGER PRIMARY KEY,
    display_name TEXT NOT NULL,
    native_languages_json TEXT NOT NULL DEFAULT '["en","zh"]',
    content_boundary TEXT NOT NULL DEFAULT 'romance-only; non-explicit',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE diagnostic_runs (
    id INTEGER PRIMARY KEY,
    learner_id INTEGER NOT NULL REFERENCES learners(id),
    level_scope TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    result_json TEXT,
    supersedes_id INTEGER REFERENCES diagnostic_runs(id)
);

CREATE TABLE mastery_states (
    learner_id INTEGER NOT NULL REFERENCES learners(id),
    concept_id INTEGER NOT NULL REFERENCES concepts(id),
    skill TEXT NOT NULL CHECK (skill IN ('recognition', 'reading', 'meaning', 'recall', 'listening', 'production', 'comprehension')),
    difficulty REAL NOT NULL DEFAULT 0,
    stability REAL NOT NULL DEFAULT 0,
    retrievability REAL NOT NULL DEFAULT 0,
    confidence REAL NOT NULL DEFAULT 0 CHECK (confidence >= 0 AND confidence <= 1),
    evidence_count INTEGER NOT NULL DEFAULT 0 CHECK (evidence_count >= 0),
    last_reviewed_at TEXT,
    next_due_at TEXT,
    scheduler TEXT NOT NULL DEFAULT 'fsrs',
    scheduler_version TEXT NOT NULL DEFAULT 'unconfigured',
    scheduler_state_json TEXT NOT NULL DEFAULT '{}',
    PRIMARY KEY (learner_id, concept_id, skill)
);

CREATE TABLE learning_sessions (
    id INTEGER PRIMARY KEY,
    learner_id INTEGER NOT NULL REFERENCES learners(id),
    session_type TEXT NOT NULL CHECK (session_type IN ('diagnostic', 'lesson', 'review')),
    lesson_packet_json TEXT,
    started_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE TABLE attempts (
    id INTEGER PRIMARY KEY,
    learner_id INTEGER NOT NULL REFERENCES learners(id),
    session_id INTEGER REFERENCES learning_sessions(id),
    diagnostic_run_id INTEGER REFERENCES diagnostic_runs(id),
    concept_id INTEGER NOT NULL REFERENCES concepts(id),
    skill TEXT NOT NULL,
    response_kind TEXT NOT NULL,
    correct INTEGER NOT NULL CHECK (correct IN (0, 1)),
    confidence REAL CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1)),
    response_ms INTEGER CHECK (response_ms IS NULL OR response_ms >= 0),
    hint_used INTEGER NOT NULL DEFAULT 0 CHECK (hint_used IN (0, 1)),
    answered_at TEXT NOT NULL
);

CREATE TABLE mistake_events (
    id INTEGER PRIMARY KEY,
    attempt_id INTEGER NOT NULL REFERENCES attempts(id),
    mistake_type TEXT NOT NULL,
    confused_with_concept_id INTEGER REFERENCES concepts(id),
    details_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE confusion_pairs (
    learner_id INTEGER NOT NULL REFERENCES learners(id),
    concept_a_id INTEGER NOT NULL REFERENCES concepts(id),
    concept_b_id INTEGER NOT NULL REFERENCES concepts(id),
    evidence_count INTEGER NOT NULL DEFAULT 1,
    last_seen_at TEXT NOT NULL,
    PRIMARY KEY (learner_id, concept_a_id, concept_b_id)
);

CREATE TABLE review_events (
    id INTEGER PRIMARY KEY,
    learner_id INTEGER NOT NULL REFERENCES learners(id),
    concept_id INTEGER NOT NULL REFERENCES concepts(id),
    skill TEXT NOT NULL,
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 4),
    reviewed_at TEXT NOT NULL,
    scheduled_days REAL,
    scheduler TEXT NOT NULL,
    scheduler_version TEXT NOT NULL,
    state_before_json TEXT NOT NULL,
    state_after_json TEXT NOT NULL
);

CREATE TABLE learner_preferences (
    learner_id INTEGER NOT NULL REFERENCES learners(id),
    preference_key TEXT NOT NULL,
    preference_value_json TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (learner_id, preference_key)
);

CREATE INDEX idx_source_files_hash ON source_files(sha256);
CREATE INDEX idx_source_locators_file ON source_locators(source_file_id);
CREATE INDEX idx_assertions_concept ON source_assertions(concept_id);
CREATE INDEX idx_mastery_due ON mastery_states(learner_id, next_due_at);
CREATE INDEX idx_attempts_concept ON attempts(learner_id, concept_id, skill);
