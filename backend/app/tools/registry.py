from app.tools.base import BaseTool
from app.tools.json_format import JsonFormatTool


class ToolRegistry:
    def __init__(self, tools: list[BaseTool]) -> None:
        self._tools = {tool.name: tool for tool in tools}

    def all(self) -> list[BaseTool]:
        return list(self._tools.values())

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)


_registry = ToolRegistry([JsonFormatTool()])


def get_tool_registry() -> ToolRegistry:
    return _registry
