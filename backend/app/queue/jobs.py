import time

from sqlalchemy import select

from app.db.models import ToolExecution
from app.db.session import get_sessionmaker
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
        tool = get_tool_registry().get(execution.tool_name)
        if tool is None:
            execution.status = "failed"
            execution.error_code = "tool_not_found"
            execution.error_message = "Tool not found"
            await db.commit()
            return

        started = time.perf_counter()
        execution.status = "running"
        await db.commit()

        try:
            input_data = tool.input_model.model_validate(input_payload)
            options = tool.option_model.model_validate(options_payload)
            output = await tool.run(input_data, options)
        except Exception as exc:
            execution.status = "failed"
            execution.error_code = "tool_failed"
            execution.error_message = str(exc)
        else:
            execution.status = "succeeded"
            execution.result_json = output.model_dump()
            execution.duration_ms = int((time.perf_counter() - started) * 1000)
        await db.commit()
