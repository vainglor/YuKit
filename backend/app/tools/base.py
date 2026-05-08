from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class ToolAccessLevel(StrEnum):
    PUBLIC = "public"
    AUTHENTICATED = "authenticated"


class ToolExecutionMode(StrEnum):
    SYNC = "sync"
    ASYNC = "async"


class BaseTool[InputModelT: BaseModel, OptionModelT: BaseModel, OutputModelT: BaseModel](ABC):
    name: str
    label: str
    description: str
    tags: list[str]
    access_level: ToolAccessLevel
    execution_mode: ToolExecutionMode
    risk_level: str
    input_model: type[InputModelT]
    option_model: type[OptionModelT]
    output_model: type[OutputModelT]
    allow_history_input_storage: bool = False
    timeout_seconds: float = 10

    def metadata(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "label": self.label,
            "description": self.description,
            "tags": self.tags,
            "access_level": self.access_level,
            "execution_mode": self.execution_mode,
            "risk_level": self.risk_level,
            "allow_history_input_storage": self.allow_history_input_storage,
            "input_schema": self.input_model.model_json_schema(),
            "option_schema": self.option_model.model_json_schema(),
            "output_schema": self.output_model.model_json_schema(),
        }

    @abstractmethod
    async def run(self, input_data: InputModelT, options: OptionModelT) -> OutputModelT:
        raise NotImplementedError
