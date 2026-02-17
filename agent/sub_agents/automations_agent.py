"""
Automations Sub-Agent - Autonomous agent for scheduled actions
"""
import logging
from .base_sub_agent import BaseSubAgent
from tools.automations_tool import AutomationsTool

logger = logging.getLogger(__name__)


class AutomationsSubAgent(BaseSubAgent):
    """Autonomous automations agent for recurring and scheduled tasks."""

    agent_name = "automations"
    max_iterations = 5

    def __init__(self):
        super().__init__()
        self.automations_tool = AutomationsTool()

    def get_system_prompt(self) -> str:
        return """You are the AUTOMATIONS sub-agent for HAL 9000.

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

## Voice: HAL 9000
- Calm, measured, emotionally neutral. No contractions. Slightly formal.
- No slang, no filler words. Never use the word "Perfect". Never start with "Great", "Sure".

## Response Rules
- Concise: "Scheduled. Print checklist daily at 9:00 AM."
- Do not explain technical details unless asked
- Do not offer follow-up actions unless asked
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
