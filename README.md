# Chat Service

Authoritative **PHI-complete store** for patient-facing chat. Channel adapters (app, web, SMS) share one ingestion and retrieval API so conversation history stays durable and unredacted before deidentification, AI analysis, or clinician review run elsewhere. **Care episodes** (clinical context and lifecycle) are owned by the Care Episode Service; this service stores `care_episode_uuid` on each message and will reject new interactions when no active episode exists as the full spec is implemented.

Design background and acceptance criteria: [001-chat-service.md](https://github.com/Neosofia/cdp/blob/main/specs/001-chat-service.md).

## How this service fits into the platform

The Chat Service sits between patient channels and the clinical mesh. Adapters write inbound traffic here; clinicians and operators read stored messages within Cedar-enforced scope; when a **chat interaction** ends, identifier-only events (no message bodies) notify the deidentification pipeline to fetch the full log. Authentication issues platform JWTs; this service validates them and applies chat-specific Cedar policies before returning content. Real-time AI streaming, SMS delivery, and clean analytics stores remain in their owning services.

## What this service does / does not do

| In scope | Elsewhere |
|----------|-----------|
| Durable raw message storage (`messages` table, audit trail) | Care episode lifecycle → **Care Episode** |
| Message list/create and last-activity batch lookup (current API) | Channel protocols (SMS gateway, push) → channel adapters |
| Stub `POST /api/v1/messages/completions` for patient-app development | Production AI Response agent + streaming → **AI Agent** (spec 010) |
| Cedar policies in `policies/` for message read/create | Deidentified / clean chat copy → **Deidentification** (spec 002) |
| Interaction-end events and per-patient rate limits (spec FR-004, FR-009) | Token issuance → **Authentication** |

## Operations and security

- Run, test, migrate, and deploy: **[OPERATIONS.md](OPERATIONS.md)**
- Threat model, authz boundaries, and logging rules: **[SECURITY.md](SECURITY.md)**
- Feature scope and requirements: [001-chat-service.md](https://github.com/Neosofia/cdp/blob/main/specs/001-chat-service.md)

Service listens on **8001** (CDP spec 001 → port 8000 + 1). In local compose, Postgres is on host port **5001** (`cdp_chat`).

## Endpoints

**Public (no JWT):** `GET /health`

**Message API** (`/api/v1/messages`; JWT + Cedar wiring in progress — see `policies/` and `src/authorization/entities.py`):

- `GET /api/v1/messages` — list messages for `patient_uuid` + `care_episode_uuid` (optional `limit`, default 200, max 500)
- `POST /api/v1/messages` — persist inbound or outbound message (`patient_uuid`, `care_episode_uuid`, `sender_type`, `content`; optional `sender_uuid`)
- `POST /api/v1/messages/last-activity` — batch last message timestamp per patient/episode pair
- `POST /api/v1/messages/completions` — development stub for patient chat replies (replaced by AI Agent integration)

`sender_type` is one of `patient`, `ai_agent`, or `clinician`. Message UUIDs are assigned server-side (`uuidv7()`).

Contract: `openapi.json`.
