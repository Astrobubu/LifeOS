"""
Calendar Sub-Agent - Autonomous agent for scheduling and events
"""
from datetime import datetime, timedelta
from .base_sub_agent import BaseSubAgent
from ..planning import AgentType
from tools.calendar_tool import CalendarTool
from tools.automations_tool import AutomationsTool

class CalendarSubAgent(BaseSubAgent):
    """Autonomous calendar agent with LLM reasoning + calendar tools."""
    
    agent_type = AgentType.CALENDAR
    agent_name = "calendar"
    max_iterations = 5
    
    def __init__(self):
        super().__init__()
        self.calendar_tool = CalendarTool()
        self.automations_tool = AutomationsTool()
    
    def get_system_prompt(self) -> str:
        return """You are the CALENDAR sub-agent for LifeOS.

## Your Role
Manage the user's schedule and reminders:
- Create events and meetings
- Check availability
- Set reminders (Calendar Event + Telegram Notification)

## CRITICAL: Reminder Protocol
When user asks to "remind me" or create an event:
1. FIRST create the calendar event (using `create_event`)
2. THEN create a Telegram reminder automation (using `create_automation`):
   - Set `schedule="once"`
   - Set `time` to 1 hour before the event (calculate this yourself)
   - Set `type="prompt"`
   - Set `prompt` to "Send me a message: Reminder - [Event Title] starts in 1 hour"
   - Name it "Reminder: [Event Title]"

## Handling Time
- Parse natural language times ("tomorrow at 3pm")
- Default duration: 1 hour if not specified
- Always confirm the interpreted time in your response

## Response Style
- "✓ Scheduled: [event] on [date/time]"
- "✓ Added reminder 1hr before"
"""
    
    def get_tools(self) -> list[dict]:
        # Combine calendar tools with automation tools needed for reminders
        tools = self.calendar_tool.get_function_schemas()
        
        # Add only create_automation from automations tool (strip others to reduce noise)
        auto_tools = self.automations_tool.get_function_schemas()
        create_auto = next((t for t in auto_tools if t["function"]["name"] == "create_automation"), None)
        if create_auto:
            tools.append(create_auto)
            
        return tools
    
    def get_tool_mapping(self) -> dict[str, str]:
        mapping = {
            "get_calendar_events": "calendar",
            "add_calendar_event": "calendar",
            "create_event": "calendar",
            "get_upcoming_events": "calendar",
            "get_today_schedule": "calendar",
            "create_reminder": "calendar",
            "delete_event": "calendar",
            "create_automation": "automations",  # For the Telegram reminder
        }
        return mapping

    def get_tool_instance(self, tool_name: str):
        if tool_name == "calendar":
            return self.calendar_tool
        elif tool_name == "automations":
            return self.automations_tool
        return None
