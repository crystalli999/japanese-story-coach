# Privacy and content controls

- Source files are opened read-only for inventory and hashing.
- Private runtime data must live outside the Git repository.
- Runtime directories use owner-only permissions; the SQLite database uses owner read/write permissions.
- Symlinks are skipped during inventory so an inventory root cannot silently expand its scope.
- Inventory stores paths, types, sizes, and hashes only; Stage 1 performs no corpus extraction.
- Deleted sources are represented as inactive, preserving historical learner references.
- DeepSeek has no configured network transport in Stage 1.
- The external story payload is created from an explicit lesson-packet whitelist.
- Raw source fields, source paths, books, PDFs, manga/scripts, Anki data, and review history are rejected from provider payloads.
- Long strings are rejected to reduce the risk of hiding source passages in an allowed field.
- First-prototype generation is restricted to original, romance-only, non-explicit content and multiple-choice quizzes.
