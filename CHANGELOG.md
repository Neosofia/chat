# Changelog

What changed for patient and clinician chat experiences. Deploy steps and verification: [INSTALLATION_PLAN.md](INSTALLATION_PLAN.md).

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.6.0] - 2026-06-14

### Changed

- Pinned **`authorization-in-the-middle/v0.7.1`** — principals via shared `resolve_jwt_principal`; removed duplicate service-principal builder.

## [0.5.0] - 2026-06-11

### Changed

- **Interaction create** requires non-empty `context` supplied only by the Care Episode service token; patient and clinician callers receive **400** if they send `context`.
- Clinician cross-user tenant authorization reads `tenant_uuid` from **stored interaction context** (CE-authored at create) instead of calling the User service.
- Care assistant completions **fail closed**: unconfigured or failing inference returns **503**; no synthetic assistant messages are persisted. `GET /meta/enums` reports `assistant.available` from live configuration.

### Removed

- **`USER_SERVICE_BASE_URL`** — Chat no longer looks up patient organization from the User service.

## [0.4.0] - 2026-06-10

### Added

- Conversations, messages, and assistant completions are scoped to a **user** — apps load and post chat under that user’s threads.
- **Last activity** per user for roster and dashboard “last message” timestamps.

### Changed

- Clinicians authorized for a patient’s organization can access that patient’s conversations through the same user-scoped surface.

### Removed

- Care-episode identifiers are no longer stored on chat threads in this service (apps may still attach episode context when opening a conversation).

## [0.3.0] - 2026-06-10

### Added

- Human-readable labels for chat enums (sender types, channels) for UI dropdowns and display.
- A **channel** on each stored message for multi-channel chat later.

## [0.2.2] - 2026-06-05

### Added

- Patients and clinicians can open, list, and switch between **conversation threads**.
- The care assistant can draft replies, continue a thread, or greet the patient when a **new conversation** starts.
- When a clinician has joined a thread, the care assistant stays **paused** in that conversation so the care team owns the reply.

### Changed

- Messages belong to a conversation thread rather than being keyed only by care episode.

## [0.2.1] - 2026-06-04

### Added

- Service version is exposed on the health check for platform monitoring.

## [0.2.0] - 2026-06-03

### Changed

- Message access requires a signed-in user authorized for chat; the health check remains public.

## [0.1.0] - 2026-06-03

### Added

- Authoritative chat message store with list and create APIs and access control.
