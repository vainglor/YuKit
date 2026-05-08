from hashlib import new as new_hash
from typing import Literal

from pydantic import BaseModel, Field

from app.tools.base import BaseTool, ToolAccessLevel, ToolExecutionMode


class TextHashInput(BaseModel):
    text: str = Field(max_length=1_000_000)


class TextHashOptions(BaseModel):
    algorithm: Literal["sha256", "sha512", "md5"] = "sha256"


class TextHashOutput(BaseModel):
    algorithm: str
    digest: str
    size_bytes: int


class TextHashTool(BaseTool[TextHashInput, TextHashOptions, TextHashOutput]):
    name = "text-hash"
    label = "Text Hash"
    description = "Calculate a digest for text input."
    tags = ["developer", "crypto", "async"]
    access_level = ToolAccessLevel.AUTHENTICATED
    execution_mode = ToolExecutionMode.ASYNC
    risk_level = "medium"
    input_model = TextHashInput
    option_model = TextHashOptions
    output_model = TextHashOutput

    async def run(self, input_data: TextHashInput, options: TextHashOptions) -> TextHashOutput:
        raw = input_data.text.encode("utf-8")
        digest = new_hash(options.algorithm, raw).hexdigest()
        return TextHashOutput(
            algorithm=options.algorithm,
            digest=digest,
            size_bytes=len(raw),
        )
