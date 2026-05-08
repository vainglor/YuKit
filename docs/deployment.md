# YuKit Deployment Notes

This is the runnable YuKit V1 platform slice. PostgreSQL stores users, sessions, favorites, preferences, and execution history. Redis backs rate limiting and the ARQ worker queue. The first concrete tools are JSON Format, Timestamp, Base64, Regex Test, and authenticated async Text Hash.

## Local App

```powershell
cd frontend
pnpm install
pnpm build
cd ..
Copy-Item .env.example .env
docker compose up --build
```

Open `http://localhost:8080`. Compose publishes HTTP on `${YUKIT_HTTP_PORT:-8080}` and HTTPS on `${YUKIT_HTTPS_PORT:-8443}` for local testing. In production, set `YUKIT_SITE_ADDRESS=your-domain.example`, `YUKIT_HTTP_PORT=80`, and `YUKIT_HTTPS_PORT=443` so Caddy can manage HTTPS certificates, or put YuKit behind an external load balancer.

For GitHub OAuth, set `YUKIT_GITHUB_CLIENT_ID`, `YUKIT_GITHUB_CLIENT_SECRET`, `YUKIT_PUBLIC_BASE_URL`, and `YUKIT_API_BASE_URL` in `.env`. Local development can use `YUKIT_DEV_AUTH_ENABLED=true` for the built-in dev login route.

## Production Upgrade Flow

Use pinned image tags in production instead of relying only on `latest`.

```bash
docker compose --profile ops run --rm migrate
docker compose pull api worker caddy
docker compose up -d api worker caddy
docker compose ps
curl -fsS http://localhost/api/ready
```

Rollback is the reverse operation: set the previous image tag in `.env` or your Compose override, then run `docker compose up -d api worker`.

## Health Checks

Compose defines health checks for:

- `api`: `GET /api/health`
- `caddy`: proxied `GET /api/health`
- `postgres`: `pg_isready`
- `redis`: `redis-cli ping`

Readiness is available at `GET /api/ready` and reports database and Redis status.

## Backups

Run an on-demand PostgreSQL backup:

```bash
mkdir -p backups
docker compose --profile ops run --rm postgres-backup
```

Keep at least 7 daily and 4 weekly backups. Redis is not the source of truth for user data, but append-only persistence is enabled for queue durability.

## Security Guardrails

- Keep `YUKIT_DEV_AUTH_ENABLED=false` in production.
- Use a long random `YUKIT_SESSION_SECRET`.
- Configure GitHub OAuth callback to match `YUKIT_API_BASE_URL`.
- Caddy applies security headers and a 2 MB request body limit.
- API docs are disabled when `YUKIT_ENVIRONMENT=production`.
- OAuth callback state is validated before token exchange.

## Development Servers

Run the API:

```powershell
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

Run the frontend:

```powershell
cd frontend
pnpm dev
```

Open `http://localhost:5173`.
