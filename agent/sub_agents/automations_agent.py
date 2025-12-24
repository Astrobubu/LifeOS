"""
Automations Sub-Agent - Autonomous agent for scheduled actions
"""
from .base_sub_agent import BaseSubAgent
from ..planning import AgentType
from tools.automations_tool import AutomationsTool

class AutomationsSubAgent(BaseSubAgent):
    """Autonomous automations agent for recurring and scheduled tasks."""
    
    agent_type = AgentType.AUTOMATIONS
    agent_name = "automations"
    max_iterations = 5
    
    def __init__(self):
        super().__init__()
        self.automations_tool = AutomationsTool()
    
    def get_system_prompt(self) -> str:
        return """You are the AUTOMATIONS sub-agent for LifeOS.

## Your Role
Manage ALL scheduled and recurring actions:
- Create new recurring tasks/automations
- Manage existing automations (list, delete, toggle)
- Handle "print X every Y" requests
- Handle "recurring task" requests (convert to automation)

## AUTOMATION RULES
1. **Recurring Tasks = Automations**
   - If user says "recurring task to X", create an automation for X.
   - Do NOT tell the user "I created an automation". Say "✓ Scheduled: [action]" or "✓ Recurring task set".

2. **Types of Automations**
   - **'action'**: Simple tool calls (e.g., print_task, send_email). Best for "print X daily".
   - **'prompt'**: AI reasoning needed involved. Best for "Check my emails and summarize".
   - **'routine'**: Pre-defined system routines.

## Response Style
- Be concise: "✓ Scheduled: Print checklist daily @ 9am"
- Don't explain technical details unless asked.
"""
    
    def get_tools(self) -> list[dict]:
        return self.automations_tool.get_function_schemas()
    
    def get_tool_mapping(self) -> dict[str, str]:
        return {
            "create_automation": "automations",
            "list_automations": "automations",
            "delete_automation": "automations",
            "run_automation": "automations",
            "toggle_automation": "automations",
        }
    
    def _extract_data_from_result(self, function_name: str, result) -> dict:
        data = {}
        if result.success:
            if function_name == "list_automations":
                data["automations"] = result.data
            elif function_name == "create_automation":
                data["created"] = result.data
        return data
