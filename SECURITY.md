# Chat Service — Security Posture

This service follows the [Neosofia Service Security Baseline](https://github.com/Neosofia/templates/blob/main/python/service/SECURITY.md) for transport, JWT validation, rate limiting, logging, container hardening, and CI controls. Platform-wide PHI containment and identity principles are in [CDP SECURITY.md](https://github.com/Neosofia/cdp/blob/main/SECURITY.md).

This document covers only what is specific to the Chat Service.

The Chat Service is the **authoritative PHI-complete store for raw message content**. Downstream deidentification and analytics must not read message bodies from any other service.

To report any security-related issue please email security@neosofia.tech — do not create a public issue.

---

## Role in the Platform

| Concern | This service | Owner elsewhere |
|---------|--------------|-----------------|
| Raw message content at rest | **Source of truth** | — |
| JWT issuance, login, MFA | — | **Authentication** |
| Tier-2 roles and user registry | — | **User** |
| Deidentified / clean analytics stores | — | Deidentification pipeline, clean chat store |
| Channel delivery (SMS, push) | — | Channel adapters, notification |
| Long-term audit aggregation | — | Audit infrastructure |

---

## Trust Boundaries

| Boundary | Control |
|----------|---------|
| Caller identity | Platform JWT from **Authentication**; human `sub` is the authenticated principal |
| API scope | User-scoped nested routes (`/api/v1/users/{user_uuid}/…`); path `user_uuid` must match authorized scope |
| Authorization | Fail-closed Cedar in `policies/policy.cedar`, evaluated in-process via `authorization-in-the-middle` |
| Cross-user tenant match | For principals acting on another user's thread, `tenantId` on the Cedar resource is read from `tenant_uuid` in the interaction `context` persisted at Care Episode–authorized create |
| Public surface | Only `GET /health` is unauthenticated |
| AI completions | OpenAI-compatible inference (`INFERENCE_*`); required for patient-facing assistant; completions fail closed (**503**, no persisted assistant message) when unavailable |

---

## Authorization (Cedar)

Policy bundle: `policies/policy.cedar`. Entity payloads are built in `src/authorization/entities.py`.

Deploy-time sender labels (`MESSAGE_SENDER_TYPES`, `INTERVENTION_SENDER_TYPES`, completion sender types) define which `sender_type` values are accepted and which pause AI completions. Clients read active labels from `GET /meta/enums`.

Policy rules encode **self-scope** (principal uuid matches resource `userUuid`) and **same-tenant** access for authorized cross-user reads and writes. Unknown or unauthorized scope fails closed.

**Interaction create:** `context` is required on `POST …/interactions` and may be supplied only by a `care-episode` service JWT. Patient and clinician callers cannot attach `context`; empty or missing `context` is rejected before persistence.

**Tenant resolution for interaction and message catalogs:** (1) Care Episode create — `tenant_uuid` from request `context`; (2) patient self — principal `tenantId` from JWT; (3) clinician cross-user — `tenant_uuid` from stored interaction `context` (database read during authorization). Chat does not call the User service for tenant lookup.

---

## Sensitive Data

| Data | In API / DB | In logs | External inference |
|------|-------------|---------|-------------------|
| Message body | Yes (PHI-complete) | **No** | Yes, when completions run — only to the configured `INFERENCE_COMPLETIONS_URL` |
| User / interaction UUIDs | Yes | Correlation ids only | No raw identifiers beyond what the model request requires |
| Agent context block | In completion request payload | **No** | Yes, when provided on completion requests |
| Deploy-time prompts | Shipped defaults or `*_FILE` paths | **No** | System prompt content only |

Baseline logging rules apply: no message text, names, or other PHI/PII in log lines. Exception types are logged as `type(exc).__name__` only.

Deploy-time AI assistant prompts are **operator configuration** (see [NOTICE](NOTICE)); operators may supply private prompt files without publishing them.

---

## Deployment Requirements

| Setting | Requirement |
|---------|-------------|
| `JWT_AUDIENCE` | Must include `chat` |
| `JWT_JWKS_URI` / `JWT_PUBLIC_KEY` | Authentication JWKS or PEM — same trust chain as other platform APIs |
| PostgreSQL (`APP_DATABASE_URL`) | Required; interaction `context` supplies cross-user tenant resolution in Cedar |
| `AUTHORIZATION_POLICIES_DIR` | Default `policies`; ship `policy.cedar` in the image |
| `INFERENCE_*` | Required for patient-facing assistant; when unset or unreachable, completion endpoints return **503** and `/health` reports `degraded` |
| SDK wheels | Pin `authentication-in-the-middle` and `authorization-in-the-middle` to published release URLs in production |

---

## Known Limitations

| Item | Status | Notes |
|------|--------|-------|
| Inference unavailable at runtime | Fail closed | Completions return **503**; no stub or synthetic assistant content is persisted. `/health` returns 200 with `degraded` so the service stays operable for history reads |
| No stub assistant path | By design | Misconfigured inference must not produce clinical-sounding placeholder replies ([chat#1](https://github.com/Neosofia/chat/issues/1)) |
| Message content leaves the platform for completions | Accepted | Operators must use a HIPAA-eligible inference endpoint and BAA where required |
| Rate limit storage in-memory | Accepted (baseline) | Set `RATE_LIMIT_STORAGE_URI` to Redis when running multiple replicas |
| Interaction context missing `tenant_uuid` | Fail closed | Missing tenant resolution denies cross-user Cedar permits |

---

## References

- [CDP Platform Security](https://github.com/Neosofia/cdp/blob/main/SECURITY.md)
- [Neosofia Service Security Baseline](https://github.com/Neosofia/templates/blob/main/python/service/SECURITY.md)
- [Constitution](https://github.com/Neosofia/cdp/blob/main/architecture/constitution.md)
- [Feature spec](https://github.com/Neosofia/cdp/blob/main/specs/001-chat-service.md)
