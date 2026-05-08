import pytest

from app.tools.json_format import JsonFormatInput, JsonFormatOptions, JsonFormatTool


@pytest.mark.asyncio
async def test_json_format_pretty_prints_and_sorts_keys() -> None:
    tool = JsonFormatTool()

    result = await tool.run(
        JsonFormatInput(text='{"b":1,"a":{"d":4,"c":3}}'),
        JsonFormatOptions(indent=2, sort_keys=True, ensure_ascii=False),
    )

    assert result.formatted == '{\n  "a": {\n    "c": 3,\n    "d": 4\n  },\n  "b": 1\n}'
    assert result.valid is True
    assert result.size_bytes == len(result.formatted.encode("utf-8"))


@pytest.mark.asyncio
async def test_json_format_reports_parse_location() -> None:
    tool = JsonFormatTool()

    with pytest.raises(ValueError) as exc_info:
        await tool.run(JsonFormatInput(text='{"a": }'), JsonFormatOptions())

    assert "line 1 column 7" in str(exc_info.value)
