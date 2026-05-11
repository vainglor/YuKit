import asyncio
import time

from sqlalchemy import select

from app.db.models import ToolExecution
from app.db.session import get_sessionmaker
from app.observability import WORKER_LOGGER
from app.tools.registry import get_tool_registry


async def run_tool_job(
    _: dict,
    execution_id: str,
    input_payload: dict,
    options_payload: dict,
) -> None:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        result = await db.execute(select(ToolExecution).where(ToolExecution.id == execution_id))
        execution = result.scalar_one()
        if execution.status == "canceled":
            WORKER_LOGGER.info(
                "worker job skipped tool=%s execution_id=%s status=canceled",
                execution.tool_name,
                execution.id,
                extra={
                    "tool": execution.tool_name,
                    "execution_id": execution.id,
                    "status": "canceled",
                },
            )
            return

        tool = get_tool_registry().get(execution.tool_name)
        if tool is None:
            execution.status = "failed"
            execution.error_code = "tool_not_found"
            execution.error_message = "Tool not found"
            await db.commit()
            WORKER_LOGGER.error(
                "worker job failed tool=%s execution_id=%s status=failed error_code=tool_not_found",
                execution.tool_name,
                execution.id,
                extra={
                    "tool": execution.tool_name,
                    "execution_id": execution.id,
                    "status": "failed",
                    "error_code": "tool_not_found",
                },
            )
            return

        started = time.perf_counter()
        execution.status = "running"
        await db.commit()
        WORKER_LOGGER.info(
            "worker job running tool=%s execution_id=%s status=running",
            execution.tool_name,
            execution.id,
            extra={
                "tool": execution.tool_name,
                "execution_id": execution.id,
                "status": "running",
            },
        )

        try:
            input_data = tool.input_model.model_validate(input_payload)
            options = tool.option_model.model_validate(options_payload)
            output = await asyncio.wait_for(
                tool.run(input_data, options),
                timeout=tool.timeout_seconds,
            )
        except TimeoutError:
            execution.status = "timed_out"
            execution.error_code = "tool_timed_out"
            execution.error_message = "Tool execution timed out"
            execution.duration_ms = int((time.perf_counter() - started) * 1000)
            WORKER_LOGGER.warning(
                "worker job timed out tool=%s execution_id=%s duration_ms=%s",
                execution.tool_name,
                execution.id,
                execution.duration_ms,
                extra={
                    "tool": execution.tool_name,
                    "execution_id": execution.id,
                    "status": "timed_out",
                    "duration_ms": execution.duration_ms,
                    "error_code": "tool_timed_out",
                },
            )
        except Exception as exc:
            execution.status = "failed"
            execution.error_code = "tool_failed"
            execution.error_message = str(exc)
            execution.duration_ms = int((time.perf_counter() - started) * 1000)
            WORKER_LOGGER.exception(
                "worker job failed tool=%s execution_id=%s duration_ms=%s",
                execution.tool_name,
                execution.id,
                execution.duration_ms,
                extra={
                    "tool": execution.tool_name,
                    "execution_id": execution.id,
                    "status": "failed",
                    "duration_ms": execution.duration_ms,
                    "error_code": "tool_failed",
                },
            )
        else:
            execution.status = "succeeded"
            execution.result_json = output.model_dump()
            execution.duration_ms = int((time.perf_counter() - started) * 1000)
            WORKER_LOGGER.info(
                "worker job succeeded tool=%s execution_id=%s duration_ms=%s",
                execution.tool_name,
                execution.id,
                execution.duration_ms,
                extra={
                    "tool": execution.tool_name,
                    "execution_id": execution.id,
                    "status": "succeeded",
                    "duration_ms": execution.duration_ms,
                },
            )
        await db.commit()
