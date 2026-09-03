# Current state

Last updated: 2026-09-03

- Local planning repository created on the MacBook.
- Product key: `japanese-story-coach`.
- Scope is an N5-first adaptive learning prototype.
- Stage 1 local foundation exists: private paths, SQLite migrations, metadata inventory, contracts, privacy filtering, and tests.
- Stage 2A adds read-only Anki package inspection and content-free coverage reporting; it does not import note contents.
- Stage 2B adds direct, validated, transactional import for the approved Hiragana and Genki note models without a manual review gate.
- Hiragana and Genki are imported into the private local database outside Git; no source file or private database has been copied into the repository.
- GitHub origin `https://github.com/crystalli999/japanese-story-coach` is connected; `main` was clean and synchronized before Stage 1 work.
- No deployment, external AI provider, or synchronization is configured.
- The real Hiragana and Genki starter packages were inspected through disposable database copies: 1,180 notes, 2,256 cards, no orphan cards, no missing media, and no review history.
- Combined Anki coverage includes vocabulary, readings, meanings, audio, and lesson sequencing but not grammar; selective PDF work remains deferred until a grammar gap plan exists.
- Verified private database totals: 1,180 notes, 2,256 cards, 54 decks, 883 media records, 1,141 canonical concepts, 1,644 English senses, and 2,889 concept/meaning provenance assertions; integrity is `ok` with zero foreign-key violations.
- No OCR, PDF/script import, DeepSeek call, complete UI, grammar spine, or story response parser exists.
- iMac availability and path are unknown.

## Verification

- 17 tests cover private paths, migrations, inventory safety, provider privacy, APKG inspection, normalization profiles, in-transaction rollback, provenance, deduplication, and idempotent reimport.
