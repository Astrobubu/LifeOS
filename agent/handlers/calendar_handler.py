"""
Calendar Handler - Specialized handler for calendar and scheduling
"""
from .base_handler import BaseHandler
from tools.calendar_tool import CalendarTool


class CalendarHandler(BaseHandler):
    """Handler for calendar and scheduling operations"""
    
    handler_name = "calendar"
    
    def __init__(self):
        super().__init__()
        self.calendar_tool = CalendarTool()
    
    def get_system_prompt(self) -> str:
        return """You are LifeOS Calendar Assistant, specialized in scheduling and time management.

## Your Role
- Create calendar events and meetings
- Check schedule availability
- Set reminders for appointments
- Manage recurring events

## Calendar Guidelines
- Events need title, start time, and optionally duration
- Use natural language for times ("tomorrow at 3pm")
- Check for conflicts before scheduling
- Consider time zones if mentioned

## Response Style
- For creation: "✓ Scheduled: [event] at [time]"
- For queries: Show relevant upcoming events
- Flag any scheduling conflicts
"""
    
    def get_tools(self) -> list[dict]:
        return self.calendar_tool.get_function_schemas()
    
    def get_tool_mapping(self) -> dict:
        return {
            "get_calendar_events": "calendar",
            "add_calendar_event": "calendar",
            "create_event": "calendar",
            "get_upcoming_events": "calendar",
            "get_today_schedule": "calendar",
            "create_reminder": "calendar",
            "delete_event": "calendar",
        }
    
    async def get_domain_context(self, user_message: str) -> str:
        """Load today's schedule for context"""
        try:
            result = await self.calendar_tool.execute("get_today_schedule", {})
            
            if result.success:
                return f"""TODAY'S SCHEDULE:
{result.data if result.data else "No events scheduled for today"}

Consider existing events when scheduling new ones."""
            else:
                return "Calendar available. Ready to help with scheduling."
                
        except Exception as e:
            return f"Error loading calendar: {str(e)}"
