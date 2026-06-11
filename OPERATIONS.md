# Operations

## Local development

1. Sync dependencies:

   ```bash
   uv sync
   ```

2. Configure environment (copy `.env.example` to `.env`). Required: database URLs, `JWT_AUDIENCE=chat`, and `JWT_JWKS_URI` or `JWT_PUBLIC_KEY`.

   Compose example (Postgres on host port **5001**):

   ```dotenv
   MIGRATION_DATABASE_URL=postgresql+psycopg://chat_template:change-me@localhost:5001/cdp_chat
   APP_DATABASE_URL=postgresql+psycopg://app:change-me@localhost:5001/cdp_chat
   JWT_JWKS_URI=http://localhost:8014/.well-known/jwks.json
   JWT_AUDIENCE=chat
   ```

3. Apply migrations (audit SQL from `templates/sql/audit` in the monorepo, or baked into the image):

   ```bash
   uv run alembic upgrade head
   ```

4. Run tests:

   ```bash
   uv run --dev -m pytest -q
   ```

5. Start the service (default port **8001**):

   ```bash
   uv run --dev -m gunicorn -c src/gunicorn.py src.app:app
   curl http://localhost:8001/health
   ```

6. Local JWT for protected routes:

   ```bash
   uv run scripts/gen_dev_jwt.py --type Patient --sub p1
   ```

**Care assistant (fail closed):** Set all three `INFERENCE_*` variables for local patient-chat testing. When inference is unset or the provider is unreachable, `POST …/completions` returns **503**, no `ai_agent` message is written, and `GET /meta/enums` reports `assistant.available: false`. The CDP patient UI disables send and shows an unavailable message — it does not synthesize clinical replies. Clinician-authored messages and clinician **intervention** (AI paused) are unchanged.

Other optional settings (prompts, sender taxonomy, rate limits): see commented keys in `.env.example`. Active enum labels: `GET /meta/enums`.

## Docker build and run

From this repository:

```bash
docker build --target runtime -t chat:local .
docker run -d --rm -p 8001:8001 -e ENV=development --env-file .env --name chat-dev chat:local
```

Run migrations before or via `preDeployCommand` (see `railway.toml`).

## Public cloud deployment

Shared JWT, JWKS, CORS, healthcheck, and PaaS guidance:

**→ [infrastructure/public-cloud/OPERATIONS.md](https://github.com/Neosofia/infrastructure/blob/main/public-cloud/OPERATIONS.md)**

**Service-specific:**

- `JWT_AUDIENCE` must include **`chat`**.
- `JWT_JWKS_URI` → authentication service (for example `http://authentication:8014/.well-known/jwks.json`).
- Interaction create accepts `context` only from **care-episode** service tokens; patient channels open interactions via the Care Episode proxy.
- **Care assistant:** `INFERENCE_COMPLETIONS_URL`, `INFERENCE_API_KEY`, and `INFERENCE_MODEL` are **required** for patient-facing deployments. Completions fail closed (**503**) when inference is unavailable; private prompts via `AGENT_*_FILE` (see [NOTICE](NOTICE)).

## Test matrix

- `tests/unit/` — business logic and routes with isolated patches.
- `tests/integration/` — Flask client, OpenAPI contract, response shapes.
- `tests/integration/test_container.py` — built image health (slow; needs Docker).
