import time
from hashlib import sha256
from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.permissions import optional_current_user
from app.db.models import ToolExecution, User
from app.db.session import get_db_session
from app.dependencies import get_redis
from app.errors import ApiError
from app.queue.client import get_arq_pool
from app.services.rate_limits import RateLimit, check_rate_limit
from app.tools.base import ToolAccessLevel, ToolExecutionMode
from app.tools.registry import get_tool_registry

router = APIRouter(tags=["tools"])


class ToolRunRequest(BaseModel):
    input: dict = Field(default_factory=dict)
    options: dict = Field(default_factory=dict)


@router.get("/tools")
async def list_tools() -> dict[str, object]:
    registry = get_tool_registry()
    return {"tools": [tool.metadata() for tool in registry.all()]}


@router.get("/tools/{name}")
async def get_tool(name: str) -> dict[str, object]:
    tool = get_tool_registry().get(name)
    if tool is None:
        raise ApiError(status_code=404, code="tool_not_found", message="Tool not found")
    return {"tool": tool.metadata()}


def _client_key(request: Request, user: User | None) -> str:
    if user is not None:
        return f"user:{user.id}"
    host = request.client.host if request.client else "unknown"
    return f"ip:{host}"


async def _create_execution(
    db: AsyncSession | None,
    *,
    user: User | None,
    tool_name: str,
    status: str,
    execution_mode: str,
    options: dict[str, Any],
    input_payload: dict[str, Any],
) -> ToolExecution | None:
    if db is None:
        return None
    digest = sha256(repr(input_payload).encode("utf-8")).hexdigest()
    execution = ToolExecution(
        user_id=user.id if user else None,
        tool_name=tool_name,
        status=status,
        execution_mode=execution_mode,
        options_json=options,
        input_digest=digest,
    )
    db.add(execution)
    await db.flush()
    return execution


@router.post("/tools/{name}/runs")
async def run_tool(
    name: str,
    payload: ToolRunRequest,
    request: Request,
    user: User | None = Depends(optional_current_user),
    db: AsyncSession | None = Depends(get_db_session),
    redis=Depends(get_redis),
) -> dict[str, object]:
    tool = get_tool_registry().get(name)
    if tool is None:
        raise ApiError(status_code=404, code="tool_not_found", message="Tool not found")
    if tool.access_level == ToolAccessLevel.AUTHENTICATED and user is None:
        raise ApiError(status_code=401, code="auth_required", message="Authentication required")

    await check_rate_limit(
        redis,
        f"rate:tool:{tool.name}:{_client_key(request, user)}",
        RateLimit(max_requests=60 if user else 30, window_seconds=60),
    )

    input_data = tool.input_model.model_validate(payload.input)
    options = tool.option_model.model_validate(payload.options)

    if tool.execution_mode == ToolExecutionMode.ASYNC:
        execution = await _create_execution(
            db,
            user=user,
            tool_name=tool.name,
            status="queued",
            execution_mode=tool.execution_mode,
            options=payload.options,
            input_payload=payload.input,
        )
        if db is not None:
            await db.commit()
        if execution is None:
            raise ApiError(
                status_code=503,
                code="database_unavailable",
                message="Database is unavailable",
            )
        pool = await get_arq_pool()
        if pool is None:
            raise ApiError(
                status_code=503,
                code="queue_unavailable",
                message="Queue is unavailable",
            )
        await pool.enqueue_job("run_tool_job", execution.id, payload.input, payload.options)
        await pool.aclose()
        return {
            "execution_id": execution.id,
            "tool": tool.name,
            "status": "queued",
            "mode": "async",
        }

    started = time.perf_counter()
    execution = await _create_execution(
        db,
        user=user,
        tool_name=tool.name,
        status="running",
        execution_mode=tool.execution_mode,
        options=payload.options,
        input_payload=payload.input,
    )
    try:
        result = await tool.run(input_data, options)
    except ValueError as exc:
        if execution is not None and db is not None:
            execution.status = "failed"
            execution.error_code = "invalid_json"
            execution.error_message = str(exc)
            execution.duration_ms = int((time.perf_counter() - started) * 1000)
            await db.commit()
        raise ApiError(status_code=422, code="invalid_json", message=str(exc)) from exc

    duration_ms = int((time.perf_counter() - started) * 1000)
    if execution is not None and db is not None:
        execution.status = "succeeded"
        execution.duration_ms = duration_ms
        execution.result_json = result.model_dump()
        await db.commit()
    return {
        "execution_id": execution.id if execution else "",
        "tool": tool.name,
        "status": "succeeded",
        "mode": tool.execution_mode,
        "duration_ms": duration_ms,
        "result": result.model_dump(),
    }
