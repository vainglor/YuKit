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

Open `http://localhost:8080`. Compose publishes HTTP on `${YUKIT_HTTP_PORT:-8080}` and HTTPS on `${YUKIT_HTTPS_PORT:-8443}` for local testing. In production, use `docker-compose.prod.yml` when the server already has OpenResty and PostgreSQL managed outside this repository.

For GitHub OAuth, set `YUKIT_GITHUB_CLIENT_ID`, `YUKIT_GITHUB_CLIENT_SECRET`, `YUKIT_PUBLIC_BASE_URL`, and `YUKIT_API_BASE_URL` in `.env`. Local development can use `YUKIT_DEV_AUTH_ENABLED=true` for the built-in dev login route.

## Image Deployment With ACR, OpenResty, And Existing PostgreSQL

The production stack is split into two pushed images:

- `:api-latest` and `:api-<git-sha>`: FastAPI API, Alembic migrations, and ARQ worker runtime.
- `:web-latest` and `:web-<git-sha>`: compiled Vue app served by Nginx.

`docker-compose.prod.yml` starts only YuKit `web`, `api`, `worker`, `redis`, and one-shot `migrate`. It does not start Caddy or PostgreSQL and does not publish host ports, so it can run beside 1Panel OpenResty and 1Panel PostgreSQL.

For the current Aliyun ACR repository, configure these GitHub Actions secrets:

```text
ACR_REGISTRY=crpi-aa48fntml5lhz63u.cn-shenzhen.personal.cr.aliyuncs.com
ACR_IMAGE_REPOSITORY=crpi-aa48fntml5lhz63u.cn-shenzhen.personal.cr.aliyuncs.com/aliyun_neeko/yukit
ACR_PULL_REGISTRY=crpi-aa48fntml5lhz63u-vpc.cn-shenzhen.personal.cr.aliyuncs.com
ACR_USERNAME=dbp1906
ACR_PASSWORD=<acr-password>
SERVER_HOST=120.25.195.126
SERVER_USER=<ssh-user>
SERVER_PORT=22
SERVER_SSH_KEY=<private-key>
DEPLOY_PATH=/opt/yukit
```

GitHub Actions pushes images through the public ACR address. The ECS server pulls through the VPC ACR address.

## First Server Setup

Create a YuKit deploy directory on the ECS server:

```bash
mkdir -p /opt/yukit
cd /opt/yukit
```

Find the Docker network used by the existing OpenResty container:

```bash
docker inspect 1Panel-openresty-awUd --format '{{range $name, $_ := .NetworkSettings.Networks}}{{println $name}}{{end}}'
```

Use that network as `YUKIT_PROXY_NETWORK`. If PostgreSQL is not already attached to the same network, attach it with a stable alias:

```bash
docker network connect --alias yukit-postgres "$YUKIT_PROXY_NETWORK" 1Panel-postgresql-Dhce
```

If Docker says PostgreSQL is already connected, either use the existing container name `1Panel-postgresql-Dhce` as the database host, or reconnect it during a maintenance window with the `yukit-postgres` alias.

Create the `/opt/yukit/.env` file:

```bash
cat > /opt/yukit/.env <<'EOF'
YUKIT_IMAGE_REPOSITORY=crpi-aa48fntml5lhz63u-vpc.cn-shenzhen.personal.cr.aliyuncs.com/aliyun_neeko/yukit
YUKIT_PROXY_NETWORK=<openresty-network-name>
YUKIT_ENVIRONMENT=production
YUKIT_DEV_AUTH_ENABLED=false
YUKIT_PUBLIC_BASE_URL=http://120.25.195.126
YUKIT_API_BASE_URL=http://120.25.195.126/api
YUKIT_DATABASE_URL=postgresql+asyncpg://<db-user>:<db-password>@yukit-postgres:5432/yukit
YUKIT_REDIS_URL=redis://redis:6379/0
YUKIT_SESSION_SECRET=<long-random-secret>
YUKIT_GITHUB_CLIENT_ID=<github-oauth-client-id>
YUKIT_GITHUB_CLIENT_SECRET=<github-oauth-client-secret>
EOF
```

Create the `yukit` database and user in the existing PostgreSQL instance through 1Panel or `psql`. The database host in `YUKIT_DATABASE_URL` must resolve from the YuKit `api` container.

For GitHub OAuth, configure the callback URL in the GitHub OAuth App:

```text
http://120.25.195.126/api/auth/github/callback
```

## OpenResty Reverse Proxy

Add a site or location rules in the existing OpenResty container that points traffic to the YuKit containers on the shared Docker network:

```nginx
location = /api {
    return 301 /api/;
}

location /api/ {
    proxy_pass http://yukit-api:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Host $host;
}

location / {
    proxy_pass http://yukit-web:80;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Host $host;
}
```

Reload OpenResty after saving the config.

## Manual Production Deploy

After the first CI image push, deploy manually with:

```bash
cd /opt/yukit
docker login --username dbp1906 crpi-aa48fntml5lhz63u-vpc.cn-shenzhen.personal.cr.aliyuncs.com
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml --profile ops run --rm migrate
docker compose -f docker-compose.prod.yml up -d --remove-orphans redis api worker web
docker compose -f docker-compose.prod.yml ps
curl -fsS http://120.25.195.126/api/ready
```

The GitHub Actions `deploy` job runs the same pull, migration, restart, and readiness check automatically on pushes to `main`.

## Production Upgrade And Rollback

The default deployment uses `api-latest` and `web-latest`. For a pinned rollout, edit `/opt/yukit/docker-compose.prod.yml` or add a production override that uses `api-<git-sha>` and `web-<git-sha>`.

Rollback is the reverse operation: set the previous image tag in `docker-compose.prod.yml` or your Compose override, then run `docker compose -f docker-compose.prod.yml up -d api worker web`.

## Health Checks

Compose defines health checks for:

- `api`: `GET /api/health`
- `web`: `GET /health`
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
