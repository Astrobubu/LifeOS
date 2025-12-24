"""
Print Sub-Agent - Fast agent for thermal printer operations
"""
from .base_sub_agent import BaseSubAgent
from ..planning import AgentType
from tools.printer_tool import PrinterTool


class PrintSubAgent(BaseSubAgent):
    """
    Print agent - optimized for SPEED.
    
    No complex reasoning needed, just extract content and print.
    """
    
    agent_type = AgentType.PRINT
    agent_name = "print"
    max_iterations = 2  # Print should be fast
    
    def __init__(self):
        super().__init__()
        self.printer_tool = PrinterTool()
    
    def get_system_prompt(self) -> str:
        return """You are the PRINT sub-agent for LifeOS.

## Your Role
Print content to the thermal printer. BE FAST.

## Rules
1. Extract the content to print
2. Call the appropriate print function
3. Respond with "✓ Printed" - nothing more

## Functions
- print_task: For task-formatted output (title + description)
- print_text: For general text/content

Don't overthink. Just print.
"""
    
    def get_tools(self) -> list[dict]:
        return self.printer_tool.get_function_schemas()
    
    def get_tool_mapping(self) -> dict[str, str]:
        return {
            "print_task": "printer",
            "print_text": "printer",
        }
