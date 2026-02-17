"""
Print Sub-Agent - Fast agent for thermal printer operations

Also handles "add task X" since tasks ARE physical prints.
"""
import logging
from .base_sub_agent import BaseSubAgent
from tools.printer_tool import PrinterTool

logger = logging.getLogger(__name__)


class PrintSubAgent(BaseSubAgent):
    """
    Print agent - optimized for SPEED.

    No complex reasoning needed, just extract content and print.
    Also handles "add task X" - tasks are physical printouts.
    """

    agent_name = "print"
    max_iterations = 2  # Print should be fast

    def __init__(self):
        super().__init__()
        self.printer_tool = PrinterTool()

    def get_system_prompt(self) -> str:
        return """You are the PRINT sub-agent for HAL 9000.

## Your Role
Print content to the thermal printer. BE FAST.

## Rules
1. Extract the content to print
2. Call the appropriate print function
3. Respond with "Printed." — nothing more

## Task = Print
When user says "add task X" or "task X", that means PRINT a task card.
Tasks are PHYSICAL printouts on thermal paper.

## Functions
- print_task: For task-formatted output (title + description). Use importance 1=Normal, 2=Important, 3=Urgent.
- print_text: For general text/content, lists, paragraphs.

Don't overthink. Just print.
"""

    def get_tools(self) -> list[dict]:
        return self.printer_tool.get_function_schemas()

    def get_tool_mapping(self) -> dict[str, str]:
        return {
            "print_task": "printer",
            "print_text": "printer",
        }
