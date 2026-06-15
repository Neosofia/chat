# Chat Service

The Chat Service is the platform's authoritative store for user-scoped conversation while message content is still PHI-complete. Channel adapters for app, web, and SMS share one ingestion and retrieval API so every channel reads the same timeline; this service persists the full unredacted message, ties each conversation to a care episode, and runs the inline care assistant on patient turns. Deidentification, clean analytics stores, channel delivery (push, SMS receipts, offline queues), and long-term audit aggregation live in the services that own those concerns — not here.

Callers reach this service when a patient or clinician sends a message, lists or opens a thread, or when the care assistant must draft a reply. **Authentication** validates platform JWTs; **Care Episode** owns procedure-scoped episode data and is the only producer of authoritative interaction `context` on create (see [015-care-episode-service.md](https://github.com/Neosofia/cdp/blob/main/specs/015-care-episode-service.md) FR-015). Production patient chat is proxied through Care Episode (`POST …/care-episodes/{patient}/chat/interactions`); the UI does not open bare interactions on Chat directly. **User** registry roles and tenant membership are enforced elsewhere; this service resolves clinician same-tenant access from `tenant_uuid` stored in interaction `context`, not from outbound User Service calls. **Inference** powers the care assistant on completion turns. Patient-facing deployments require `INFERENCE_*` configuration; when unavailable, completions fail closed (**503**) and clients must show an explicit unavailable state — not fabricated clinical replies.

## Resources

### Operations

For testers, developers, and system administrators, [OPERATIONS.md](OPERATIONS.md) is the place to start — local tooling, database migrations, ports, and smoke checks. Per-release operator steps and verification are in [INSTALLATION_PLAN.md](INSTALLATION_PLAN.md).

### Changelog

For product owners and release readers, [CHANGELOG.md](CHANGELOG.md) records user-visible chat changes per release ([Keep a Changelog](https://keepachangelog.com/)).

### API Contract

For API consumers, integration testers, and frontend developers, [openapi.json](openapi.json) is the authoritative machine-readable contract for this service. It is maintained in-repo for CI and codegen; it is **not** served over HTTP in any environment.

### Security Policy

For security reviewers, on-call engineers, and contributors, [SECURITY.md](SECURITY.md) documents the threat model, Cedar authorization boundaries, and logging rules for this service.

### License

AGPL-3.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE). Deploy-time AI assistant prompts are treated as operator configuration; see NOTICE.

### Feature Specification

For product owners, architects, and new contributors, the [feature spec](https://github.com/Neosofia/cdp/blob/main/specs/001-chat-service.md) describes goals, functional requirements, and acceptance criteria. Care-episode context injection and the patient chat proxy are specified in [015-care-episode-service.md](https://github.com/Neosofia/cdp/blob/main/specs/015-care-episode-service.md) FR-015.

### Governance & Architecture Decisions

For architects and senior engineers, the [project constitution](https://github.com/Neosofia/cdp/blob/main/architecture/constitution.md) captures platform-wide principles. [ADR-0003](https://github.com/Neosofia/cdp/blob/main/architecture/adrs/0003-store-categorical-columns-as-integer-enums.md) records integer enum storage for categorical columns such as `channel`; [ADR-0008](https://github.com/Neosofia/cdp/blob/main/architecture/adrs/0008-published-json-schema-contracts-for-api-testing.md) establishes the published OpenAPI contract approach used here.

## Care Episode Context Boundary

Episode fields (procedure name, dates, risk, patient display name, organisation binding) are **authored by Care Episode** and supplied to Chat only on interaction create. The route gate in `src/routes/interactions.py` enforces:

- `POST /api/v1/users/{user_uuid}/interactions` requires a non-empty `context` object.
- Only a `care-episode` **service** JWT may supply `context`; patient or clinician tokens that include `context` are rejected.
- Creates without `context` are rejected.

Chat normalizes and persists `context` on `chat_interactions.context` (JSONB). Completions and later reads use that stored blob; Chat does not re-fetch episode state from Care Episode on every message. Service-token creates use `src/clients/chat_client.py` in Care Episode; patient completions pass the patient JWT through the CE proxy.

## Authorization & Tenant Boundary

Cedar policies in `policies/policy.cedar` are evaluated in-process via `authorization-in-the-middle`. Entity payloads are built in `src/authorization/entities.py`. Catalog resources mirror REST layout:

* **`chat::InteractionCatalog`** — `GET|POST …/users/{user_uuid}/interactions`, tenant/user last-activity aggregates
* **`chat::MessageCatalog`** — `GET|POST …/interactions/{chat_interaction_uuid}/messages`

For both catalog types, `resource.tenantId` is resolved in order:

1. **Care Episode create** — `tenant_uuid` from the request `context` (same trust boundary as other episode fields).
2. **Patient self-scope** — `tenantId` from the caller's JWT (`neosofia:tenant_uuid`).
3. **Clinician cross-user** — `tenant_uuid` from persisted interaction `context` (local database read at authorization time).

If tenant cannot be resolved, cross-user clinician permits fail closed. This service does not call the User registry for authorization.

## Chat Naming Glossary

To trace conversation identity from HTTP routes through storage and Cedar evaluation, we keep these terms distinct:

* **Care episode** — Procedure-scoped clinical grouping owned by **Care Episode** ([015](https://github.com/Neosofia/cdp/blob/main/specs/015-care-episode-service.md)). Chat does not own episode lifecycle.
* **Chat interaction** — A conversation window stored in `chat_interactions`, scoped under a platform user (`user_uuid`). Identified by `chat_interaction_uuid`.
* **Interaction `context`** — JSON object on the interaction row, written at create time by Care Episode. Includes `tenant_uuid` for organisation binding and episode fields for the care assistant. Not supplied by patient or clinician callers directly.
* **Message** — A single turn in an interaction (`messages` table), with `sender_type` (patient, ai_agent, clinician).
* **API path `user_uuid`** — The platform user whose thread is being accessed (`/api/v1/users/{user_uuid}/…`). For patients acting on self, this matches JWT `sub`.
* **Cedar `resource.tenantId`** — Organisation scope on the catalog resource for clinician permits. Sourced from interaction `context.tenant_uuid` or the principal JWT — not from a live User Service lookup.
* **JWT `neosofia:tenant_uuid`** — Organisation claim on human tokens from **Authentication**; maps to Cedar principal `tenantId`.
