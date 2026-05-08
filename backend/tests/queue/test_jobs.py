import asyncio

import pytest
from pydantic import BaseModel
from sqlalchemy import select

from app.db.models import ToolExecution
from app.queue.jobs import run_tool_job
from app.tools.base import BaseTool, ToolAccessLevel, ToolExecutionMode


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


@pytest.mark.asyncio
async def test_run_tool_job_executes_async_text_hash_tool(db_session) -> None:
    execution = ToolExecution(
        tool_name="text-hash",
        status="queued",
        execution_mode="async",
        options_json={"algorithm": "sha256"},
        input_digest="digest",
    )
    db_session.add(execution)
    await db_session.commit()

    await run_tool_job({}, execution.id, {"text": "YuKit"}, {"algorithm": "sha256"})

    await db_session.refresh(execution)
    saved = await db_session.get(ToolExecution, execution.id)
    assert saved is not None
    assert saved.status == "succeeded"
    assert saved.result_json == {
        "algorithm": "sha256",
        "digest": "a4ef91ad3d30bfadda12021b8d7d9848d651516767c5b007890e34395d7914ec",
        "size_bytes": 5,
    }


@pytest.mark.asyncio
async def test_run_tool_job_marks_tool_timeout(db_session, monkeypatch) -> None:
    class SlowInput(BaseModel):
        text: str

    class SlowOptions(BaseModel):
        pass

    class SlowOutput(BaseModel):
        ok: bool

    class SlowTool(BaseTool):
        name = "slow-tool"
        label = "Slow Tool"
        description = "Sleeps longer than the worker timeout."
        tags = ["test"]
        access_level = ToolAccessLevel.AUTHENTICATED
        execution_mode = ToolExecutionMode.ASYNC
        risk_level = "medium"
        timeout_seconds = 0.01
        input_model = SlowInput
        option_model = SlowOptions
        output_model = SlowOutput

        async def run(self, input_data: BaseModel, options: BaseModel) -> BaseModel:
            await asyncio.sleep(0.05)
            return SlowOutput(ok=True)

    class FakeRegistry:
        def get(self, name: str):
            return SlowTool() if name == "slow-tool" else None

    monkeypatch.setattr("app.queue.jobs.get_tool_registry", lambda: FakeRegistry())

    execution = ToolExecution(
        tool_name="slow-tool",
        status="queued",
        execution_mode="async",
        options_json={},
        input_digest="digest",
    )
    db_session.add(execution)
    await db_session.commit()

    await run_tool_job({}, execution.id, {"text": "YuKit"}, {})

    await db_session.refresh(execution)
    assert execution.status == "timed_out"
    assert execution.error_code == "tool_timed_out"
