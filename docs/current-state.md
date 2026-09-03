# Current state

Last updated: 2026-09-03

- Local planning repository created on the MacBook.
- Product key: `japanese-story-coach`.
- Scope is an N5-first adaptive learning prototype.
- Stage 1 local foundation exists: private paths, SQLite migrations, metadata inventory, contracts, privacy filtering, and tests.
- Stage 2A adds read-only Anki package inspection and content-free coverage reporting; it does not import note contents.
- No curriculum content has been imported and no source file has been copied into the repository.
- GitHub origin `https://github.com/crystalli999/japanese-story-coach` is connected; `main` was clean and synchronized before Stage 1 work.
- No deployment, external AI provider, or synchronization is configured.
- The real Hiragana and Genki starter packages were inspected through disposable database copies: 1,180 notes, 2,256 cards, no orphan cards, no missing media, and no review history.
- Combined Anki coverage includes vocabulary, readings, meanings, audio, and lesson sequencing but not grammar; selective PDF work remains deferred until a grammar gap plan exists.
- No OCR, permanent curriculum import, DeepSeek call, complete UI, or story response parser exists.
- iMac availability and path are unknown.

## Verification

- 14 tests cover private paths, migrations, inventory safety, provider privacy, malformed APKG rejection, relationship/media warnings, content-free reporting, and combined coverage.
