# Product Installation Plan

Per-version deploy steps for operators. User-visible changes: [CHANGELOG.md](CHANGELOG.md).

## chat v0.4.0

**Image:** `ghcr.io/neosofia/chat:v0.4.0` (tag `chat/v0.4.0`)

**Mandatory (same change window):**

- Redeploy clients on user-scoped API paths (`/api/v1/users/{user_uuid}/…`). Flat `/api/v1/interactions` routes and completion fields `ai_disabled` / `patient_message` are removed.

**Deploy:**

1. `alembic upgrade head` before starting the new container (revision **007**).
2. Set **`USER_SERVICE_BASE_URL`** (cross-user thread authorization).
3. Set **`INFERENCE_COMPLETIONS_URL`**, **`INFERENCE_API_KEY`**, **`INFERENCE_MODEL`** if AI assistant replies are required (otherwise `/health` reports `degraded`).
4. Pull image and redeploy; keep existing DB, JWT, and Cedar settings unless your environment customizes them.

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
