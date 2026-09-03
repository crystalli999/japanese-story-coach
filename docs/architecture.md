# Architecture

Stage 1 establishes a standard-library-first Python core and private SQLite database. Runtime data defaults to `~/Library/Application Support/Japanese Story Coach`, outside the Git repository, with owner-only directory and database permissions.

The future plan should keep these concerns separate:

- Curriculum catalog: kana, vocabulary, kanji, grammar, examples, levels, and provenance
- Learner model: attempts, mastery, confidence, mistakes, and review scheduling
- Diagnostic engine: placement and uncertainty measurement
- Lesson planner: daily selection within a time budget
- Story system: original content constrained by learning targets
- Exercise engine: recognition, recall, comprehension, and memorization
- Progress system: daily/weekly summaries and manga-readiness estimates
- Private reference inventory: read-only metadata derived from permitted local sources

## Implemented boundaries

- `config.py`: private application paths and Git-repository separation guard
- `database.py` and `migrations/`: versioned SQLite schema and migration runner
- `inventory.py`: read-only metadata/SHA-256 inventory for `.apkg`, `.pdf`, `.txt`, and `.md`
- `anki.py`: fail-closed APKG/SQLite inspection and content-free lesson-planning coverage reports
- `anki_importer.py`: transactional profile-based normalization and provenance-preserving Anki import
- `contracts.py`: neutral Anki/curriculum, selective-PDF, FSRS-compatible scheduler, lesson-planner, and story/quiz interfaces
- `privacy.py`: explicit whitelist conversion from a lesson packet to an external story-provider payload
- `providers.py`: transport-injected DeepSeek story boundary with no network implementation in Stage 1
- `grammar.py` and `curriculum/n5_grammar_v1.json`: validated, versioned N5 grammar seed and deterministic links to imported vocabulary
- `learning.py`: repeatable placement diagnostics, learner-memory evidence, and prerequisite-aware local lesson planning

## Data separation

Source collections, files, locators, assertions, concepts, forms, and senses form the curriculum side. Learners, diagnostics, mastery, sessions, attempts, mistakes, confusion pairs, review events, and preferences form the personal-progress side. Sources can become inactive without deleting learner history.

## Approved direction

- Anki is the primary structured curriculum source.
- PDFs are selectively consulted only to fill demonstrated grammar or sequencing gaps.
- FSRS is the initial scheduler behind a replaceable interface.
- The local lesson planner chooses targets; DeepSeek may later receive only the resulting structured packet.
- Generated content is romance-only and non-explicit for the first prototype.
- Raw books, decks, scripts, source paths, and personal review history are forbidden from external provider payloads.

Application framework and complete UI remain future decisions.

## Stage 2A Anki inspection

APKG files remain unchanged. Only the collection database and media manifest are read, with size limits and duplicate-member checks. The collection is copied into a temporary directory, opened with SQLite `mode=ro`, `query_only`, and an integrity check, then deleted automatically. Reports expose structure and counts but omit note contents and absolute source paths.

Coverage dimensions are vocabulary, reading, meaning, audio, lesson sequencing, and grammar. The first real Hiragana + Genki report confirms the decks are suitable for the structured vocabulary side of lesson planning but do not provide a grammar catalog.

## Stage 2B Anki import

Only explicitly supported note models are normalized. Hiragana notes become kana concepts; Genki notes become lexeme concepts keyed by normalized surface and reading. Exact note fields, tags, deck/card relationships, and media references remain private source records, while canonical concepts, forms, English senses, locators, and assertions support future lesson planning.

Each package is validated and hash-matched to its inventory record before a transaction replaces that source's imported Anki rows. A package with an unknown model or unresolved relationship fails rather than guessing a mapping. Reimporting is safe and does not duplicate canonical concepts.

## Stage 3A grammar spine

The application owns a practical beginner sequence of 24 grammar concepts. It stores bilingual English/Traditional Chinese explanations, formations, ordering, and directed prerequisite edges. The seed loader validates the complete graph before writing and refreshes it transactionally and idempotently.

Each point declares a small set of vocabulary requirements used to teach or demonstrate it. Resolution searches active imported kana, kanji, and lexeme concepts by normalized form and optional reading. Exactly one candidate creates a link; zero or multiple candidates become explicit `missing` or `ambiguous` gaps. This boundary lets the future placement test and lesson planner reason about readiness without silently inventing curriculum mappings.

## Stage 3 learning loop

The placement engine creates a deterministic 36-question N5 run: 8 kana-reading, 16 vocabulary-meaning, and 12 grammar-recognition questions. Answer keys stay in the private database and are not included in the next-question response. Each answer writes an attempt and updates the matching current mastery confidence; a retake is a new run linked to its predecessor.

The local planner walks the grammar sequence and selects the earliest unmastered point whose directed prerequisites meet the readiness threshold. It adds uniquely resolved teaching vocabulary plus up to four weak review concepts, persists the packet as a learning session, and preserves the approved romance-only, non-explicit boundary. It performs no network request; the existing privacy filter remains the only future bridge to DeepSeek.
