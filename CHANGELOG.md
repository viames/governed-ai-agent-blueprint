# Changelog

All notable changes to this project are documented here.

## Unreleased

No changes yet.

## 0.2.0 — 2026-09-25

### Added

- Explicit `ModelOutput` citations supplied by the language-model adapter.
- Rejection of missing citations and record identifiers outside retrieved context.
- Tests for fabricated citations, uncited answers and audit-data minimization.

### Changed

- `LanguageModel.complete()` now returns `ModelOutput` instead of plain text.
- Tool audit events no longer retain request arguments or free-form purpose text.

## 0.1.0 — 2026-09-25

### Added

- Grounded answers with deterministic keyword retrieval.
- Default-deny tool policy with explicit human-approval outcomes.
- Structured audit events, unit tests, executable evaluations and CI.
