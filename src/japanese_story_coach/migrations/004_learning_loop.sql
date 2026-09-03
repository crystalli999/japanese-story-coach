CREATE TABLE diagnostic_items (
    id INTEGER PRIMARY KEY,
    diagnostic_run_id INTEGER NOT NULL REFERENCES diagnostic_runs(id),
    position INTEGER NOT NULL CHECK (position > 0),
    concept_id INTEGER NOT NULL REFERENCES concepts(id),
    skill TEXT NOT NULL CHECK (skill IN ('recognition', 'reading', 'meaning', 'grammar')),
    prompt TEXT NOT NULL,
    choices_json TEXT NOT NULL,
    correct_index INTEGER NOT NULL CHECK (correct_index BETWEEN 0 AND 3),
    answered_index INTEGER CHECK (answered_index IS NULL OR answered_index BETWEEN 0 AND 3),
    attempt_id INTEGER REFERENCES attempts(id),
    UNIQUE(diagnostic_run_id, position),
    UNIQUE(diagnostic_run_id, concept_id, skill)
);

CREATE INDEX idx_diagnostic_items_run ON diagnostic_items(diagnostic_run_id, position);
CREATE INDEX idx_diagnostic_items_concept ON diagnostic_items(concept_id);
