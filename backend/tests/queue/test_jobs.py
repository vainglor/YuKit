import pytest
from sqlalchemy import select

from app.db.models import ToolExecution
from app.queue.jobs import run_tool_job


@pytest.mark.asyncio
async def test_run_tool_job_updates_execution(db_session) -> None:
    execution = ToolExecution(
        tool_name="json-format",
        status="queued",
        execution_mode="async",
        options_json={"indent": 2, "sort_keys": True, "ensure_ascii": False},
    )
    db_session.add(execution)
    await db_session.commit()

    await run_tool_job(
        {},
        execution.id,
        {"text": '{"b":1,"a":2}'},
        {"indent": 2, "sort_keys": True, "ensure_ascii": False},
    )

    await db_session.refresh(execution)
    result = await db_session.execute(select(ToolExecution).where(ToolExecution.id == execution.id))
    saved = result.scalar_one()
    assert saved.status == "succeeded"
    assert saved.result_json["formatted"] == '{\n  "a": 2,\n  "b": 1\n}'
