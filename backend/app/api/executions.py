from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.permissions import optional_current_user
from app.db.models import ToolExecution, User
from app.db.session import get_db_session
from app.errors import ApiError

router = APIRouter(prefix="/executions", tags=["executions"])


def serialize_execution(execution: ToolExecution) -> dict[str, Any]:
    return {
        "id": execution.id,
        "tool": execution.tool_name,
        "status": execution.status,
        "mode": execution.execution_mode,
        "duration_ms": execution.duration_ms,
        "result": execution.result_json,
        "error_code": execution.error_code,
        "error_message": execution.error_message,
    }


@router.get("/{execution_id}")
async def get_execution(
    execution_id: str,
    user: User | None = Depends(optional_current_user),
    db: AsyncSession | None = Depends(get_db_session),
) -> dict[str, Any]:
    if db is None:
        raise ApiError(
            status_code=503,
            code="database_unavailable",
            message="Database is unavailable",
        )

    result = await db.execute(select(ToolExecution).where(ToolExecution.id == execution_id))
    execution = result.scalar_one_or_none()
    if execution is None:
        raise ApiError(status_code=404, code="execution_not_found", message="Execution not found")
    if execution.user_id and (user is None or execution.user_id != user.id):
        raise ApiError(status_code=404, code="execution_not_found", message="Execution not found")

    return {"execution": serialize_execution(execution)}


@router.post("/{execution_id}/cancel")
async def cancel_execution(
    execution_id: str,
    user: User | None = Depends(optional_current_user),
    db: AsyncSession | None = Depends(get_db_session),
) -> dict[str, Any]:
    if db is None:
        raise ApiError(
            status_code=503,
            code="database_unavailable",
            message="Database is unavailable",
        )

    result = await db.execute(select(ToolExecution).where(ToolExecution.id == execution_id))
    execution = result.scalar_one_or_none()
    if execution is None:
        raise ApiError(status_code=404, code="execution_not_found", message="Execution not found")
    if execution.user_id and (user is None or execution.user_id != user.id):
        raise ApiError(status_code=404, code="execution_not_found", message="Execution not found")
    if user is None:
        raise ApiError(status_code=404, code="execution_not_found", message="Execution not found")

    if execution.status in {"queued", "running"}:
        execution.status = "canceled"
        await db.commit()
        await db.refresh(execution)

    return {"execution": serialize_execution(execution)}
