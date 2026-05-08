# YuKit Platform V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build YuKit V1 as a public multi-user toolbox platform with FastAPI orchestration, Vue schema-driven UI, PostgreSQL persistence, Redis rate limiting/queueing, ARQ workers, GitHub OAuth, and Docker Compose deployment.

**Architecture:** FastAPI owns API orchestration, authentication, authorization, validation, tool metadata, rate-limit checks, sync tool execution, and execution lifecycle APIs. Long-running or high-risk tools run through Redis-backed ARQ workers. Vue renders tools from backend schema metadata and calls typed API endpoints.

**Tech Stack:** Vue 3, Vite, TypeScript, FastAPI, Pydantic, SQLAlchemy 2.x, Alembic, PostgreSQL, Redis, ARQ, Authlib, Docker Compose, Caddy, GitHub Actions, pytest, Vitest, Playwright.

---

## Source Spec

- Design spec: `docs/superpowers/specs/2026-05-08-yukit-toolbox-design.md`
- Current repository state: documentation-only repository with no backend, frontend, deployment, or CI files.
- Implementation boundary: this plan describes code and commands. Do not write production code until the user explicitly approves execution.

## Scope Check

The spec spans several subsystems: backend API, authentication, tool plugins, queue workers, frontend, deployment, and CI. This plan keeps them in one V1 sequence because each task adds a testable slice and the tasks depend on shared contracts. If implementation gets too large during execution, split after Task 6 into separate backend, frontend, and deployment plans.

## File Structure Map

Create this structure during implementation:

```text
YuKit/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── dependencies.py
│   │   ├── errors.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── executions.py
│   │   │   ├── health.py
│   │   │   ├── me.py
│   │   │   └── tools.py
│   │   ├── auth/
│   │   │   ├── __init__.py
│   │   │   ├── github.py
│   │   │   ├── permissions.py
│   │   │   └── sessions.py
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   └── session.py
│   │   ├── migrations/
│   │   │   ├── env.py
│   │   │   ├── script.py.mako
│   │   │   └── versions/
│   │   ├── queue/
│   │   │   ├── __init__.py
│   │   │   ├── client.py
│   │   │   ├── jobs.py
│   │   │   └── worker.py
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── common.py
│   │   │   ├── executions.py
│   │   │   └── tools.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── executions.py
│   │   │   └── rate_limits.py
│   │   └── tools/
│   │       ├── __init__.py
│   │       ├── base.py
│   │       ├── registry.py
│   │       ├── json_format.py
│   │       ├── timestamp.py
│   │       ├── base64_codec.py
│   │       └── regex_test.py
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── api/
│   │   ├── auth/
│   │   ├── db/
│   │   ├── queue/
│   │   └── tools/
│   ├── alembic.ini
│   └── pyproject.toml
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── src/
│       ├── main.ts
│       ├── router.ts
│       ├── api/
│       ├── components/
│       ├── stores/
│       └── views/
├── docker/
│   ├── Caddyfile
│   ├── entrypoint-api.sh
│   └── entrypoint-worker.sh
├── docs/
│   └── deployment.md
├── docker-compose.yml
├── Dockerfile
└── .github/
    └── workflows/
        └── ci.yml
```

## Shared Contracts To Preserve

Use these names consistently across tasks:

```python
class ToolAccessLevel(str, Enum):
    PUBLIC = "public"
    AUTHENTICATED = "authenticated"

class ToolExecutionMode(str, Enum):
    SYNC = "sync"
    ASYNC = "async"

class ExecutionStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    CANCELED = "canceled"
```

API routes:

```text
GET    /api/health
GET    /api/ready
GET    /api/auth/me
GET    /api/auth/github/start
GET    /api/auth/github/callback
POST   /api/auth/logout
GET    /api/tools
GET    /api/tools/{name}
POST   /api/tools/{name}/runs
GET    /api/executions/{id}
GET    /api/me/favorites
PUT    /api/me/favorites/{tool}
DELETE /api/me/favorites/{tool}
GET    /api/me/executions
GET    /api/me/preferences
PUT    /api/me/preferences
```

---

### Task 1: Repository Tooling And Backend Scaffold

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/config.py`
- Create: `backend/app/errors.py`
- Create: `backend/tests/conftest.py`

- [ ] **Step 1: Create backend package metadata and dependencies**

Create `backend/pyproject.toml` with this content:

```toml
[project]
name = "yukit-backend"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = [
  "arq>=0.26",
  "asyncpg>=0.30",
  "authlib>=1.3",
  "fastapi[standard]>=0.115",
  "httpx>=0.27",
  "itsdangerous>=2.2",
  "orjson>=3.10",
  "pydantic-settings>=2.7",
  "redis>=5.2",
  "sqlalchemy[asyncio]>=2.0",
  "structlog>=24.4",
  "alembic>=1.14"
]

[project.optional-dependencies]
dev = [
  "pytest>=8.3",
  "pytest-asyncio>=0.25",
  "pytest-cov>=6.0",
  "ruff>=0.8",
  "mypy>=1.14"
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
pythonpath = ["."]

[tool.ruff]
line-length = 100
target-version = "py313"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "ASYNC"]

[tool.mypy]
python_version = "3.13"
strict = true
plugins = ["pydantic.mypy"]
```

- [ ] **Step 2: Add app settings**

Create `backend/app/config.py`:

```python
from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="YUKIT_", extra="ignore")

    environment: Literal["local", "test", "production"] = "local"
    app_name: str = "YuKit"
    public_base_url: AnyHttpUrl = "http://localhost:5173"
    api_base_url: AnyHttpUrl = "http://localhost:8000"
    database_url: str = "postgresql+asyncpg://yukit:yukit@localhost:5432/yukit"
    redis_url: str = "redis://localhost:6379/0"
    session_secret: str = Field(default="local-dev-session-secret-change-me", min_length=32)
    github_client_id: str = ""
    github_client_secret: str = ""
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:8000"]
    docs_enabled: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 3: Add error envelope primitives**

Create `backend/app/errors.py`:

```python
from dataclasses import dataclass

from fastapi import Request
from fastapi.responses import ORJSONResponse


@dataclass(frozen=True)
class ApiError(Exception):
    code: str
    message: str
    status_code: int = 400


def error_response(request: Request, error: ApiError) -> ORJSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    return ORJSONResponse(
        status_code=error.status_code,
        content={"error": {"code": error.code, "message": error.message, "request_id": request_id}},
    )
```

- [ ] **Step 4: Add minimal FastAPI app factory**

Create `backend/app/main.py`:

```python
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.errors import ApiError, error_response


def create_app() -> FastAPI:
    settings = get_settings()
    docs_url = "/docs" if settings.docs_enabled and settings.environment != "production" else None
    redoc_url = "/redoc" if settings.docs_enabled and settings.environment != "production" else None
    app = FastAPI(title=settings.app_name, docs_url=docs_url, redoc_url=redoc_url)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Content-Type", "X-CSRF-Token"],
    )

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        request.state.request_id = request.headers.get("X-Request-ID", f"req_{uuid4().hex}")
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    @app.exception_handler(ApiError)
    async def api_error_handler(request: Request, exc: ApiError):
        return error_response(request, exc)

    return app


app = create_app()
```

- [ ] **Step 5: Add backend test fixture**

Create `backend/tests/conftest.py`:

```python
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as test_client:
        yield test_client
```

- [ ] **Step 6: Install and verify scaffold**

Run from `backend/`:

```powershell
python -m pip install -e ".[dev]"
python -m pytest -q
python -m ruff check .
```

Expected:

```text
no tests ran
All checks passed!
```

- [ ] **Step 7: Commit**

```bash
git add backend/pyproject.toml backend/app backend/tests/conftest.py
git commit -m "chore: scaffold backend application"
```

---

### Task 2: Health, Readiness, And Shared Dependencies

**Files:**
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/health.py`
- Create: `backend/app/db/__init__.py`
- Create: `backend/app/db/session.py`
- Create: `backend/app/dependencies.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/api/test_health.py`

- [ ] **Step 1: Write failing API health tests**

Create `backend/tests/api/test_health.py`:

```python
import pytest


@pytest.mark.asyncio
async def test_health_returns_ok(client):
    response = await client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_ready_returns_dependency_status(client):
    response = await client.get("/api/ready")

    assert response.status_code == 200
    assert response.json()["status"] in {"ok", "degraded"}
    assert "postgres" in response.json()["dependencies"]
    assert "redis" in response.json()["dependencies"]
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
cd backend
python -m pytest tests/api/test_health.py -q
```

Expected: FAIL with `404 Not Found`.

- [ ] **Step 3: Add database and dependency helpers**

Create `backend/app/db/session.py`:

```python
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings

settings = get_settings()
engine = create_async_engine(settings.database_url, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session
```

Create `backend/app/dependencies.py`:

```python
from collections.abc import AsyncIterator

from redis.asyncio import Redis

from app.config import get_settings
from app.db.session import get_db_session


async def get_redis() -> AsyncIterator[Redis]:
    redis = Redis.from_url(get_settings().redis_url, decode_responses=True)
    try:
        yield redis
    finally:
        await redis.aclose()


__all__ = ["get_db_session", "get_redis"]
```

- [ ] **Step 4: Add health router**

Create `backend/app/api/health.py`:

```python
from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db_session, get_redis

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
async def ready(
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
) -> dict[str, object]:
    dependencies: dict[str, str] = {}

    try:
        await db.execute(text("select 1"))
        dependencies["postgres"] = "ok"
    except Exception:
        dependencies["postgres"] = "unavailable"

    try:
        await redis.ping()
        dependencies["redis"] = "ok"
    except Exception:
        dependencies["redis"] = "unavailable"

    status = "ok" if all(value == "ok" for value in dependencies.values()) else "degraded"
    return {"status": status, "dependencies": dependencies}
```

Modify `backend/app/main.py`:

```python
from app.api.health import router as health_router

# inside create_app(), before return app:
app.include_router(health_router)
```

- [ ] **Step 5: Run tests**

Run:

```powershell
cd backend
python -m pytest tests/api/test_health.py -q
```

Expected: PASS. If local PostgreSQL or Redis is unavailable, `/api/ready` may return `degraded`, which is accepted.

- [ ] **Step 6: Commit**

```bash
git add backend/app backend/tests/api/test_health.py
git commit -m "feat: add health and readiness endpoints"
```

---

### Task 3: Database Models And Migrations

**Files:**
- Create: `backend/app/db/models.py`
- Create: `backend/alembic.ini`
- Create: `backend/app/migrations/env.py`
- Create: `backend/app/migrations/script.py.mako`
- Create: `backend/app/migrations/versions/0001_initial_schema.py`
- Test: `backend/tests/db/test_models.py`

- [ ] **Step 1: Write model constraint tests**

Create `backend/tests/db/test_models.py`:

```python
from app.db.models import AuthIdentity, FavoriteTool, ToolExecution, User


def test_model_table_names_are_stable():
    assert User.__tablename__ == "users"
    assert AuthIdentity.__tablename__ == "auth_identities"
    assert FavoriteTool.__tablename__ == "favorite_tools"
    assert ToolExecution.__tablename__ == "tool_executions"


def test_auth_identity_has_provider_subject_unique_constraint():
    constraint_names = {constraint.name for constraint in AuthIdentity.__table__.constraints}
    assert "uq_auth_identities_provider_subject" in constraint_names


def test_favorite_tools_uses_composite_primary_key():
    primary_keys = {column.name for column in FavoriteTool.__table__.primary_key.columns}
    assert primary_keys == {"user_id", "tool_name"}
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
cd backend
python -m pytest tests/db/test_models.py -q
```

Expected: FAIL with `ModuleNotFoundError` for `app.db.models`.

- [ ] **Step 3: Add SQLAlchemy models**

Create `backend/app/db/models.py` with these model names and columns:

```python
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    display_name: Mapped[str] = mapped_column(String(200))
    avatar_url: Mapped[str | None] = mapped_column(Text)
    primary_email: Mapped[str | None] = mapped_column(String(320))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    identities: Mapped[list["AuthIdentity"]] = relationship(back_populates="user")


class AuthIdentity(Base):
    __tablename__ = "auth_identities"
    __table_args__ = (
        UniqueConstraint("provider", "provider_subject", name="uq_auth_identities_provider_subject"),
    )

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    provider: Mapped[str] = mapped_column(String(50))
    provider_subject: Mapped[str] = mapped_column(String(200))
    provider_username: Mapped[str | None] = mapped_column(String(200))
    provider_email: Mapped[str | None] = mapped_column(String(320))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    user: Mapped[User] = relationship(back_populates="identities")


class UserPreference(Base):
    __tablename__ = "user_preferences"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    theme: Mapped[str] = mapped_column(String(20), default="system")
    default_tool_options: Mapped[dict] = mapped_column(JSONB, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class FavoriteTool(Base):
    __tablename__ = "favorite_tools"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    tool_name: Mapped[str] = mapped_column(String(120), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ToolExecution(Base):
    __tablename__ = "tool_executions"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    anonymous_token_hash: Mapped[str | None] = mapped_column(String(128))
    tool_name: Mapped[str] = mapped_column(String(120))
    access_level: Mapped[str] = mapped_column(String(40))
    execution_mode: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(40))
    input_hash: Mapped[str | None] = mapped_column(String(128))
    input_snapshot: Mapped[dict | None] = mapped_column(JSONB)
    options_snapshot: Mapped[dict] = mapped_column(JSONB, default=dict)
    result_snapshot: Mapped[dict | None] = mapped_column(JSONB)
    error_code: Mapped[str | None] = mapped_column(String(80))
    error_message: Mapped[str | None] = mapped_column(Text)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
```

- [ ] **Step 4: Add Alembic configuration**

Create `backend/alembic.ini`:

```ini
[alembic]
script_location = app/migrations
prepend_sys_path = .
sqlalchemy.url = postgresql+asyncpg://yukit:yukit@localhost:5432/yukit

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
```

Create `backend/app/migrations/env.py`:

```python
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import get_settings
from app.db.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", get_settings().database_url.replace("+asyncpg", ""))
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 5: Generate and verify initial migration**

Run:

```powershell
cd backend
python -m alembic revision --autogenerate -m "initial schema"
```

Rename the generated file under `backend/app/migrations/versions/` to `0001_initial_schema.py`.

Open the generated migration and verify it contains these fragments:

```python
op.create_table("users",
op.create_table("auth_identities",
op.create_table("user_preferences",
op.create_table("favorite_tools",
op.create_table("tool_executions",
sa.UniqueConstraint("provider", "provider_subject", name="uq_auth_identities_provider_subject"),
sa.PrimaryKeyConstraint("user_id", "tool_name")
```

Run:

```powershell
cd backend
python -m alembic upgrade head
```

Expected: migration applies without errors against the local PostgreSQL database.

- [ ] **Step 6: Run model tests**

Run:

```powershell
cd backend
python -m pytest tests/db/test_models.py -q
```

Expected: PASS.

- [ ] **Step 7: Run lint**

Run:

```powershell
cd backend
python -m ruff check .
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add backend/app/db backend/app/migrations backend/alembic.ini backend/tests/db/test_models.py
git commit -m "feat: add database schema"
```

---

### Task 4: Tool Contract, Registry, And Public Sync Tools

**Files:**
- Create: `backend/app/tools/base.py`
- Create: `backend/app/tools/registry.py`
- Create: `backend/app/tools/json_format.py`
- Create: `backend/app/tools/timestamp.py`
- Create: `backend/app/tools/base64_codec.py`
- Create: `backend/app/tools/regex_test.py`
- Create: `backend/app/schemas/tools.py`
- Create: `backend/app/api/tools.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/tools/test_registry.py`
- Test: `backend/tests/tools/test_public_tools.py`
- Test: `backend/tests/api/test_tools_metadata.py`

- [ ] **Step 1: Write failing registry tests**

Create `backend/tests/tools/test_registry.py`:

```python
from app.tools.registry import tool_registry


def test_initial_tools_are_registered():
    assert set(tool_registry.names()) == {"json-format", "timestamp", "base64", "regex-test"}


def test_registry_returns_safe_metadata():
    metadata = tool_registry.get("json-format").metadata()

    assert metadata["name"] == "json-format"
    assert metadata["access_level"] == "public"
    assert metadata["execution_mode"] == "sync"
    assert "input_schema" in metadata
    assert "option_schema" in metadata
    assert "output_schema" in metadata
```

- [ ] **Step 2: Add tool base contract**

Create `backend/app/tools/base.py`:

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Literal

from pydantic import BaseModel


class ToolAccessLevel(str, Enum):
    PUBLIC = "public"
    AUTHENTICATED = "authenticated"


class ToolExecutionMode(str, Enum):
    SYNC = "sync"
    ASYNC = "async"


@dataclass(frozen=True)
class ToolExecutionContext:
    user_id: str | None
    request_id: str


class ToolLimit(BaseModel):
    max_input_bytes: int = 64_000
    timeout_seconds: float = 2.0
    anonymous_rate_limit: str = "30/minute"
    authenticated_rate_limit: str = "120/minute"


class BaseTool(ABC):
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
    limits: ToolLimit
    allow_history_input_storage: bool

    def metadata(self) -> dict[str, object]:
        return {
            "name": self.name,
            "label": self.label,
            "description": self.description,
            "tags": self.tags,
            "access_level": self.access_level.value,
            "execution_mode": self.execution_mode.value,
            "risk_level": self.risk_level,
            "input_schema": self.input_schema.model_json_schema(),
            "option_schema": self.option_schema.model_json_schema(),
            "output_schema": self.output_schema.model_json_schema(),
        }

    @abstractmethod
    async def run(
        self,
        input_data: BaseModel,
        options: BaseModel,
        context: ToolExecutionContext,
    ) -> BaseModel:
        raise NotImplementedError
```

- [ ] **Step 3: Add registry**

Create `backend/app/tools/registry.py`:

```python
from app.errors import ApiError
from app.tools.base import BaseTool
from app.tools.base64_codec import Base64Tool
from app.tools.json_format import JsonFormatTool
from app.tools.regex_test import RegexTestTool
from app.tools.timestamp import TimestampTool


class ToolRegistry:
    def __init__(self, tools: list[BaseTool]) -> None:
        self._tools = {tool.name: tool for tool in tools}

    def names(self) -> list[str]:
        return sorted(self._tools)

    def all(self) -> list[BaseTool]:
        return [self._tools[name] for name in self.names()]

    def get(self, name: str) -> BaseTool:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise ApiError("TOOL_NOT_FOUND", "Tool not found.", 404) from exc


tool_registry = ToolRegistry([JsonFormatTool(), TimestampTool(), Base64Tool(), RegexTestTool()])
```

- [ ] **Step 4: Add public tool implementations**

Implement each tool with Pydantic input/options/output models:

```python
class TextInput(BaseModel):
    text: str = Field(max_length=64_000)

class TextOutput(BaseModel):
    text: str
```

Behavior:

- `json-format`: parse JSON, indent 2 or 4, optional sort keys, return validation error `INVALID_JSON`.
- `timestamp`: accept Unix seconds or ISO datetime, return ISO, Unix, or RFC 2822.
- `base64`: encode/decode UTF-8 by default, return `INVALID_BASE64` for invalid decode input.
- `regex-test`: compile pattern with allowed flags `i` and `m`, apply strict input size, return match ranges and groups. Avoid catastrophic behavior by enforcing small input and a low timeout at API level.

- [ ] **Step 5: Add metadata schemas and API routes**

Create `backend/app/schemas/tools.py`:

```python
from pydantic import BaseModel


class ToolRunRequest(BaseModel):
    input: dict
    options: dict = {}


class ToolRunResponse(BaseModel):
    mode: str
    status: str
    result: dict | None = None
    execution_id: str | None = None


class ToolMetadata(BaseModel):
    name: str
    label: str
    description: str
    tags: list[str]
    access_level: str
    execution_mode: str
    risk_level: str
    input_schema: dict
    option_schema: dict
    output_schema: dict
```

Create `backend/app/api/tools.py` with:

```python
from fastapi import APIRouter

from app.tools.registry import tool_registry

router = APIRouter(prefix="/api/tools", tags=["tools"])


@router.get("")
async def list_tools() -> list[dict]:
    return [tool.metadata() for tool in tool_registry.all()]


@router.get("/{name}")
async def get_tool(name: str) -> dict:
    return tool_registry.get(name).metadata()
```

Add a `metadata()` method to concrete tools or a small mixin so each tool returns JSON schemas via `model_json_schema()`.

Modify `backend/app/main.py`:

```python
from app.api.tools import router as tools_router

app.include_router(tools_router)
```

- [ ] **Step 6: Run tests**

Run:

```powershell
cd backend
python -m pytest tests/tools tests/api/test_tools_metadata.py -q
python -m ruff check .
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/tools backend/app/schemas backend/app/api/tools.py backend/app/main.py backend/tests/tools backend/tests/api/test_tools_metadata.py
git commit -m "feat: add tool registry and public tool metadata"
```

---

### Task 5: Sessions, GitHub OAuth, And Current User API

**Files:**
- Create: `backend/app/auth/sessions.py`
- Create: `backend/app/auth/github.py`
- Create: `backend/app/auth/permissions.py`
- Create: `backend/app/api/auth.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/auth/test_sessions.py`
- Test: `backend/tests/api/test_auth.py`

- [ ] **Step 1: Write failing session tests**

Create `backend/tests/auth/test_sessions.py`:

```python
from app.auth.sessions import SessionData, SessionManager


def test_session_round_trip():
    manager = SessionManager(secret="x" * 32)
    cookie = manager.create_session_cookie(SessionData(user_id="user_123"))

    data = manager.read_session_cookie(cookie)

    assert data.user_id == "user_123"


def test_invalid_session_returns_none():
    manager = SessionManager(secret="x" * 32)

    assert manager.read_session_cookie("not-a-valid-cookie") is None
```

- [ ] **Step 2: Add signed session manager**

Create `backend/app/auth/sessions.py`:

```python
from pydantic import BaseModel
from itsdangerous import BadSignature, URLSafeTimedSerializer


class SessionData(BaseModel):
    user_id: str


class SessionManager:
    def __init__(self, secret: str) -> None:
        self._serializer = URLSafeTimedSerializer(secret_key=secret, salt="yukit-session")

    def create_session_cookie(self, data: SessionData) -> str:
        return self._serializer.dumps(data.model_dump())

    def read_session_cookie(self, value: str, max_age_seconds: int = 60 * 60 * 24 * 30) -> SessionData | None:
        try:
            payload = self._serializer.loads(value, max_age=max_age_seconds)
        except BadSignature:
            return None
        return SessionData.model_validate(payload)
```

- [ ] **Step 3: Add auth permissions dependency**

Create `backend/app/auth/permissions.py`:

```python
from dataclasses import dataclass

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.session import get_db_session
from app.errors import ApiError
from app.auth.sessions import SessionManager


@dataclass(frozen=True)
class CurrentUser:
    id: str
    display_name: str


async def optional_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> CurrentUser | None:
    cookie = request.cookies.get("yukit_session")
    if not cookie:
        return None
    data = SessionManager(get_settings().session_secret).read_session_cookie(cookie)
    if data is None:
        return None
    user = await db.get(User, data.user_id)  # import User when adding the file
    if user is None:
        return None
    return CurrentUser(id=str(user.id), display_name=user.display_name)


async def require_current_user(
    user: CurrentUser | None = Depends(optional_current_user),
) -> CurrentUser:
    if user is None:
        raise ApiError("AUTH_REQUIRED", "Sign in required.", 401)
    return user
```

Import `User` from `app.db.models` in the final file.

- [ ] **Step 4: Add GitHub OAuth service**

Create `backend/app/auth/github.py` with an `OAuth` client from Authlib:

```python
from datetime import UTC, datetime

from authlib.integrations.starlette_client import OAuth
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import AuthIdentity, User


def create_oauth() -> OAuth:
    settings = get_settings()
    oauth = OAuth()
    oauth.register(
        name="github",
        client_id=settings.github_client_id,
        client_secret=settings.github_client_secret,
        access_token_url="https://github.com/login/oauth/access_token",
        authorize_url="https://github.com/login/oauth/authorize",
        api_base_url="https://api.github.com/",
        client_kwargs={"scope": "read:user user:email"},
    )
    return oauth


class GitHubProfile(BaseModel):
    id: int
    login: str
    name: str | None = None
    avatar_url: str | None = None
    email: str | None = None


async def upsert_github_user(db: AsyncSession, profile: GitHubProfile) -> User:
    now = datetime.now(UTC)
    subject = str(profile.id)
    result = await db.execute(
        select(AuthIdentity)
        .where(AuthIdentity.provider == "github")
        .where(AuthIdentity.provider_subject == subject)
    )
    identity = result.scalar_one_or_none()

    if identity is not None:
        user = await db.get(User, identity.user_id)
        if user is None:
            raise RuntimeError("GitHub identity points to a missing user")
        user.display_name = profile.name or profile.login
        user.avatar_url = profile.avatar_url
        user.primary_email = profile.email
        user.last_login_at = now
        identity.provider_username = profile.login
        identity.provider_email = profile.email
        await db.commit()
        await db.refresh(user)
        return user

    user = User(
        display_name=profile.name or profile.login,
        avatar_url=profile.avatar_url,
        primary_email=profile.email,
        last_login_at=now,
    )
    db.add(user)
    await db.flush()
    db.add(
        AuthIdentity(
            user_id=user.id,
            provider="github",
            provider_subject=subject,
            provider_username=profile.login,
            provider_email=profile.email,
        )
    )
    await db.commit()
    await db.refresh(user)
    return user
```

- [ ] **Step 5: Add auth API routes**

Create `backend/app/api/auth.py`:

```python
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.permissions import optional_current_user
from app.auth.sessions import SessionData, SessionManager
from app.config import get_settings
from app.db.session import get_db_session
from app.auth.github import GitHubProfile, create_oauth, upsert_github_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/me")
async def me(user=Depends(optional_current_user)) -> dict[str, object]:
    if user is None:
        return {"authenticated": False, "user": None}
    return {"authenticated": True, "user": {"id": user.id, "display_name": user.display_name}}


@router.get("/github/start")
async def github_start(request: Request):
    oauth = create_oauth()
    redirect_uri = str(request.url_for("github_callback"))
    return await oauth.github.authorize_redirect(request, redirect_uri)


@router.get("/github/callback", name="github_callback")
async def github_callback(request: Request, db: AsyncSession = Depends(get_db_session)):
    settings = get_settings()
    oauth = create_oauth()
    token = await oauth.github.authorize_access_token(request)
    profile_response = await oauth.github.get("user", token=token)
    profile_response.raise_for_status()
    profile = GitHubProfile.model_validate(profile_response.json())
    user = await upsert_github_user(db, profile)

    session_value = SessionManager(settings.session_secret).create_session_cookie(
        SessionData(user_id=str(user.id))
    )
    response = RedirectResponse(str(settings.public_base_url))
    response.set_cookie(
        "yukit_session",
        session_value,
        httponly=True,
        secure=settings.environment == "production",
        samesite="lax",
        max_age=60 * 60 * 24 * 30,
        path="/",
    )
    return response


@router.post("/logout")
async def logout(response: Response) -> dict[str, bool]:
    response.delete_cookie("yukit_session", path="/")
    return {"ok": True}
```

Unit tests should mock Authlib/GitHub calls rather than calling GitHub.

- [ ] **Step 6: Add tests for current user API**

Create `backend/tests/api/test_auth.py`:

```python
import pytest


@pytest.mark.asyncio
async def test_me_returns_anonymous_when_not_signed_in(client):
    response = await client.get("/api/auth/me")

    assert response.status_code == 200
    assert response.json() == {"authenticated": False, "user": None}


@pytest.mark.asyncio
async def test_logout_clears_session_cookie(client):
    response = await client.post("/api/auth/logout")

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert "yukit_session" in response.headers.get("set-cookie", "")
```

- [ ] **Step 7: Run auth tests**

Run:

```powershell
cd backend
python -m pytest tests/auth tests/api/test_auth.py -q
python -m ruff check .
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add backend/app/auth backend/app/api/auth.py backend/app/main.py backend/tests/auth backend/tests/api/test_auth.py
git commit -m "feat: add session auth foundation"
```

---

### Task 6: Tool Runs, Execution Records, And Rate Limiting

**Files:**
- Create: `backend/app/services/rate_limits.py`
- Create: `backend/app/services/executions.py`
- Create: `backend/app/schemas/executions.py`
- Create: `backend/app/api/executions.py`
- Modify: `backend/app/api/tools.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/api/test_tool_runs.py`
- Test: `backend/tests/services/test_rate_limits.py`

- [ ] **Step 1: Write failing sync run API tests**

Create `backend/tests/api/test_tool_runs.py`:

```python
import pytest


@pytest.mark.asyncio
async def test_run_public_sync_tool_returns_result(client):
    response = await client.post(
        "/api/tools/json-format/runs",
        json={"input": {"text": "{\"b\":1,\"a\":2}"}, "options": {"indent": 2, "sort_keys": True}},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "sync"
    assert body["status"] == "succeeded"
    assert body["result"]["text"] == '{\n  "a": 2,\n  "b": 1\n}'


@pytest.mark.asyncio
async def test_invalid_tool_input_returns_error_envelope(client):
    response = await client.post(
        "/api/tools/json-format/runs",
        json={"input": {"text": "{"}, "options": {"indent": 2, "sort_keys": False}},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_JSON"
```

- [ ] **Step 2: Add rate limiter service**

Create `backend/app/services/rate_limits.py`:

```python
from dataclasses import dataclass

from redis.asyncio import Redis

from app.errors import ApiError


@dataclass(frozen=True)
class RateLimit:
    limit: int
    window_seconds: int


def parse_rate_limit(value: str) -> RateLimit:
    amount, unit = value.split("/")
    seconds = {"second": 1, "minute": 60, "hour": 3600}[unit]
    return RateLimit(limit=int(amount), window_seconds=seconds)


async def check_rate_limit(redis: Redis, key: str, rate_limit: RateLimit) -> None:
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, rate_limit.window_seconds)
    if count > rate_limit.limit:
        raise ApiError("RATE_LIMITED", "Too many requests. Please try again later.", 429)
```

- [ ] **Step 3: Add execution service**

Create `backend/app/services/executions.py`:

```python
import hashlib
from datetime import UTC, datetime
from uuid import UUID

import orjson
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ToolExecution
from app.errors import ApiError


def hash_input(payload: dict) -> str:
    raw = orjson.dumps(payload, option=orjson.OPT_SORT_KEYS)
    return hashlib.sha256(raw).hexdigest()


async def create_sync_execution(
    db: AsyncSession,
    *,
    user_id: str | None,
    tool_name: str,
    access_level: str,
    execution_mode: str,
    input_payload: dict,
    options_payload: dict,
    result_payload: dict | None,
    error_code: str | None,
    error_message: str | None,
    duration_ms: int,
) -> ToolExecution:
    now = datetime.now(UTC)
    execution = ToolExecution(
        user_id=UUID(user_id) if user_id else None,
        tool_name=tool_name,
        access_level=access_level,
        execution_mode=execution_mode,
        status="succeeded" if error_code is None else "failed",
        input_hash=hash_input(input_payload),
        input_snapshot=None,
        options_snapshot=options_payload,
        result_snapshot=result_payload,
        error_code=error_code,
        error_message=error_message,
        duration_ms=duration_ms,
        created_at=now,
        started_at=now,
        finished_at=now,
    )
    db.add(execution)
    await db.commit()
    await db.refresh(execution)
    return execution


async def create_queued_execution(
    db: AsyncSession,
    *,
    user_id: str,
    tool_name: str,
    access_level: str,
    execution_mode: str,
    input_payload: dict,
    options_payload: dict,
) -> ToolExecution:
    execution = ToolExecution(
        user_id=UUID(user_id),
        tool_name=tool_name,
        access_level=access_level,
        execution_mode=execution_mode,
        status="queued",
        input_hash=hash_input(input_payload),
        input_snapshot=None,
        options_snapshot=options_payload,
    )
    db.add(execution)
    await db.commit()
    await db.refresh(execution)
    return execution


async def get_execution_or_404(db: AsyncSession, execution_id: UUID) -> ToolExecution:
    execution = await db.get(ToolExecution, execution_id)
    if execution is None:
        raise ApiError("EXECUTION_NOT_FOUND", "Execution not found.", 404)
    return execution


async def list_user_executions(db: AsyncSession, user_id: str) -> list[ToolExecution]:
    result = await db.execute(
        select(ToolExecution)
        .where(ToolExecution.user_id == UUID(user_id))
        .order_by(ToolExecution.created_at.desc())
        .limit(50)
    )
    return list(result.scalars().all())


async def mark_execution_running(db: AsyncSession, execution_id: str) -> ToolExecution:
    execution = await get_execution_or_404(db, UUID(execution_id))
    execution.status = "running"
    execution.started_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(execution)
    return execution


async def mark_execution_succeeded(
    db: AsyncSession,
    execution: ToolExecution,
    result_payload: dict,
) -> ToolExecution:
    now = datetime.now(UTC)
    execution.status = "succeeded"
    execution.result_snapshot = result_payload
    execution.error_code = None
    execution.error_message = None
    execution.finished_at = now
    if execution.started_at:
        execution.duration_ms = int((now - execution.started_at).total_seconds() * 1000)
    await db.commit()
    await db.refresh(execution)
    return execution


async def mark_execution_failed(
    db: AsyncSession,
    execution: ToolExecution,
    error: Exception,
) -> ToolExecution:
    now = datetime.now(UTC)
    execution.status = "failed"
    execution.error_code = error.__class__.__name__
    execution.error_message = "Tool execution failed."
    execution.finished_at = now
    if execution.started_at:
        execution.duration_ms = int((now - execution.started_at).total_seconds() * 1000)
    await db.commit()
    await db.refresh(execution)
    return execution


async def mark_execution_timed_out(db: AsyncSession, execution: ToolExecution) -> ToolExecution:
    now = datetime.now(UTC)
    execution.status = "timed_out"
    execution.error_code = "TIMED_OUT"
    execution.error_message = "Tool execution timed out."
    execution.finished_at = now
    if execution.started_at:
        execution.duration_ms = int((now - execution.started_at).total_seconds() * 1000)
    await db.commit()
    await db.refresh(execution)
    return execution


def serialize_execution(execution: ToolExecution) -> dict[str, object]:
    return {
        "id": str(execution.id),
        "tool_name": execution.tool_name,
        "status": execution.status,
        "execution_mode": execution.execution_mode,
        "result": execution.result_snapshot,
        "error": (
            {"code": execution.error_code, "message": execution.error_message}
            if execution.error_code
            else None
        ),
        "duration_ms": execution.duration_ms,
        "created_at": execution.created_at.isoformat(),
        "finished_at": execution.finished_at.isoformat() if execution.finished_at else None,
    }
```

- [ ] **Step 4: Implement POST `/api/tools/{name}/runs` for sync tools**

Modify `backend/app/api/tools.py` to:

1. Load the tool by name.
2. Resolve optional current user.
3. Reject authenticated-only tools when user is absent.
4. Validate input and options through the tool's Pydantic models.
5. Check Redis rate limit using IP for anonymous users or user ID for signed-in users.
6. Run sync tools in the API process.
7. Store execution metadata.
8. Return `ToolRunResponse`.

Core shape:

```python
@router.post("/{name}/runs")
async def run_tool(
    name: str,
    request: Request,
    payload: ToolRunRequest,
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
    user: CurrentUser | None = Depends(optional_current_user),
) -> ToolRunResponse:
    tool = tool_registry.get(name)
    ensure_tool_access(tool, user)
    input_data = tool.input_schema.model_validate(payload.input)
    options = tool.option_schema.model_validate(payload.options)
    await enforce_tool_rate_limit(redis, request, tool, user)

    if tool.execution_mode == ToolExecutionMode.ASYNC:
        return await enqueue_async_tool_run(db, redis, tool, input_data, options, user, request)

    result = await tool.run(input_data, options, ToolExecutionContext(user_id=user.id if user else None, request_id=request.state.request_id))
    return ToolRunResponse(mode="sync", status="succeeded", result=result.model_dump())
```

- [ ] **Step 5: Add execution lookup route**

Create `backend/app/api/executions.py`:

```python
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session

router = APIRouter(prefix="/api/executions", tags=["executions"])


@router.get("/{execution_id}")
async def get_execution(execution_id: UUID, db: AsyncSession = Depends(get_db_session)) -> dict:
    execution = await db.get(ToolExecution, execution_id)
    if execution is None:
        raise ApiError("EXECUTION_NOT_FOUND", "Execution not found.", 404)
    return serialize_execution(execution)
```

Import `ToolExecution`, `ApiError`, and `serialize_execution` in the final file.

- [ ] **Step 6: Run tests**

Run:

```powershell
cd backend
python -m pytest tests/api/test_tool_runs.py tests/services/test_rate_limits.py -q
python -m ruff check .
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/services backend/app/schemas/executions.py backend/app/api backend/tests/api/test_tool_runs.py backend/tests/services/test_rate_limits.py
git commit -m "feat: add tool run lifecycle"
```

---

### Task 7: ARQ Queue And Worker Execution

**Files:**
- Create: `backend/app/queue/client.py`
- Create: `backend/app/queue/jobs.py`
- Create: `backend/app/queue/worker.py`
- Modify: `backend/app/api/tools.py`
- Modify: `backend/app/services/executions.py`
- Test: `backend/tests/queue/test_jobs.py`
- Test: `backend/tests/api/test_async_tool_runs.py`

- [ ] **Step 1: Write failing queue tests**

Create `backend/tests/queue/test_jobs.py`:

```python
from app.queue.jobs import ToolRunJob


def test_tool_run_job_payload_is_stable():
    job = ToolRunJob(
        execution_id="exec_1",
        tool_name="json-format",
        user_id="user_1",
        input={"text": "{}"},
        options={"indent": 2},
        request_id="req_1",
    )

    assert job.model_dump()["tool_name"] == "json-format"
    assert job.model_dump()["request_id"] == "req_1"
```

- [ ] **Step 2: Add queue payload model**

Create `backend/app/queue/jobs.py`:

```python
from pydantic import BaseModel


class ToolRunJob(BaseModel):
    execution_id: str
    tool_name: str
    user_id: str | None
    input: dict
    options: dict
    request_id: str
```

- [ ] **Step 3: Add ARQ client helper**

Create `backend/app/queue/client.py`:

```python
from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from app.config import get_settings


def redis_settings_from_url(url: str) -> RedisSettings:
    return RedisSettings.from_dsn(url)


async def get_arq_pool() -> ArqRedis:
    return await create_pool(redis_settings_from_url(get_settings().redis_url))
```

- [ ] **Step 4: Add worker job function**

Create `backend/app/queue/worker.py`:

```python
import asyncio
from datetime import UTC, datetime

from app.config import get_settings
from app.db.session import AsyncSessionLocal
from app.queue.jobs import ToolRunJob
from app.tools.base import ToolExecutionContext
from app.tools.registry import tool_registry


async def run_tool_job(ctx, payload: dict) -> None:
    job = ToolRunJob.model_validate(payload)
    tool = tool_registry.get(job.tool_name)
    input_data = tool.input_schema.model_validate(job.input)
    options = tool.option_schema.model_validate(job.options)

    async with AsyncSessionLocal() as db:
        execution = await mark_execution_running(db, job.execution_id)
        try:
            result = await asyncio.wait_for(
                tool.run(input_data, options, ToolExecutionContext(user_id=job.user_id, request_id=job.request_id)),
                timeout=tool.limits.timeout_seconds,
            )
        except TimeoutError:
            await mark_execution_timed_out(db, execution)
        except Exception as exc:
            await mark_execution_failed(db, execution, exc)
        else:
            await mark_execution_succeeded(db, execution, result.model_dump())


class WorkerSettings:
    functions = [run_tool_job]
    redis_settings = redis_settings_from_url(get_settings().redis_url)
```

Import `redis_settings_from_url`, `mark_execution_running`, `mark_execution_timed_out`, `mark_execution_failed`, and `mark_execution_succeeded` in the final file.

- [ ] **Step 5: Update async API path**

Modify `backend/app/api/tools.py` so async tools:

1. Create `ToolExecution` with status `queued`.
2. Enqueue `run_tool_job` through ARQ.
3. Return:

```json
{
  "mode": "async",
  "status": "queued",
  "execution_id": "6f9619ff-8b86-d011-b42d-00cf4fc964ff"
}
```

Add one test-only async tool in the registry test fixture rather than marking public tools async.

- [ ] **Step 6: Run queue tests**

Run:

```powershell
cd backend
python -m pytest tests/queue tests/api/test_async_tool_runs.py -q
python -m ruff check .
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/queue backend/app/api/tools.py backend/app/services/executions.py backend/tests/queue backend/tests/api/test_async_tool_runs.py
git commit -m "feat: add async tool worker queue"
```

---

### Task 8: User Preferences, Favorites, And History APIs

**Files:**
- Create: `backend/app/api/me.py`
- Create: `backend/app/services/profile.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/services/executions.py`
- Test: `backend/tests/api/test_me.py`

- [ ] **Step 1: Write failing authenticated API tests**

Create `backend/tests/api/test_me.py`:

```python
import pytest


@pytest.mark.asyncio
async def test_favorites_require_authentication(client):
    response = await client.get("/api/me/favorites")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"


@pytest.mark.asyncio
async def test_preferences_require_authentication(client):
    response = await client.get("/api/me/preferences")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"
```

- [ ] **Step 2: Add `/api/me` routes**

Create `backend/app/api/me.py`:

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.permissions import CurrentUser, require_current_user
from app.db.session import get_db_session

router = APIRouter(prefix="/api/me", tags=["me"])


@router.get("/favorites")
async def list_favorites(
    user: CurrentUser = Depends(require_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> list[str]:
    return await list_user_favorites(db, user.id)


@router.put("/favorites/{tool_name}")
async def add_favorite(
    tool_name: str,
    user: CurrentUser = Depends(require_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, bool]:
    tool_registry.get(tool_name)
    await add_user_favorite(db, user.id, tool_name)
    return {"ok": True}


@router.delete("/favorites/{tool_name}")
async def remove_favorite(
    tool_name: str,
    user: CurrentUser = Depends(require_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, bool]:
    await remove_user_favorite(db, user.id, tool_name)
    return {"ok": True}


@router.get("/preferences")
async def get_preferences(
    user: CurrentUser = Depends(require_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    return await get_user_preferences(db, user.id)


@router.put("/preferences")
async def update_preferences(
    payload: dict,
    user: CurrentUser = Depends(require_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    return await update_user_preferences(db, user.id, payload)


@router.get("/executions")
async def list_executions(
    user: CurrentUser = Depends(require_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    return await list_user_executions(db, user.id)
```

- [ ] **Step 3: Add profile service functions**

Create `backend/app/services/profile.py`:

```python
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import FavoriteTool, UserPreference


async def list_user_favorites(db: AsyncSession, user_id: str) -> list[str]:
    result = await db.execute(
        select(FavoriteTool.tool_name)
        .where(FavoriteTool.user_id == UUID(user_id))
        .order_by(FavoriteTool.created_at.desc())
    )
    return list(result.scalars().all())


async def add_user_favorite(db: AsyncSession, user_id: str, tool_name: str) -> None:
    existing = await db.get(FavoriteTool, {"user_id": UUID(user_id), "tool_name": tool_name})
    if existing is None:
        db.add(FavoriteTool(user_id=UUID(user_id), tool_name=tool_name))
        await db.commit()


async def remove_user_favorite(db: AsyncSession, user_id: str, tool_name: str) -> None:
    await db.execute(
        delete(FavoriteTool)
        .where(FavoriteTool.user_id == UUID(user_id))
        .where(FavoriteTool.tool_name == tool_name)
    )
    await db.commit()


async def get_user_preferences(db: AsyncSession, user_id: str) -> dict:
    preference = await db.get(UserPreference, UUID(user_id))
    if preference is None:
        preference = UserPreference(user_id=UUID(user_id), theme="system", default_tool_options={})
        db.add(preference)
        await db.commit()
        await db.refresh(preference)
    return {"theme": preference.theme, "default_tool_options": preference.default_tool_options}


async def update_user_preferences(db: AsyncSession, user_id: str, payload: dict) -> dict:
    preference = await db.get(UserPreference, UUID(user_id))
    if preference is None:
        preference = UserPreference(user_id=UUID(user_id), theme="system", default_tool_options={})
        db.add(preference)
    if "theme" in payload:
        preference.theme = str(payload["theme"])
    if "default_tool_options" in payload and isinstance(payload["default_tool_options"], dict):
        preference.default_tool_options = payload["default_tool_options"]
    await db.commit()
    await db.refresh(preference)
    return {"theme": preference.theme, "default_tool_options": preference.default_tool_options}
```

- [ ] **Step 4: Import services in `/api/me`**

Modify `backend/app/api/me.py` imports:

```python
from app.services.executions import list_user_executions, serialize_execution
from app.services.profile import (
    add_user_favorite,
    get_user_preferences,
    list_user_favorites,
    remove_user_favorite,
    update_user_preferences,
)
from app.tools.registry import tool_registry
```

Change the history route return line:

```python
return [serialize_execution(execution) for execution in await list_user_executions(db, user.id)]
```

- [ ] **Step 5: Run tests**

Run:

```powershell
cd backend
python -m pytest tests/api/test_me.py -q
python -m ruff check .
```

Expected: PASS for auth requirements. Add authenticated happy-path tests after the user fixture exists.

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/me.py backend/app/main.py backend/app/services backend/tests/api/test_me.py
git commit -m "feat: add user personalization APIs"
```

---

### Task 9: Frontend Scaffold And API Client

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/index.html`
- Create: `frontend/tsconfig.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/src/main.ts`
- Create: `frontend/src/router.ts`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/api/types.ts`
- Test: `frontend/src/api/client.test.ts`

- [ ] **Step 1: Create Vue project files**

Create `frontend/package.json`:

```json
{
  "name": "yukit-frontend",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc --noEmit && vite build",
    "test": "vitest run",
    "lint": "eslint .",
    "preview": "vite preview"
  },
  "dependencies": {
    "@vitejs/plugin-vue": "latest",
    "lucide-vue-next": "latest",
    "vue": "latest",
    "vue-router": "latest"
  },
  "devDependencies": {
    "@types/node": "latest",
    "@vue/test-utils": "latest",
    "eslint": "latest",
    "typescript": "latest",
    "vite": "latest",
    "vitest": "latest",
    "vue-tsc": "latest"
  }
}
```

- [ ] **Step 2: Add API types**

Create `frontend/src/api/types.ts`:

```ts
export type ToolAccessLevel = 'public' | 'authenticated'
export type ToolExecutionMode = 'sync' | 'async'
export type ExecutionStatus = 'queued' | 'running' | 'succeeded' | 'failed' | 'timed_out' | 'canceled'

export interface ToolMetadata {
  name: string
  label: string
  description: string
  tags: string[]
  access_level: ToolAccessLevel
  execution_mode: ToolExecutionMode
  risk_level: 'low' | 'medium' | 'high'
  input_schema: Record<string, unknown>
  option_schema: Record<string, unknown>
  output_schema: Record<string, unknown>
}

export interface ToolRunResponse {
  mode: ToolExecutionMode
  status: ExecutionStatus
  result?: Record<string, unknown>
  execution_id?: string
}

export interface AuthMeResponse {
  authenticated: boolean
  user: null | { id: string; display_name: string }
}
```

- [ ] **Step 3: Add API client**

Create `frontend/src/api/client.ts`:

```ts
import type { AuthMeResponse, ToolMetadata, ToolRunResponse } from './types'

const API_BASE = import.meta.env.VITE_API_BASE ?? '/api'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    ...init
  })
  const body = await response.json()
  if (!response.ok) {
    throw new Error(body.error?.message ?? 'Request failed')
  }
  return body as T
}

export const api = {
  me: () => request<AuthMeResponse>('/auth/me'),
  tools: () => request<ToolMetadata[]>('/tools'),
  tool: (name: string) => request<ToolMetadata>(`/tools/${name}`),
  runTool: (name: string, input: Record<string, unknown>, options: Record<string, unknown>) =>
    request<ToolRunResponse>(`/tools/${name}/runs`, {
      method: 'POST',
      body: JSON.stringify({ input, options })
    })
}
```

- [ ] **Step 4: Add minimal app and routes**

Create `frontend/src/main.ts`:

```ts
import { createApp } from 'vue'
import { router } from './router'
import App from './views/App.vue'
import './styles.css'

createApp(App).use(router).mount('#app')
```

Create `frontend/src/router.ts`:

```ts
import { createRouter, createWebHistory } from 'vue-router'
import ToolView from './views/ToolView.vue'
import HistoryView from './views/HistoryView.vue'
import SettingsView from './views/SettingsView.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/tool/json-format' },
    { path: '/tool/:toolName', component: ToolView },
    { path: '/history', component: HistoryView },
    { path: '/settings', component: SettingsView }
  ]
})
```

- [ ] **Step 5: Run frontend checks**

Run:

```powershell
cd frontend
pnpm install
pnpm build
pnpm test
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend
git commit -m "chore: scaffold frontend app"
```

---

### Task 10: Schema-Driven Tool Workspace UI

**Files:**
- Create: `frontend/src/views/App.vue`
- Create: `frontend/src/views/ToolView.vue`
- Create: `frontend/src/views/HistoryView.vue`
- Create: `frontend/src/views/SettingsView.vue`
- Create: `frontend/src/components/AppLayout.vue`
- Create: `frontend/src/components/Sidebar.vue`
- Create: `frontend/src/components/GlobalCommandMenu.vue`
- Create: `frontend/src/components/SchemaForm.vue`
- Create: `frontend/src/components/SchemaField.vue`
- Create: `frontend/src/components/ToolPanel.vue`
- Create: `frontend/src/components/ResultPanel.vue`
- Create: `frontend/src/components/ExecutionStatusStrip.vue`
- Create: `frontend/src/components/StatusBadge.vue`
- Create: `frontend/src/design/tokens.css`
- Create: `frontend/src/styles.css`
- Test: `frontend/src/components/SchemaForm.test.ts`
- Test: `frontend/src/components/ResultPanel.test.ts`
- Test: `frontend/src/components/ExecutionStatusStrip.test.ts`
- Test: `frontend/src/views/ToolView.test.ts`

- [ ] **Step 1: Write schema form tests**

Create `frontend/src/components/SchemaForm.test.ts`:

```ts
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import SchemaForm from './SchemaForm.vue'

describe('SchemaForm', () => {
  it('renders string and boolean fields from JSON schema', () => {
    const wrapper = mount(SchemaForm, {
      props: {
        schema: {
          type: 'object',
          properties: {
            text: { type: 'string', title: 'Text' },
            sort_keys: { type: 'boolean', title: 'Sort keys' }
          },
          required: ['text']
        },
        modelValue: {}
      }
    })

    expect(wrapper.find('textarea[name="text"]').exists()).toBe(true)
    expect(wrapper.find('input[name="sort_keys"]').exists()).toBe(true)
  })
})
```

- [ ] **Step 2: Add design tokens**

Create `frontend/src/design/tokens.css`:

```css
:root {
  --color-primary: #2563eb;
  --color-success: #10b981;
  --color-warning: #f59e0b;
  --color-danger: #ef4444;
  --color-bg: #f6f8fb;
  --color-surface: #ffffff;
  --color-border: #dce3ee;
  --color-text: #172033;
  --color-muted: #536274;
  --color-subtle: #718096;
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-6: 24px;
  --radius-panel: 8px;
  --topbar-height: 56px;
  --sidebar-width: 264px;
  --inspector-width: 320px;
  --font-ui: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  --font-mono: "JetBrains Mono", "SFMono-Regular", Consolas, "Liberation Mono", monospace;
}
```

Modify `frontend/src/main.ts` to import tokens before app styles:

```ts
import './design/tokens.css'
import './styles.css'
```

- [ ] **Step 3: Add schema form component**

Create `frontend/src/components/SchemaForm.vue`:

```vue
<script setup lang="ts">
const props = defineProps<{
  schema: Record<string, any>
  modelValue: Record<string, unknown>
}>()

const emit = defineEmits<{
  'update:modelValue': [value: Record<string, unknown>]
}>()

function updateField(name: string, value: unknown) {
  emit('update:modelValue', { ...props.modelValue, [name]: value })
}
</script>

<template>
  <div class="schema-form">
    <label v-for="(field, name) in schema.properties ?? {}" :key="name" class="field">
      <span>{{ field.title ?? name }}</span>
      <textarea
        v-if="field.type === 'string'"
        :name="String(name)"
        :value="String(modelValue[String(name)] ?? '')"
        rows="8"
        @input="updateField(String(name), ($event.target as HTMLTextAreaElement).value)"
      />
      <input
        v-else-if="field.type === 'boolean'"
        :name="String(name)"
        type="checkbox"
        :checked="Boolean(modelValue[String(name)])"
        @change="updateField(String(name), ($event.target as HTMLInputElement).checked)"
      />
      <input
        v-else-if="field.type === 'integer' || field.type === 'number'"
        :name="String(name)"
        type="number"
        :value="Number(modelValue[String(name)] ?? field.default ?? 0)"
        @input="updateField(String(name), Number(($event.target as HTMLInputElement).value))"
      />
    </label>
  </div>
</template>
```

- [ ] **Step 4: Add status and result components**

Create `frontend/src/components/StatusBadge.vue`:

```vue
<script setup lang="ts">
defineProps<{ tone: 'neutral' | 'success' | 'warning' | 'danger'; label: string }>()
</script>

<template>
  <span class="status-badge" :data-tone="tone">{{ label }}</span>
</template>
```

Create `frontend/src/components/ExecutionStatusStrip.vue`:

```vue
<script setup lang="ts">
import { computed } from 'vue'
import StatusBadge from './StatusBadge.vue'
import type { ExecutionStatus, ToolAccessLevel, ToolExecutionMode } from '../api/types'

const props = defineProps<{
  accessLevel: ToolAccessLevel
  executionMode: ToolExecutionMode
  status: ExecutionStatus | 'idle'
  durationMs?: number
  historyPolicy: string
}>()

const tone = computed(() => {
  if (props.status === 'succeeded') return 'success'
  if (props.status === 'failed' || props.status === 'timed_out') return 'danger'
  if (props.status === 'queued' || props.status === 'running') return 'warning'
  return 'neutral'
})
</script>

<template>
  <div class="execution-status-strip" aria-live="polite">
    <StatusBadge tone="neutral" :label="accessLevel" />
    <StatusBadge tone="neutral" :label="executionMode" />
    <StatusBadge :tone="tone" :label="status" />
    <StatusBadge v-if="durationMs !== undefined" tone="neutral" :label="`${durationMs}ms`" />
    <StatusBadge tone="neutral" :label="historyPolicy" />
  </div>
</template>
```

Create `frontend/src/components/ResultPanel.vue`:

```vue
<script setup lang="ts">
import { ref, watch } from 'vue'

const props = defineProps<{
  result: Record<string, unknown> | null
  error: string | null
}>()

const activeView = ref<'raw' | 'error'>('raw')
watch(() => props.error, (error) => {
  if (error) activeView.value = 'error'
})
</script>

<template>
  <section class="tool-panel">
    <header class="panel-head">
      <span>Output</span>
      <div class="panel-actions">
        <button type="button" @click="activeView = 'raw'">Raw</button>
        <button type="button" @click="activeView = 'error'">Error</button>
        <button type="button">Copy</button>
      </div>
    </header>
    <pre v-if="activeView === 'raw'" class="result-code">{{ JSON.stringify(result, null, 2) }}</pre>
    <div v-else class="result-error">{{ error ?? 'No error' }}</div>
  </section>
</template>
```

- [ ] **Step 5: Add layout, command menu, and tool view**

Create `ToolView.vue` that:

1. Reads `toolName` from route params.
2. Fetches tool metadata through `api.tool`.
3. Renders input and options with `SchemaForm`.
4. Calls `api.runTool`.
5. Shows idle/queued/running/succeeded/failed/timed_out states in `ExecutionStatusStrip`.
6. Displays output through `ResultPanel` with `Raw` and `Error` views.
7. Uses a right-side options inspector on desktop and an options drawer/tabs pattern on mobile.

Core script shape:

```ts
const route = useRoute()
const tool = ref<ToolMetadata | null>(null)
const input = ref<Record<string, unknown>>({})
const options = ref<Record<string, unknown>>({})
const output = ref<Record<string, unknown> | null>(null)
const error = ref<string | null>(null)
const running = ref(false)

async function run() {
  if (!tool.value) return
  running.value = true
  error.value = null
  try {
    const result = await api.runTool(tool.value.name, input.value, options.value)
    output.value = result.result ?? { execution_id: result.execution_id, status: result.status }
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Request failed'
  } finally {
    running.value = false
  }
}
```

- [ ] **Step 6: Add app styling**

Create `frontend/src/styles.css` with:

```css
:root {
  color-scheme: light;
  font-family: var(--font-ui);
  background: var(--color-bg);
  color: var(--color-text);
}

body {
  margin: 0;
}

.app-shell {
  min-height: 100vh;
  display: grid;
  grid-template-columns: var(--sidebar-width) minmax(0, 1fr);
  grid-template-rows: var(--topbar-height) minmax(0, 1fr);
}

.sidebar {
  border-right: 1px solid var(--color-border);
  background: var(--color-surface);
  padding: var(--space-4);
}

.workspace {
  padding: var(--space-6);
  max-width: 1120px;
}

.tool-workspace-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) var(--inspector-width);
  gap: var(--space-4);
}

.tool-panel {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-panel);
  background: var(--color-surface);
  overflow: hidden;
}

.panel-head {
  min-height: 40px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid #edf1f6;
  padding: 0 var(--space-3);
  font-size: 13px;
  line-height: 18px;
  font-weight: 650;
}

.execution-status-strip {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.status-badge {
  border: 1px solid var(--color-border);
  border-radius: 999px;
  padding: 5px 9px;
  font-size: 12px;
  line-height: 16px;
  background: var(--color-surface);
  color: var(--color-muted);
}

.status-badge[data-tone='success'] {
  color: #047857;
  border-color: #9fe4c4;
  background: #ecfdf5;
}

.status-badge[data-tone='warning'] {
  color: #92400e;
  border-color: #f7d08a;
  background: #fffbeb;
}

.status-badge[data-tone='danger'] {
  color: #b91c1c;
  border-color: #f3a7a7;
  background: #fef2f2;
}

.field {
  display: grid;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
}

textarea,
input,
button {
  font: inherit;
}

textarea,
input[type="number"] {
  border: 1px solid #c8d0dc;
  border-radius: 8px;
  padding: 10px;
  background: var(--color-surface);
}

textarea:focus,
input:focus,
button:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

@media (max-width: 820px) {
  .app-shell {
    grid-template-columns: 1fr;
  }

  .sidebar {
    display: none;
  }

  .tool-workspace-grid {
    grid-template-columns: 1fr;
  }
}
```

- [ ] **Step 7: Run frontend tests**

Run:

```powershell
cd frontend
pnpm test
pnpm build
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add frontend/src
git commit -m "feat: add schema-driven tool workspace"
```

---

### Task 11: Auth State, Favorites, And History UI

**Files:**
- Create: `frontend/src/stores/auth.ts`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/components/AppLayout.vue`
- Modify: `frontend/src/components/GlobalCommandMenu.vue`
- Modify: `frontend/src/components/Sidebar.vue`
- Modify: `frontend/src/views/HistoryView.vue`
- Modify: `frontend/src/views/SettingsView.vue`
- Test: `frontend/src/stores/auth.test.ts`

- [ ] **Step 1: Add auth store tests**

Create `frontend/src/stores/auth.test.ts`:

```ts
import { describe, expect, it, vi } from 'vitest'
import { createAuthStore } from './auth'

describe('auth store', () => {
  it('loads anonymous auth state', async () => {
    const api = { me: vi.fn().mockResolvedValue({ authenticated: false, user: null }) }
    const store = createAuthStore(api)

    await store.load()

    expect(store.state.authenticated).toBe(false)
    expect(store.state.user).toBeNull()
  })
})
```

- [ ] **Step 2: Add auth store**

Create `frontend/src/stores/auth.ts`:

```ts
import { reactive } from 'vue'
import { api as defaultApi } from '../api/client'
import type { AuthMeResponse } from '../api/types'

export function createAuthStore(api = defaultApi) {
  const state = reactive<AuthMeResponse>({ authenticated: false, user: null })

  async function load() {
    const next = await api.me()
    state.authenticated = next.authenticated
    state.user = next.user
  }

  return { state, load }
}

export const authStore = createAuthStore()
```

- [ ] **Step 3: Extend API client**

Add methods:

```ts
favorites: () => request<string[]>('/me/favorites'),
addFavorite: (tool: string) => request<{ ok: boolean }>(`/me/favorites/${tool}`, { method: 'PUT' }),
removeFavorite: (tool: string) => request<{ ok: boolean }>(`/me/favorites/${tool}`, { method: 'DELETE' }),
history: () => request<ExecutionSummary[]>('/me/executions'),
preferences: () => request<Record<string, unknown>>('/me/preferences'),
updatePreferences: (payload: Record<string, unknown>) =>
  request<Record<string, unknown>>('/me/preferences', { method: 'PUT', body: JSON.stringify(payload) }),
logout: () => request<{ ok: boolean }>('/auth/logout', { method: 'POST' })
```

- [ ] **Step 4: Add UI behavior**

Implement:

- Header sign-in link points to `/api/auth/github/start`.
- Header global command/search can open tools, history, and settings.
- If authenticated, show display name and logout button.
- Sidebar shows favorites section only when authenticated.
- Sidebar keeps tag filters and tool discovery visible for anonymous users.
- History view shows login prompt when anonymous and execution list when authenticated.
- Settings view shows login prompt when anonymous and preferences form when authenticated.

- [ ] **Step 5: Run frontend tests**

Run:

```powershell
cd frontend
pnpm test
pnpm build
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src
git commit -m "feat: add authenticated user UI"
```

---

### Task 12: Docker, Caddy, And Local Compose

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `docker/Caddyfile`
- Create: `docker/entrypoint-api.sh`
- Create: `docker/entrypoint-worker.sh`
- Create: `.env.example`
- Test: manual smoke commands

- [ ] **Step 1: Add multi-stage Dockerfile**

Create `Dockerfile`:

```dockerfile
FROM node:22-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package.json frontend/pnpm-lock.yaml* ./
RUN corepack enable && pnpm install --frozen-lockfile=false
COPY frontend/ ./
RUN pnpm build

FROM python:3.13-slim AS backend-builder
WORKDIR /app/backend
COPY backend/pyproject.toml ./
RUN python -m pip install --upgrade pip && python -m pip install --prefix=/install ".[dev]"
COPY backend/ ./

FROM python:3.13-slim AS runtime
WORKDIR /app
ENV PYTHONPATH=/app/backend
COPY --from=backend-builder /install /usr/local
COPY backend/ /app/backend/
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist
COPY docker/entrypoint-api.sh /entrypoint-api.sh
COPY docker/entrypoint-worker.sh /entrypoint-worker.sh
RUN chmod +x /entrypoint-api.sh /entrypoint-worker.sh
EXPOSE 8000
```

- [ ] **Step 2: Add Compose services**

Create `docker-compose.yml`:

```yaml
services:
  caddy:
    image: caddy:2-alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./docker/Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
    depends_on:
      - api
    restart: unless-stopped

  api:
    build: .
    command: /entrypoint-api.sh
    env_file: .env
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

  worker:
    build: .
    command: /entrypoint-worker.sh
    env_file: .env
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

  postgres:
    image: postgres:17-alpine
    environment:
      POSTGRES_DB: yukit
      POSTGRES_USER: yukit
      POSTGRES_PASSWORD: yukit
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  caddy_data:
  caddy_config:
```

- [ ] **Step 3: Add Caddyfile**

Create `docker/Caddyfile`:

```caddyfile
:80 {
  encode gzip zstd

  header {
    X-Content-Type-Options nosniff
    Referrer-Policy strict-origin-when-cross-origin
    X-Frame-Options DENY
  }

  handle /api/* {
    reverse_proxy api:8000
  }

  handle {
    root * /app/frontend/dist
    try_files {path} /index.html
    file_server
  }
}
```

- [ ] **Step 4: Add entrypoints**

Create `docker/entrypoint-api.sh`:

```sh
#!/bin/sh
set -eu
cd /app/backend
alembic upgrade head
fastapi run app/main.py --host 0.0.0.0 --port 8000
```

Create `docker/entrypoint-worker.sh`:

```sh
#!/bin/sh
set -eu
cd /app/backend
python -m arq app.queue.worker.WorkerSettings
```

- [ ] **Step 5: Add environment example**

Create `.env.example`:

```dotenv
YUKIT_ENVIRONMENT=local
YUKIT_PUBLIC_BASE_URL=http://localhost
YUKIT_API_BASE_URL=http://localhost/api
YUKIT_DATABASE_URL=postgresql+asyncpg://yukit:yukit@postgres:5432/yukit
YUKIT_REDIS_URL=redis://redis:6379/0
YUKIT_SESSION_SECRET=local-development-session-secret-32-chars-minimum
YUKIT_GITHUB_CLIENT_ID=
YUKIT_GITHUB_CLIENT_SECRET=
YUKIT_CORS_ORIGINS=["http://localhost","http://localhost:5173"]
YUKIT_DOCS_ENABLED=false
```

- [ ] **Step 6: Run Compose smoke test**

Run:

```powershell
Copy-Item .env.example .env
docker compose up --build -d
curl.exe http://localhost/api/health
docker compose ps
docker compose down
```

Expected:

```json
{"status":"ok"}
```

`docker compose ps` should show `api`, `worker`, `postgres`, `redis`, and `caddy` running before shutdown.

- [ ] **Step 7: Commit**

```bash
git add Dockerfile docker-compose.yml docker .env.example
git commit -m "chore: add containerized deployment"
```

---

### Task 13: CI, Deployment Notes, And Production Guardrails

**Files:**
- Create: `.github/workflows/ci.yml`
- Create: `docs/deployment.md`
- Modify: `backend/app/config.py`
- Test: CI-equivalent local commands

- [ ] **Step 1: Add GitHub Actions workflow**

Create `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - name: Install backend
        run: |
          cd backend
          python -m pip install --upgrade pip
          python -m pip install -e ".[dev]"
      - name: Lint backend
        run: cd backend && ruff check .
      - name: Type check backend
        run: cd backend && mypy app
      - name: Test backend
        run: cd backend && pytest -q

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
        with:
          version: 10
      - uses: actions/setup-node@v4
        with:
          node-version: "22"
          cache: "pnpm"
          cache-dependency-path: frontend/pnpm-lock.yaml
      - name: Install frontend
        run: cd frontend && pnpm install --frozen-lockfile
      - name: Test frontend
        run: cd frontend && pnpm test
      - name: Build frontend
        run: cd frontend && pnpm build

  container:
    runs-on: ubuntu-latest
    needs: [backend, frontend]
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/build-push-action@v6
        with:
          context: .
          push: ${{ github.event_name == 'push' }}
          tags: |
            ghcr.io/${{ github.repository }}:main-${{ github.sha }}
            ghcr.io/${{ github.repository }}:latest
```

- [ ] **Step 2: Add deployment documentation**

Create `docs/deployment.md`:

```markdown
# YuKit Deployment

## Required Server Packages

- Docker
- Docker Compose plugin

## Required Secrets

- `YUKIT_SESSION_SECRET`
- `YUKIT_GITHUB_CLIENT_ID`
- `YUKIT_GITHUB_CLIENT_SECRET`
- PostgreSQL password if changed from the local default

## First Deploy

```bash
cd /opt/YuKit
cp .env.example .env
docker compose up -d --build
docker compose ps
curl http://localhost/api/health
```

## Upgrade

```bash
git pull
docker compose pull
docker compose up -d --build
docker compose ps
```

## Backup PostgreSQL

```bash
docker compose exec postgres pg_dump -U yukit yukit > backups/yukit-$(date +%F).sql
```

## Restore PostgreSQL

```bash
cat backups/yukit-2026-05-08.sql | docker compose exec -T postgres psql -U yukit yukit
```

## Health Checks

- API liveness: `GET /api/health`
- API readiness: `GET /api/ready`
- Worker: inspect ARQ worker logs and Redis queue depth
```

- [ ] **Step 3: Enforce production docs behavior**

Modify `backend/app/config.py` so production disables docs regardless of `YUKIT_DOCS_ENABLED`:

```python
@property
def effective_docs_enabled(self) -> bool:
    return self.environment != "production" and self.docs_enabled
```

Modify `backend/app/main.py` to use `settings.effective_docs_enabled`.

- [ ] **Step 4: Run full local verification**

Run:

```powershell
cd backend
python -m ruff check .
python -m mypy app
python -m pytest -q
cd ..\frontend
pnpm test
pnpm build
cd ..
docker compose build
```

Expected: every command exits 0.

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/ci.yml docs/deployment.md backend/app/config.py backend/app/main.py
git commit -m "ci: add verification and deployment workflow"
```

---

## Final Acceptance Checklist

- [ ] `GET /api/health` returns `{"status":"ok"}`.
- [ ] `GET /api/ready` reports PostgreSQL and Redis status.
- [ ] `GET /api/tools` returns JSON Format, Timestamp, Base64, and Regex Test metadata.
- [ ] Anonymous user can run `json-format`.
- [ ] Anonymous user receives `AUTH_REQUIRED` for authenticated-only tools.
- [ ] GitHub OAuth creates or links a local user and sets an HTTP-only session cookie.
- [ ] Signed-in user can manage favorites and preferences.
- [ ] Signed-in user can view execution history.
- [ ] Desktop UI follows Quiet Utility Workspace: top command search, left discovery sidebar, main input/output workspace, right options inspector.
- [ ] ResultPanel supports at least Raw and Error views, with API room for Tree and Diff later.
- [ ] Execution states use text plus semantic visual treatment, not color alone.
- [ ] Mobile layout uses tool picker, input/output tabs or stacked panels, and options drawer instead of squeezing desktop columns.
- [ ] Async tool jobs move from `queued` to `running` to a terminal status.
- [ ] Worker failures produce sanitized errors.
- [ ] Raw input is not stored unless a tool explicitly opts in.
- [ ] Redis rate limits apply by IP for anonymous users and by user ID for signed-in users.
- [ ] Production disables `/docs` and `/redoc`.
- [ ] Docker Compose starts API, worker, PostgreSQL, Redis, and Caddy.
- [ ] CI runs backend lint, backend type check, backend tests, frontend tests, frontend build, and container build.

## Self-Review Notes

- Spec coverage: architecture, auth, plugin model, queue execution, data model, frontend, deployment, and testing are mapped to Tasks 1-13.
- No production code should be written while reviewing this plan. Code snippets are implementation instructions for the execution phase.
- If a task becomes too large during execution, stop after the task's failing tests and split that task into a narrower plan before continuing.
