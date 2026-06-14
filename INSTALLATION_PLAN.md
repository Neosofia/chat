# Product Installation Plan

Per-version deploy steps for operators. User-visible changes: [CHANGELOG.md](CHANGELOG.md).

## chat v0.6.0

**Image:** `ghcr.io/neosofia/chat:v0.6.0` (tag `chat/v0.6.0`)

**Deploy:**

1. Rebuild and deploy **chat v0.6.0** (no config changes; SDK **`authorization-in-the-middle/v0.7.1`** only).

**Verify:**

- `GET /health` → `"version": "0.6.0"`.
- Care Episode service token interaction create and patient/clinician chat flows unchanged from v0.5.0.

---

## chat v0.5.0

**Image:** `ghcr.io/neosofia/chat:v0.5.0` (tag `chat/v0.5.0`)

**Mandatory (same change window):**

- Deploy **care-episode v0.4.0** (or newer) so patient channels open chat through the CE proxy with authoritative `context`.
- Redeploy channel clients that previously called Chat `POST …/interactions` with client-built context; those calls now return **400**.

**Deploy:**

1. `alembic upgrade head` before starting the new container (revision **007** — no new migration in this release).
2. Remove **`USER_SERVICE_BASE_URL`** from environment if present (no longer read).
3. Set **`INFERENCE_COMPLETIONS_URL`**, **`INFERENCE_API_KEY`**, and **`INFERENCE_MODEL`**. **Required** for any environment where patients can use the care assistant. When unset or unreachable, completions return **503** and no assistant message is persisted — there is no stub fallback.
4. Pull image and redeploy; keep existing DB, JWT, and Cedar settings unless your environment customizes them.

**Verify:**

- `GET /health` → `"version": "0.5.0"`; `"status": "ok"` when inference is configured and reachable (otherwise `"status": "degraded"` — acceptable only when patient assistant is intentionally disabled).
- `GET /meta/enums` → `assistant.available: true` when inference is configured.
- `alembic current` → head **007**.
- Care Episode service token: `POST /api/v1/users/{user_uuid}/interactions` with non-empty `context` → **201**.
- Patient JWT without CE service token: same path with `context` in body → **400**.
- Patient-facing: authorized `POST …/completions` (via CE proxy or Chat) returns **200** with a persisted assistant message when inference is up; returns **503** when inference is down (UI must show unavailable, not fabricate replies).

---

## chat v0.4.0

**Image:** `ghcr.io/neosofia/chat:v0.4.0` (tag `chat/v0.4.0`)

**Mandatory (same change window):**

- Redeploy clients on user-scoped API paths (`/api/v1/users/{user_uuid}/…`). Flat `/api/v1/interactions` routes and completion fields `ai_disabled` / `patient_message` are removed.

**Deploy:**

1. `alembic upgrade head` before starting the new container (revision **007**).
2. Set **`INFERENCE_COMPLETIONS_URL`**, **`INFERENCE_API_KEY`**, and **`INFERENCE_MODEL`** for patient-facing assistant use (completions fail closed with **503** when unavailable).
3. Pull image and redeploy; keep existing DB, JWT, and Cedar settings unless your environment customizes them.

**Verify:**

- `GET /health` → `"version": "0.4.0"`.
- `alembic current` → head **007**.
- Authorized JWT: `GET /api/v1/users/{user_uuid}/interactions` → **200**.

---

## chat v0.3.0

**Image:** `ghcr.io/neosofia/chat:v0.3.0` (tag `chat/v0.3.0`)

**Deploy:**

1. `alembic upgrade head` (revision **005**).
2. Pull image and redeploy.

**Verify:**

- `GET /health` → `"version": "0.3.0"`.
- `GET /meta/enums` → **200**.
