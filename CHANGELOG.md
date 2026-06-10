# Changelog

What changed for people who use or depend on this service (operators, integrators, patient and clinician apps — not deploy runbooks). Configuration and verification: [INSTALLATION_PLAN.md](INSTALLATION_PLAN.md).

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [0.3.0] - 2026-06-10

### Added

- `GET /meta/enums` exposes chat enum labels for UI clients.
- Message **channel** dimension on stored messages (migration `005`).

### Changed

- Cedar catalog reads use **`message:list`** (aligned with `@with_security` REST inference); removed `src/bootstrap/capabilities.py` and manual catalog entity wiring.
- Pinned **`authorization-in-the-middle/v0.4.23`** (hyphenated catalog type inference fix).
- OpenAPI contract updated for interactions, messages, and meta routes.

## [0.2.2] - 2026-06-05

### Added

- Patients and clinicians can open, list, and paginate **conversation threads** (`interactions`) scoped to a care episode.
- `POST /api/v1/messages/completions` drafts care-assistant replies, continues an existing thread, or starts a new one when `session_start` is true.
- When a clinician has sent a message in a thread, patient completions return `ai_disabled: true` and no assistant message so the care team owns the reply.

### Changed

- Messages are stored against an interaction thread instead of care-episode columns on each row.

## [0.2.1] - 2026-06-04

### Added

- `GET /health` includes the service **semver** (`version`) for operator probes and platform health dashboards.

## [0.2.0] - 2026-06-03

### Changed

- Message APIs require a valid chat-audience JWT and Cedar policy evaluation in production; only `GET /health` stays public.

## [0.1.0] - 2026-06-03

### Added

- Authoritative PHI-complete chat store with list and create message APIs, Cedar authorization, OpenAPI contract, and database migrations for messages.
