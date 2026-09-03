CREATE TABLE anki_note_models (
    id INTEGER PRIMARY KEY,
    source_file_id INTEGER NOT NULL REFERENCES source_files(id),
    external_id TEXT NOT NULL,
    name TEXT NOT NULL,
    fields_json TEXT NOT NULL,
    templates_json TEXT NOT NULL,
    UNIQUE(source_file_id, external_id)
);

CREATE TABLE anki_decks (
    id INTEGER PRIMARY KEY,
    source_file_id INTEGER NOT NULL REFERENCES source_files(id),
    external_id TEXT NOT NULL,
    name TEXT NOT NULL,
    parent_name TEXT,
    UNIQUE(source_file_id, external_id)
);

CREATE TABLE anki_notes (
    id INTEGER PRIMARY KEY,
    source_file_id INTEGER NOT NULL REFERENCES source_files(id),
    external_id TEXT NOT NULL,
    note_model_id INTEGER NOT NULL REFERENCES anki_note_models(id),
    fields_json TEXT NOT NULL,
    tags_json TEXT NOT NULL,
    source_checksum INTEGER,
    UNIQUE(source_file_id, external_id)
);

CREATE TABLE anki_cards (
    id INTEGER PRIMARY KEY,
    source_file_id INTEGER NOT NULL REFERENCES source_files(id),
    external_id TEXT NOT NULL,
    note_id INTEGER NOT NULL REFERENCES anki_notes(id),
    deck_id INTEGER NOT NULL REFERENCES anki_decks(id),
    template_ordinal INTEGER NOT NULL,
    source_queue INTEGER,
    source_type INTEGER,
    UNIQUE(source_file_id, external_id)
);

CREATE TABLE anki_media (
    id INTEGER PRIMARY KEY,
    source_file_id INTEGER NOT NULL REFERENCES source_files(id),
    archive_member TEXT NOT NULL,
    original_name TEXT NOT NULL,
    byte_size INTEGER NOT NULL,
    UNIQUE(source_file_id, archive_member)
);

CREATE TABLE anki_note_media (
    note_id INTEGER NOT NULL REFERENCES anki_notes(id),
    media_id INTEGER NOT NULL REFERENCES anki_media(id),
    PRIMARY KEY(note_id, media_id)
);

CREATE UNIQUE INDEX idx_anki_source_locator
ON source_locators(source_file_id, locator_kind, external_id)
WHERE external_id IS NOT NULL AND locator_kind IN ('anki_note', 'anki_card', 'deck');

CREATE INDEX idx_anki_cards_note ON anki_cards(note_id);
CREATE INDEX idx_anki_cards_deck ON anki_cards(deck_id);
