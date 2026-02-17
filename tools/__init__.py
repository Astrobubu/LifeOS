from .base_tool import BaseTool
from .calendar_tool import CalendarTool
from .gmail_tool import GmailTool
from .finance_tool import FinanceTool
from .printer_tool import PrinterTool
from .automations_tool import AutomationsTool
from .memory_tool import MemoryTool

AVAILABLE_TOOLS = {
    'calendar': CalendarTool,
    'gmail': GmailTool,
    'finance': FinanceTool,
    'printer': PrinterTool,
    'automations': AutomationsTool,
    'memory': MemoryTool,
}

# Singleton cache - tools are stateless, no need to re-instantiate
_tool_instances: dict[str, BaseTool] = {}


def get_tool(tool_name: str) -> BaseTool:
    """Get a cached tool instance by name"""
    if tool_name not in _tool_instances:
        tool_class = AVAILABLE_TOOLS.get(tool_name)
        if not tool_class:
            raise ValueError(f"Unknown tool: {tool_name}")
        _tool_instances[tool_name] = tool_class()
    return _tool_instances[tool_name]


def get_all_tool_schemas() -> list[dict]:
    """Get OpenAI function schemas for all tools"""
    schemas = []
    seen = set()
    for name in AVAILABLE_TOOLS:
        tool = get_tool(name)
        for schema in tool.get_function_schemas():
            func_name = schema["function"]["name"]
            if func_name not in seen:
                seen.add(func_name)
                schemas.append(schema)
    return schemas
