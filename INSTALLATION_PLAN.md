# Installation Plan — chat v0.3.0

Per-version deploy and verification steps for operators. For what changed in each release, see [CHANGELOG.md](CHANGELOG.md).

## Deploy steps

1. Pull image `ghcr.io/neosofia/chat:v0.3.0` (tag `chat/v0.3.0`).
2. Run migrations before starting the new runtime container:

   ```bash
   uv run alembic upgrade head
   ```

   Applies revisions through `005` (message channel column).

3. Deploy the chat service with existing `APP_DATABASE_URL`, JWT, and Cedar policy bundle unchanged unless your environment already customizes them.
4. Optional inference env (stub replies used when omitted):

   ```dotenv
   INFERENCE_COMPLETIONS_URL=
   INFERENCE_API_KEY=
   INFERENCE_MODEL=
   ```

## Post-deploy verification

1. `GET /health` returns `"status": "ok"` and `"version": "0.3.0"`.
2. `GET /api/v1/interactions?patient_uuid=<uuid>&care_episode_uuid=<uuid>` returns `200` with `items`.
3. `POST /api/v1/interactions` creates a thread; `POST /api/v1/messages/completions` with `session_start: true` primes an empty thread.
4. After a clinician message exists in a thread, patient `POST /api/v1/messages/completions` returns `ai_disabled: true` and no `assistant_message`.

## Evidence

- Migration `alembic current` shows head `005`.
- Health version matches `0.3.0`.
- Smoke completion flow above succeeds against staging JWT.
