# Installation Plan — chat v0.2.2

## Deploy steps

1. Pull image `ghcr.io/neosofia/chat:v0.2.2` (tag `chat/v0.2.2`).
2. Run migrations before starting the new runtime container:

   ```bash
   uv run alembic upgrade head
   ```

   Applies revisions `002` (chat interactions), `003` (messages keyed by interaction), and `004` (interaction context JSON).

3. Deploy the chat service with existing `APP_DATABASE_URL`, JWT, and Cedar policy bundle unchanged unless your environment already customizes them.
4. Optional inference env (stub replies used when omitted):

   ```dotenv
   INFERENCE_COMPLETIONS_URL=
   INFERENCE_API_KEY=
   INFERENCE_MODEL=
   ```

## Post-deploy verification

1. `GET /health` returns `"status": "ok"` and `"version": "0.2.2"`.
2. `GET /api/v1/interactions?patient_uuid=<uuid>&care_episode_uuid=<uuid>` returns `200` with `items`.
3. `POST /api/v1/interactions` creates a thread; `POST /api/v1/messages/completions` with `session_start: true` primes an empty thread.
4. After a clinician message exists in a thread, patient `POST /api/v1/messages/completions` returns `ai_disabled: true` and no `assistant_message`.

## Evidence

- Migration `alembic current` shows head `004`.
- Health version matches `0.2.2`.
- Smoke completion flow above succeeds against staging JWT.
