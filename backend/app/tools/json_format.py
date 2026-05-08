import json
from json import JSONDecodeError
from typing import Any

from pydantic import BaseModel, Field

from app.tools.base import BaseTool, ToolAccessLevel, ToolExecutionMode


class JsonFormatInput(BaseModel):
    text: str = Field(
        min_length=1,
        max_length=1_000_000,
        description="Raw JSON text to validate and format.",
    )


class JsonFormatOptions(BaseModel):
    indent: int = Field(default=2, ge=0, le=8, description="Indent size in spaces.")
    sort_keys: bool = Field(default=False, description="Sort object keys alphabetically.")
    ensure_ascii: bool = Field(default=False, description="Escape non-ASCII characters.")


class JsonFormatOutput(BaseModel):
    formatted: str
    valid: bool
    size_bytes: int


class JsonFormatTool(BaseTool):
    name = "json-format"
    label = "JSON Format"
    description = "Validate, format, and normalize JSON with predictable options."
    tags = ["developer", "format"]
    access_level = ToolAccessLevel.PUBLIC
    execution_mode = ToolExecutionMode.SYNC
    risk_level = "low"
    input_model = JsonFormatInput
    option_model = JsonFormatOptions
    output_model = JsonFormatOutput
    allow_history_input_storage = False

    async def run(
        self,
        input_data: JsonFormatInput,
        options: JsonFormatOptions,
    ) -> JsonFormatOutput:
        try:
            parsed: Any = json.loads(input_data.text)
        except JSONDecodeError as exc:
            raise ValueError(
                f"Invalid JSON at line {exc.lineno} column {exc.colno}: {exc.msg}"
            ) from exc

        indent = None if options.indent == 0 else options.indent
        formatted = json.dumps(
            parsed,
            ensure_ascii=options.ensure_ascii,
            indent=indent,
            sort_keys=options.sort_keys,
            separators=None if indent else (",", ":"),
        )
        return JsonFormatOutput(
            formatted=formatted,
            valid=True,
            size_bytes=len(formatted.encode("utf-8")),
        )
