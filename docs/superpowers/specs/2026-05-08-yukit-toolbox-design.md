# YuKit Toolbox Design Spec

## Overview

YuKit is a public, multi-user web toolbox for running developer and productivity utilities such as JSON formatting, timestamp conversion, Base64 codec, regex testing, file parsing, and other future tools.

The product should stay easy to operate on a self-managed VPS, while leaving room for long-term growth: authenticated user features, tool permissions, rate limits, async execution, execution history, observability, and safer handling of expensive or high-risk tools.

## Design Goals

- Public web access with a mixed access model: lightweight safe tools can be used without login; high-risk, expensive, or personalized features require login.
- Long-term extensibility through a tool plugin contract, shared schemas, execution modes, and metadata-driven frontend rendering.
- Operational stability through separate API and worker processes, Redis-backed queues and rate limits, PostgreSQL persistence, health checks, backups, and predictable deployment.
- Security by default for public traffic: strict input validation, conservative limits, no stack trace leaks, safe CORS, CSRF-aware auth flows, audit-friendly task records, and minimal sensitive-data retention.
- Keep the first implementation practical: no container sandbox in v1, but design the tool contract so risky tools can move to a sandboxed runner later.

## Non-Goals For V1

- Full admin console.
- Team/organization management.
- Paid plans or billing.
- Per-execution container sandboxing.
- Saving raw sensitive inputs by default.
- User-uploaded plugin installation from the web UI.

## Tech Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Frontend | Vue 3 + Vite + TypeScript | User preference; fast SPA development; strong fit for metadata-driven tool pages |
| Backend API | FastAPI | Python-native tool integration; Pydantic validation; OpenAPI schema; dependency injection for auth, DB, Redis, and permissions |
| Worker | Python worker process using Redis queue | Keeps long-running/high-risk work out of the API process; can scale independently |
| Queue/Cache/Rate Limit | Redis | Shared queue backend, session/cache storage, distributed rate limiting |
| Database | PostgreSQL | Durable user, tool, preferences, favorites, and execution history storage |
| ORM/Migrations | SQLAlchemy 2.x + Alembic | Mature PostgreSQL support and explicit schema migrations |
| Auth | GitHub OAuth first; email magic-link interface reserved | GitHub OAuth is fast for a developer-oriented first version; email login can be added without replacing the auth model |
| Reverse Proxy | Caddy or Nginx | TLS termination, static asset serving, API proxying, security headers, compression |
| Container | Docker Compose | Simple VPS deployment with clear service boundaries |
| CI/CD | GitHub Actions + GHCR | Build, test, scan, publish image; VPS pulls immutable image tags |

## Architecture

```
Browser
  |
  v
Reverse Proxy (Caddy/Nginx, TLS, security headers)
  |-----------------------> Frontend SPA assets
  |
  v
FastAPI API
  |---- PostgreSQL: users, auth identities, preferences, favorites, executions
  |---- Redis: rate limits, sessions/cache, queue backend, job status cache
  |---- Worker Queue: async/high-risk/expensive tool jobs
  |
  v
Python Worker(s)
  |---- Tool Registry
  |---- Tool Runtime
  |---- PostgreSQL execution updates
  |---- Redis job progress/result cache
```

FastAPI is the API orchestration layer. It owns request validation, authentication, authorization, tool discovery, rate-limit checks, task creation, result lookup, and lifecycle APIs. It should not run long-running or high-risk tools inside the web process.

Worker processes own async execution. They load the same tool registry, execute queued jobs with timeouts and resource limits, write durable execution metadata to PostgreSQL, and store short-lived job progress/results in Redis.

### Service Boundaries

| Service | Responsibility | Scale Path |
|---------|----------------|------------|
| `frontend` | Vue build output served by reverse proxy | Static assets; CDN later if needed |
| `api` | FastAPI routes, auth, metadata, sync safe tools, task lifecycle | Add API replicas behind proxy |
| `worker` | Async/high-risk/expensive tool execution | Add more workers by queue |
| `postgres` | Durable relational state | Backups, managed Postgres later |
| `redis` | Queue, rate limits, cache, sessions | Managed Redis or Redis persistence later |
| `reverse-proxy` | TLS, routing, headers, compression | Caddy/Nginx reloads and cert renewal |

## Authentication And Authorization

### Access Model

YuKit uses a mixed access model:

- Anonymous users can run public, lightweight, safe tools.
- Authenticated users can run tools marked as `authenticated`, use personal favorites, save preferences, and view their own execution history.
- Future admin roles can manage tool availability and inspect aggregate usage, but this is out of scope for v1.

### Login

V1 implements GitHub OAuth:

1. User clicks "Sign in with GitHub".
2. API starts OAuth flow and stores state/nonce securely.
3. GitHub redirects back to `/api/auth/github/callback`.
4. API exchanges code for profile identity.
5. API creates or links a local user and `auth_identity`.
6. API issues an HTTP-only secure session cookie.

Email magic-link login is reserved at the interface and schema level:

- `auth_identities.provider` supports `github` and future `email`.
- Auth routes should be grouped so `/api/auth/email/start` and `/api/auth/email/verify` can be added later.
- User records are provider-agnostic.

### Session And CSRF

- Browser auth should use HTTP-only, Secure, SameSite=Lax cookies.
- OAuth state and session data should be backed by Redis or signed cookies.
- Mutating authenticated requests should use either SameSite cookie protection plus an `Origin`/`Referer` check, or an explicit CSRF token if cross-site embedding is ever allowed.
- CORS should default to the production domain and local dev origins only.

### Authorization

Each tool declares access metadata:

```python
class ToolAccessLevel(str, Enum):
    PUBLIC = "public"
    AUTHENTICATED = "authenticated"

class ToolExecutionMode(str, Enum):
    SYNC = "sync"
    ASYNC = "async"
```

Authorization rules:

- `public` tools can be used anonymously if their execution mode and risk level allow it.
- `authenticated` tools require a valid user session.
- Tool-specific limits can override defaults.
- Future roles can be added without changing the public API contract.

## Tool Plugin Design

Tools are backend plugins loaded from a controlled code directory. V1 does not support installing arbitrary user-submitted plugins from the UI.

### Tool Contract

```python
class BaseTool(Protocol):
    name: str
    label: str
    description: str
    tags: list[str]
    access_level: ToolAccessLevel
    execution_mode: ToolExecutionMode
    risk_level: Literal["low", "medium", "high"]
    input_schema: type[BaseModel]
    option_schema: type[BaseModel]
    output_schema: type[BaseModel]
    allow_history_input_storage: bool = False

    async def run(
        self,
        input_data: BaseModel,
        options: BaseModel,
        context: ToolExecutionContext,
    ) -> BaseModel:
        ...
```

The registry exposes metadata to the frontend and validates execution requests. The frontend should render forms from schema metadata and avoid hard-coded per-tool pages in v1.

### Tool Metadata

`GET /api/tools` returns only safe metadata:

```json
{
  "name": "json-format",
  "label": "JSON Format",
  "description": "Format and validate JSON input.",
  "tags": ["format", "developer"],
  "access_level": "public",
  "execution_mode": "sync",
  "risk_level": "low",
  "input_schema": {},
  "option_schema": {},
  "output_schema": {}
}
```

### Tool Categories

| Category | Access | Execution | Examples |
|----------|--------|-----------|----------|
| Safe lightweight tools | Public | Sync | JSON format, timestamp convert, Base64 encode/decode |
| Personalized tools | Authenticated | Sync or async | Saved presets, favorites, history-aware tools |
| Expensive tools | Authenticated | Async | Batch processing, large file parsing |
| High-risk tools | Authenticated | Async | URL fetch, archive parsing, regex stress tests |

### Adding A Tool

Adding a new internal tool should require:

1. Create a new module under `backend/app/tools/`.
2. Implement the `BaseTool` contract.
3. Add it to the registry.
4. Add unit tests for validation, success, expected failures, and limits.
5. Optionally add frontend schema-rendering tests if it uses new option field types.

## Queue Execution Design

### Execution Modes

`sync` tools:

- Must be low risk.
- Must complete quickly.
- Run in the API process after validation and rate-limit checks.
- Return a result immediately.

`async` tools:

- Required for high-risk, expensive, file-based, external-network, or long-running operations.
- API creates an execution record and enqueues a job in Redis.
- Worker executes the job and updates status.
- Client polls, or future SSE/WebSocket support can stream progress.

### Async Flow

```
POST /api/tools/{name}/runs
  -> validate request
  -> authenticate/authorize
  -> apply rate limit
  -> create execution row: queued
  -> enqueue Redis job
  -> return { execution_id, status: "queued" }

Worker
  -> reserve job
  -> mark execution: running
  -> run tool with timeout/context
  -> store sanitized result/error
  -> mark execution: succeeded/failed/timed_out/canceled

GET /api/executions/{id}
  -> authorize owner or anonymous token
  -> return status/result/error metadata
```

### Status Model

```text
queued -> running -> succeeded
queued -> running -> failed
queued -> running -> timed_out
queued -> canceled
queued -> running -> canceled
```

### Limits

Every tool can define:

- Max input size.
- Max file size.
- Timeout seconds.
- Anonymous and authenticated rate-limit buckets.
- Whether raw input can be stored.
- Whether network access is allowed.
- Whether execution must happen in a future sandbox.

The first implementation can enforce timeouts and size limits in Python. The contract should leave room for stronger OS/container-level limits later.

## API Design

| Method | Path | Access | Purpose |
|--------|------|--------|---------|
| GET | `/api/health` | Public | Process health |
| GET | `/api/ready` | Public/internal | DB/Redis readiness |
| GET | `/api/auth/me` | Optional | Current user/session |
| GET | `/api/auth/github/start` | Public | Start OAuth flow |
| GET | `/api/auth/github/callback` | Public | Complete OAuth flow |
| POST | `/api/auth/logout` | Authenticated | Clear session |
| GET | `/api/tools` | Public | List tool metadata |
| GET | `/api/tools/{name}` | Public | Get one tool metadata |
| POST | `/api/tools/{name}/runs` | Mixed | Run sync tool or enqueue async job |
| GET | `/api/executions/{id}` | Owner or token | Read execution status/result |
| GET | `/api/me/favorites` | Authenticated | List favorite tools |
| PUT | `/api/me/favorites/{tool}` | Authenticated | Add favorite |
| DELETE | `/api/me/favorites/{tool}` | Authenticated | Remove favorite |
| GET | `/api/me/executions` | Authenticated | User execution history |
| GET | `/api/me/preferences` | Authenticated | User preferences |
| PUT | `/api/me/preferences` | Authenticated | Update preferences |

### Response Envelope

Successful responses should use typed payloads. Errors should be consistent:

```json
{
  "error": {
    "code": "RATE_LIMITED",
    "message": "Too many requests. Please try again later.",
    "request_id": "req_..."
  }
}
```

Never return stack traces or raw internal exception messages to clients.

## Data Model

### Core Tables

```text
users
  id uuid pk
  display_name text
  avatar_url text null
  primary_email text null
  created_at timestamptz
  updated_at timestamptz
  last_login_at timestamptz null

auth_identities
  id uuid pk
  user_id uuid fk users.id
  provider text             # github, future email
  provider_subject text
  provider_username text null
  provider_email text null
  created_at timestamptz
  unique(provider, provider_subject)

user_preferences
  user_id uuid pk fk users.id
  theme text
  default_tool_options jsonb
  updated_at timestamptz

favorite_tools
  user_id uuid fk users.id
  tool_name text
  created_at timestamptz
  primary key(user_id, tool_name)

tool_executions
  id uuid pk
  user_id uuid null fk users.id
  anonymous_token_hash text null
  tool_name text
  access_level text
  execution_mode text
  status text
  input_hash text null
  input_snapshot jsonb null
  options_snapshot jsonb
  result_snapshot jsonb null
  error_code text null
  error_message text null
  duration_ms int null
  created_at timestamptz
  started_at timestamptz null
  finished_at timestamptz null
```

### Sensitive Input Policy

- Default: store only `input_hash`, not raw input.
- Tools can opt into `input_snapshot` only when the input is low sensitivity and useful for history.
- Execution history shown to users should clearly distinguish saved options/results from omitted inputs.
- Logs must not include raw tool input.

## Frontend Design

### Layout

- Header: app name, auth state, GitHub link, theme toggle.
- Sidebar: search, tags, favorites for logged-in users, recent tools.
- Workspace: tool header, input form, dynamic options form, run button, output/result area.
- History drawer/page: authenticated users can view previous executions.
- Mobile: sidebar collapses into a drawer; workspace remains the primary surface.

### Routing

```text
/                     -> default tool or tool list
/tool/:toolName       -> dynamic tool page
/history              -> authenticated execution history
/settings             -> authenticated preferences
/auth/callback        -> frontend callback landing if needed
```

Frontend should treat tool schemas as the contract. It should not need a new route/component for every tool unless a future tool needs a custom advanced UI.

## Deployment And Operations

### Docker Compose Services

```yaml
services:
  reverse-proxy:
    image: caddy:alpine # or nginx
    depends_on: [api]
    ports: ["80:80", "443:443"]

  api:
    image: ghcr.io/<user>/yukit:<version>
    command: fastapi run app/main.py --host 0.0.0.0 --port 8000
    depends_on: [postgres, redis]
    restart: unless-stopped

  worker:
    image: ghcr.io/<user>/yukit:<version>
    command: python -m app.queue.worker
    depends_on: [postgres, redis]
    restart: unless-stopped

  postgres:
    image: postgres:17-alpine
    volumes: ["postgres_data:/var/lib/postgresql/data"]
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    volumes: ["redis_data:/data"]
    restart: unless-stopped
```

V1 can use one application image for both `api` and `worker`, with different commands. Frontend assets can either be copied into the app image and served by the reverse proxy, or built into a separate static image. Prefer one app image for simpler VPS deployment at first.

### Release Strategy

- CI builds immutable image tags: `main-<sha>` and optionally `latest`.
- VPS should deploy a pinned tag, not only `latest`.
- Watchtower can be used for automatic updates, but production should prefer a controlled pull/restart script or Watchtower with labels, health checks, and rollback instructions.
- Database migrations should run as an explicit one-shot step before replacing the API/worker.

### Health Checks

- `/api/health`: process is alive.
- `/api/ready`: checks PostgreSQL and Redis connectivity.
- Worker health: heartbeat key in Redis or a small `worker_heartbeats` table.
- Compose health checks should restart unhealthy services.

### Backups

- PostgreSQL: daily `pg_dump` or volume snapshot; keep at least 7 daily and 4 weekly backups.
- Redis: not the source of truth for durable user data; persistence optional but useful for queued jobs.
- Secrets and `.env` files should not be stored in git.

### Observability

- Structured JSON logs with `request_id`, `user_id` when available, `tool_name`, `execution_id`, and duration.
- Basic metrics target: request count, error count, rate-limit count, job queue depth, job duration, worker failures.
- Error reporting can be added later through Sentry or OpenTelemetry.

### Security Baseline

- HTTPS only in production.
- Secure headers at the reverse proxy: HSTS, X-Content-Type-Options, Referrer-Policy, frame protections.
- Strict request body size limits at proxy and API layers.
- Per-tool input limits.
- Redis-backed rate limiting:
  - Anonymous: by IP and tool.
  - Authenticated: by user ID and tool.
- OAuth secrets, DB password, Redis password, and cookie signing secret managed through environment variables.
- Disable interactive API docs in production or protect them behind auth.

## Project Structure

```text
YuKit/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── dependencies.py
│   │   ├── api/
│   │   │   ├── auth.py
│   │   │   ├── tools.py
│   │   │   ├── executions.py
│   │   │   └── me.py
│   │   ├── auth/
│   │   │   ├── github.py
│   │   │   ├── sessions.py
│   │   │   └── permissions.py
│   │   ├── db/
│   │   │   ├── models.py
│   │   │   ├── session.py
│   │   │   └── migrations/
│   │   ├── queue/
│   │   │   ├── client.py
│   │   │   ├── jobs.py
│   │   │   └── worker.py
│   │   ├── tools/
│   │   │   ├── base.py
│   │   │   ├── registry.py
│   │   │   ├── json_format.py
│   │   │   ├── timestamp.py
│   │   │   ├── base64_codec.py
│   │   │   └── regex_test.py
│   │   └── schemas/
│   │       ├── common.py
│   │       ├── tools.py
│   │       └── executions.py
│   ├── tests/
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── views/
│   │   ├── router.ts
│   │   └── main.ts
│   └── package.json
├── docker/
│   ├── Caddyfile # or nginx.conf
│   └── scripts/
├── docker-compose.yml
├── Dockerfile
└── .github/
    └── workflows/
        └── ci.yml
```

## Testing Strategy

### Backend

- Unit tests for each tool:
  - valid input
  - invalid input
  - size/timeout/risk limits
  - sanitized error responses
- API tests using FastAPI TestClient or async client:
  - anonymous public tool run
  - authenticated-only tool rejection when anonymous
  - authenticated run succeeds
  - rate-limit behavior
  - execution status lifecycle
- Auth tests:
  - OAuth callback account creation/linking with mocked GitHub responses
  - session cookie behavior
  - logout clears session
- DB tests:
  - Alembic migrations apply cleanly
  - model constraints enforce identity uniqueness and favorite uniqueness
- Worker tests:
  - job enqueue/dequeue
  - success/failure/timed-out transitions
  - result sanitization

### Frontend

- Component tests:
  - schema-driven form rendering
  - auth state display
  - output panel states: idle, running, succeeded, failed
  - favorites and history UI states
- API client tests with mocked responses.
- E2E tests with Playwright:
  - tool list loads
  - anonymous public tool execution works
  - authenticated-only tool prompts login
  - mocked login unlocks favorites/history
  - async job moves from queued/running to result

### CI Gates

```text
backend:
  ruff check
  mypy or pyright
  pytest
  alembic migration check

frontend:
  pnpm lint
  vue-tsc --noEmit
  vitest
  playwright smoke tests

container:
  docker build
  optional vulnerability scan
  push immutable image tag
```

## Initial Tool List

| Tool | Access | Execution | Input | Options |
|------|--------|-----------|-------|---------|
| JSON Format | Public | Sync | JSON string | Indent size, sort keys |
| Timestamp | Public | Sync | Unix timestamp or ISO string | Output format |
| Base64 | Public | Sync | Text | Encode/decode, charset |
| Regex Test | Public initially; authenticated if advanced mode grows | Sync with strict timeout | Text + pattern | Flags |

Future tools that fetch URLs, parse files, process large inputs, or perform batch operations should be `authenticated` + `async` by default.

## Default Implementation Decisions

- Reverse proxy: use Caddy by default for automatic HTTPS and simpler VPS operation. Nginx remains an acceptable alternative if deployment familiarity matters more than automatic certificate management.
- Queue library: use ARQ by default because it is Redis-backed and asyncio-friendly. Avoid Celery in v1 unless task routing or retry requirements become substantially more complex.
- API docs: disable FastAPI `/docs` and `/redoc` in production by default. Enable them only in non-production environments or behind authenticated access.
- Anonymous async jobs: do not support them in v1. Anonymous users can run only public sync tools. If anonymous async jobs are needed later, use signed anonymous result tokens with strict rate limits and short retention.

## Recommended V1 Slice

1. Build API, frontend, PostgreSQL, Redis, and Compose foundation.
2. Implement GitHub OAuth sessions.
3. Implement tool registry and public sync tools.
4. Add rate limiting and consistent error envelopes.
5. Add execution records and authenticated history.
6. Add Redis queue and Worker for async tools.
7. Harden deployment with health checks, backups, and controlled release docs.
