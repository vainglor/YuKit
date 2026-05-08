from app.tools.base import BaseTool
from app.tools.base64_codec import Base64CodecTool
from app.tools.json_format import JsonFormatTool
from app.tools.timestamp import TimestampTool


class ToolRegistry:
    def __init__(self, tools: list[BaseTool]) -> None:
        self._tools = {tool.name: tool for tool in tools}

    def all(self) -> list[BaseTool]:
        return list(self._tools.values())

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)


_registry = ToolRegistry([JsonFormatTool(), TimestampTool(), Base64CodecTool()])


def get_tool_registry() -> ToolRegistry:
    return _registry
