import pytest

from app.tools.timestamp import TimestampInput, TimestampOptions, TimestampTool


@pytest.mark.asyncio
async def test_timestamp_converts_unix_seconds_to_iso_utc() -> None:
    tool = TimestampTool()

    result = await tool.run(
        TimestampInput(text="1700000000"),
        TimestampOptions(mode="from-unix"),
    )

    assert result.unix_seconds == 1_700_000_000
    assert result.unix_milliseconds == 1_700_000_000_000
    assert result.iso_utc == "2023-11-14T22:13:20Z"


@pytest.mark.asyncio
async def test_timestamp_converts_iso_utc_to_unix_seconds() -> None:
    tool = TimestampTool()

    result = await tool.run(
        TimestampInput(text="2023-11-14T22:13:20Z"),
        TimestampOptions(mode="from-iso"),
    )

    assert result.unix_seconds == 1_700_000_000
    assert result.unix_milliseconds == 1_700_000_000_000
    assert result.iso_utc == "2023-11-14T22:13:20Z"


@pytest.mark.asyncio
async def test_timestamp_rejects_invalid_input() -> None:
    tool = TimestampTool()

    with pytest.raises(ValueError) as exc_info:
        await tool.run(TimestampInput(text="not a timestamp"), TimestampOptions(mode="from-unix"))

    assert "Invalid timestamp input" in str(exc_info.value)
