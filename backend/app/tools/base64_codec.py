import base64
from binascii import Error as Base64DecodeError
from typing import Literal

from pydantic import BaseModel, Field

from app.tools.base import BaseTool, ToolAccessLevel, ToolExecutionMode


class Base64CodecInput(BaseModel):
    text: str = Field(
        min_length=1,
        max_length=1_000_000,
        description="Text to encode or Base64 text to decode.",
    )


class Base64CodecOptions(BaseModel):
    mode: Literal["encode", "decode"] = Field(default="encode", description="Codec direction.")
    charset: str = Field(default="utf-8", description="Character encoding for text conversion.")


class Base64CodecOutput(BaseModel):
    text: str
    size_bytes: int


class Base64CodecTool(BaseTool):
    name = "base64"
    label = "Base64"
    description = "Encode plain text to Base64 or decode Base64 back to text."
    tags = ["developer", "codec"]
    access_level = ToolAccessLevel.PUBLIC
    execution_mode = ToolExecutionMode.SYNC
    risk_level = "low"
    input_model = Base64CodecInput
    option_model = Base64CodecOptions
    output_model = Base64CodecOutput
    allow_history_input_storage = False

    async def run(
        self,
        input_data: Base64CodecInput,
        options: Base64CodecOptions,
    ) -> Base64CodecOutput:
        try:
            if options.mode == "encode":
                result = base64.b64encode(input_data.text.encode(options.charset)).decode("ascii")
            else:
                decoded = base64.b64decode(input_data.text, validate=True)
                result = decoded.decode(options.charset)
        except (Base64DecodeError, LookupError, UnicodeDecodeError, UnicodeEncodeError) as exc:
            raise ValueError("Invalid Base64 input or charset.") from exc

        return Base64CodecOutput(text=result, size_bytes=len(result.encode("utf-8")))
