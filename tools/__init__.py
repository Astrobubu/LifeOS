from .base_tool import BaseTool
from .tasks_tool import TasksTool
from .calendar_tool import CalendarTool
from .notes_tool import NotesTool
from .gmail_tool import GmailTool
from .finance_tool import FinanceTool
from .browser_tool import BrowserTool
from .web_search_tool import WebSearchTool
from .printer_tool import PrinterTool
from .automations_tool import AutomationsTool
from .memory_tool import MemoryTool

AVAILABLE_TOOLS = {
    'tasks': TasksTool,
    'calendar': CalendarTool,
    'notes': MemoryTool,  # Deprecated notes → memory
    'memory': MemoryTool,
    'gmail': GmailTool,
    'finance': FinanceTool,
    'browser': BrowserTool,
    'web_search': WebSearchTool,
    'printer': PrinterTool,
    'automations': AutomationsTool,
    'taskmaster': TasksTool,
    'task_manager': TasksTool,
    'notification': TasksTool
}

def get_tool(tool_name: str) -> BaseTool:
    """Get a tool instance by name"""
    tool_class = AVAILABLE_TOOLS.get(tool_name)
    if tool_class:
        return tool_class()
    raise ValueError(f"Unknown tool: {tool_name}")

def get_all_tool_schemas() -> list[dict]:
    """Get OpenAI function schemas for all tools"""
    schemas = []
    for tool_class in AVAILABLE_TOOLS.values():
        tool = tool_class()
        schemas.extend(tool.get_function_schemas())
    return schemas
