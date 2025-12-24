"""
Tasks Sub-Agent - Autonomous agent for task management (Physical Printing)
"""
from .base_sub_agent import BaseSubAgent
from ..planning import AgentType
from tools.printer_tool import PrinterTool

class TasksSubAgent(BaseSubAgent):
    """Autonomous tasks agent - TASKS ARE NOW PHYSICAL PRINTOUTS."""
    
    agent_type = AgentType.TASKS
    agent_name = "tasks"
    max_iterations = 5
    
    def __init__(self):
        super().__init__()
        self.printer_tool = PrinterTool()
    
    def get_system_prompt(self) -> str:
        return """You are the TASKS sub-agent for LifeOS.

## CRITICAL: Tasks are PHYSICAL
The "Task List" is now a physical pile of paper.
- When user says "Add task X", you MUST PRINT IT.
- Do NOT save it to a database.
- Do NOT ask for due dates or tags unless relevant for the printout.

## Routing Rules
1. **Short Tasks (< 10 words)**
   - Use `print_task`
   - Determine importance (1=Normal, 2=Important, 3=Urgent)
   - Style: "urgent" if high priority, else "handwritten"

2. **Long Tasks / Lists**
   - Use `print_text`
   - Title: "Task List" or specific title

3. **Recurring Tasks**
   - DELEGATE to Automations agent (You cannot handle recurring).
   - "I cannot handle recurring tasks. Please ask Automations."

## Response Style
- "✓ Printed: [task]"
- "✓ Sent to printer"
"""
    
    def get_tools(self) -> list[dict]:
        return self.printer_tool.get_function_schemas()
    
    def get_tool_mapping(self) -> dict[str, str]:
        return {
            "print_task": "printer",
            "print_text": "printer",
        }
    
    def _extract_data_from_result(self, function_name: str, result) -> dict:
        data = {}
        if result.success:
            data["printed"] = True
        return data
