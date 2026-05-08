from typing import Literal

import regex as regex_lib  # type: ignore[import-untyped]
from pydantic import BaseModel, Field

from app.tools.base import BaseTool, ToolAccessLevel, ToolExecutionMode

RegexFlag = Literal["ignorecase", "multiline", "dotall", "ascii", "verbose"]


class RegexTestInput(BaseModel):
    text: str = Field(
        max_length=100_000,
        description="Text to test against the regex pattern.",
    )
    pattern: str = Field(
        min_length=1,
        max_length=500,
        description="Regular expression pattern.",
    )


class RegexTestOptions(BaseModel):
    flags: list[RegexFlag] = Field(default_factory=list, description="Regex flags to enable.")
    max_matches: int = Field(default=50, ge=1, le=200, description="Maximum matches to return.")
    timeout_ms: int = Field(default=50, ge=10, le=250, description="Regex execution timeout.")


class RegexMatch(BaseModel):
    text: str
    start: int
    end: int
    groups: list[str | None]
    named_groups: dict[str, str | None]


class RegexTestOutput(BaseModel):
    matches: list[RegexMatch]
    count: int
    truncated: bool


class RegexTestTool(BaseTool[RegexTestInput, RegexTestOptions, RegexTestOutput]):
    name = "regex-test"
    label = "Regex Test"
    description = "Test regular expressions with strict limits and match details."
    tags = ["developer", "text"]
    access_level = ToolAccessLevel.PUBLIC
    execution_mode = ToolExecutionMode.SYNC
    risk_level = "medium"
    input_model = RegexTestInput
    option_model = RegexTestOptions
    output_model = RegexTestOutput
    allow_history_input_storage = False

    async def run(
        self,
        input_data: RegexTestInput,
        options: RegexTestOptions,
    ) -> RegexTestOutput:
        flags = self._compile_flags(options.flags)
        try:
            pattern = regex_lib.compile(input_data.pattern, flags)
        except regex_lib.error as exc:
            raise ValueError(f"Invalid regex pattern: {exc}") from exc

        matches: list[RegexMatch] = []
        timeout_seconds = options.timeout_ms / 1000

        try:
            for match in pattern.finditer(input_data.text, timeout=timeout_seconds):
                if len(matches) >= options.max_matches:
                    return RegexTestOutput(
                        matches=matches,
                        count=len(matches),
                        truncated=True,
                    )

                matches.append(
                    RegexMatch(
                        text=match.group(0),
                        start=match.start(),
                        end=match.end(),
                        groups=list(match.groups()),
                        named_groups=dict(match.groupdict()),
                    )
                )
        except TimeoutError as exc:
            raise ValueError("Regex evaluation timed out.") from exc

        return RegexTestOutput(matches=matches, count=len(matches), truncated=False)

    @staticmethod
    def _compile_flags(flags: list[RegexFlag]) -> int:
        compiled = 0
        for flag in set(flags):
            if flag == "ignorecase":
                compiled |= regex_lib.IGNORECASE
            elif flag == "multiline":
                compiled |= regex_lib.MULTILINE
            elif flag == "dotall":
                compiled |= regex_lib.DOTALL
            elif flag == "ascii":
                compiled |= regex_lib.ASCII
            elif flag == "verbose":
                compiled |= regex_lib.VERBOSE
        return compiled
