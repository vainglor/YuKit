import pytest
from sqlalchemy import select

from app.db.models import FavoriteTool, ToolExecution, User, UserPreference


@pytest.mark.asyncio
async def test_user_related_models_round_trip(db_session) -> None:
    user = User(email="dev@example.com", display_name="Dev User")
    db_session.add(user)
    await db_session.flush()

    db_session.add(FavoriteTool(user_id=user.id, tool_name="json-format"))
    db_session.add(UserPreference(user_id=user.id, preferences={"theme": "system"}))
    db_session.add(
        ToolExecution(
            user_id=user.id,
            tool_name="json-format",
            status="succeeded",
            execution_mode="sync",
            options_json={"indent": 2},
            result_json={"formatted": "{}"},
        )
    )
    await db_session.commit()

    result = await db_session.execute(select(User).where(User.email == "dev@example.com"))
    saved = result.scalar_one()

    assert saved.display_name == "Dev User"
    assert saved.favorites[0].tool_name == "json-format"
    assert saved.preference.preferences["theme"] == "system"
    assert saved.executions[0].result_json == {"formatted": "{}"}
