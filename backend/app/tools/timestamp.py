from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.tools.base import BaseTool, ToolAccessLevel, ToolExecutionMode


class TimestampInput(BaseModel):
    text: str = Field(
        min_length=1,
        max_length=200,
        description="Unix seconds or an ISO-8601 datetime string.",
    )


class TimestampOptions(BaseModel):
    mode: Literal["from-unix", "from-iso"] = Field(
        default="from-unix",
        description="Conversion direction.",
    )


class TimestampOutput(BaseModel):
    unix_seconds: int
    unix_milliseconds: int
    iso_utc: str


class TimestampTool(BaseTool):
    name = "timestamp"
    label = "Timestamp"
    description = "Convert between Unix seconds and ISO-8601 UTC datetime strings."
    tags = ["developer", "time"]
    access_level = ToolAccessLevel.PUBLIC
    execution_mode = ToolExecutionMode.SYNC
    risk_level = "low"
    input_model = TimestampInput
    option_model = TimestampOptions
    output_model = TimestampOutput
    allow_history_input_storage = False

    async def run(
        self,
        input_data: TimestampInput,
        options: TimestampOptions,
    ) -> TimestampOutput:
        try:
            if options.mode == "from-unix":
                value = int(input_data.text.strip())
                converted = datetime.fromtimestamp(value, tz=UTC)
            else:
                converted = datetime.fromisoformat(input_data.text.strip().replace("Z", "+00:00"))
                if converted.tzinfo is None:
                    converted = converted.replace(tzinfo=UTC)
                converted = converted.astimezone(UTC)
        except (OverflowError, ValueError) as exc:
            raise ValueError("Invalid timestamp input.") from exc

        unix_seconds = int(converted.timestamp())
        iso_utc = converted.replace(microsecond=0).isoformat().replace("+00:00", "Z")
        return TimestampOutput(
            unix_seconds=unix_seconds,
            unix_milliseconds=unix_seconds * 1000,
            iso_utc=iso_utc,
        )
