CREATE TABLE grammar_details (
    concept_id INTEGER PRIMARY KEY REFERENCES concepts(id),
    slug TEXT NOT NULL UNIQUE,
    sequence_index INTEGER NOT NULL CHECK (sequence_index > 0),
    pattern TEXT NOT NULL,
    formation TEXT NOT NULL,
    explanation_en TEXT NOT NULL,
    explanation_zh_hant TEXT NOT NULL,
    curriculum_version TEXT NOT NULL,
    provenance_type TEXT NOT NULL DEFAULT 'internal_curated' CHECK (provenance_type = 'internal_curated'),
    UNIQUE(curriculum_version, sequence_index)
);

CREATE TABLE grammar_vocabulary_requirements (
    grammar_concept_id INTEGER NOT NULL REFERENCES concepts(id),
    vocabulary_concept_id INTEGER REFERENCES concepts(id),
    surface TEXT NOT NULL,
    reading TEXT,
    role TEXT NOT NULL CHECK (role IN ('example', 'contrast', 'question_word', 'verb', 'adjective', 'noun')),
    resolution_status TEXT NOT NULL CHECK (resolution_status IN ('resolved', 'missing', 'ambiguous')),
    candidate_count INTEGER NOT NULL DEFAULT 0 CHECK (candidate_count >= 0),
    PRIMARY KEY (grammar_concept_id, surface, role)
);

CREATE INDEX idx_grammar_curriculum_order ON grammar_details(curriculum_version, sequence_index);
CREATE INDEX idx_grammar_vocab_concept ON grammar_vocabulary_requirements(vocabulary_concept_id);
