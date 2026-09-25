# Changelog

All notable changes to this project are documented here.

## Unreleased

No changes yet.

## 0.3.0 — 2026-09-25

### Added

- Tenant and role authorization before retrieved records enter model context.
- Persistent SQLite approval workflow with expiration and idempotency.
- Separation of requester and approver plus one-way approval consumption.
- Synthetic incident-assistant example with no external side effects.
- Threat model covering trust boundaries, controls and known limitations.
- Dataset-backed evaluations with per-category metrics and a CI threshold.
- Explicit disclosure of the project's AI-assisted provenance.

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
