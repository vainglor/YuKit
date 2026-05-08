import pytest

from app.tools.regex_test import RegexTestOptions, RegexTestTool


@pytest.mark.asyncio
async def test_regex_test_returns_matches_with_groups() -> None:
    tool = RegexTestTool()

    result = await tool.run(
        tool.input_model(
            text="Order A-100 and B-205",
            pattern=r"(?P<prefix>[A-Z])-(\d+)",
        ),
        RegexTestOptions(flags=["ignorecase"], max_matches=5),
    )

    assert result.count == 2
    assert result.truncated is False
    assert result.matches[0].text == "A-100"
    assert result.matches[0].start == 6
    assert result.matches[0].end == 11
    assert result.matches[0].groups == ["A", "100"]
    assert result.matches[0].named_groups == {"prefix": "A"}


@pytest.mark.asyncio
async def test_regex_test_respects_max_matches() -> None:
    tool = RegexTestTool()

    result = await tool.run(
        tool.input_model(text="a1 b2 c3", pattern=r"\w\d"),
        RegexTestOptions(max_matches=2),
    )

    assert result.count == 2
    assert result.truncated is True
    assert [match.text for match in result.matches] == ["a1", "b2"]


@pytest.mark.asyncio
async def test_regex_test_rejects_invalid_pattern() -> None:
    tool = RegexTestTool()

    with pytest.raises(ValueError, match="Invalid regex pattern"):
        await tool.run(
            tool.input_model(text="abc", pattern="["),
            RegexTestOptions(),
        )
