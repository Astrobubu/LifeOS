"""
Google Calendar Integration
Create events, check schedule, set reminders (via calendar)
"""
from datetime import datetime, timedelta
from typing import Optional
import re

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from config.settings import settings
from .base_tool import BaseTool, ToolResult


SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events'
]

# Default timezone - update this to your timezone
DEFAULT_TIMEZONE = 'Asia/Dubai'  # Change this to your timezone


class CalendarTool(BaseTool):
    name = "calendar"
    description = "Manage Google Calendar - create events, check schedule, set reminders"
    
    def __init__(self):
        self.creds = None
        self.service = None
        self.token_path = settings.BASE_DIR / "calendar_token.json"
        self.credentials_path = settings.BASE_DIR / "credentials.json"
    
    def _authenticate(self) -> bool:
        """Authenticate with Google Calendar API"""
        try:
            if self.token_path.exists():
                self.creds = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)
            
            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    self.creds.refresh(Request())
                else:
                    if not self.credentials_path.exists():
                        return False
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(self.credentials_path), SCOPES
                    )
                    self.creds = flow.run_local_server(port=0)
                
                with open(self.token_path, 'w') as token:
                    token.write(self.creds.to_json())
            
            self.service = build('calendar', 'v3', credentials=self.creds)
            return True
        except Exception as e:
            print(f"Calendar auth error: {e}")
            return False
    
    def get_function_schemas(self) -> list[dict]:
        return [
            self._make_schema(
                name="create_event",
                description="Create a calendar event or reminder",
                parameters={
                    "title": {"type": "string", "description": "Event title"},
                    "start_time": {"type": "string", "description": "Start time (ISO format or natural like '2024-01-15 14:00')"},
                    "end_time": {"type": "string", "description": "End time (optional, defaults to 1 hour after start)"},
                    "description": {"type": "string", "description": "Event description"},
                    "reminder_minutes": {"type": "integer", "description": "Reminder before event in minutes (default 30)"}
                },
                required=["title", "start_time"]
            ),
            self._make_schema(
                name="get_upcoming_events",
                description="Get upcoming calendar events",
                parameters={
                    "days": {"type": "integer", "description": "Number of days to look ahead (default 7)"},
                    "max_results": {"type": "integer", "description": "Maximum events to return (default 10)"}
                },
                required=[]
            ),
            self._make_schema(
                name="get_today_schedule",
                description="Get today's schedule",
                parameters={},
                required=[]
            ),
            self._make_schema(
                name="delete_event",
                description="Delete a calendar event",
                parameters={
                    "event_id": {"type": "string", "description": "Event ID to delete"}
                },
                required=["event_id"]
            ),
            self._make_schema(
                name="create_reminder",
                description="Create a reminder (calendar event with notification)",
                parameters={
                    "title": {"type": "string", "description": "What to remind about"},
                    "when": {"type": "string", "description": "When to remind (ISO format or natural)"},
                },
                required=["title", "when"]
            )
        ]
    
    async def execute(self, function_name: str, arguments: dict) -> ToolResult:
        if not self._authenticate():
            return ToolResult(
                success=False,
                error="Calendar not configured. Need credentials.json with Calendar API enabled."
            )
        
        try:
            if function_name == "create_event":
                return await self._create_event(**arguments)
            elif function_name == "get_upcoming_events":
                return await self._get_upcoming(**arguments)
            elif function_name == "get_today_schedule":
                return await self._get_today()
            elif function_name == "delete_event":
                return await self._delete_event(**arguments)
            elif function_name == "create_reminder":
                return await self._create_reminder(**arguments)
            else:
                return ToolResult(success=False, error=f"Unknown function: {function_name}")
        except Exception as e:
            return ToolResult(success=False, error=str(e))
    
    def _parse_datetime(self, dt_str: str) -> datetime:
        """Parse various datetime formats"""
        # Try ISO format first
        for fmt in [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%dT%H:%M",
            "%Y-%m-%d"
        ]:
            try:
                return datetime.strptime(dt_str, fmt)
            except ValueError:
                continue
        
        raise ValueError(f"Could not parse datetime: {dt_str}")
    
    async def _create_event(
        self,
        title: str,
        start_time: str,
        end_time: str = None,
        description: str = "",
        reminder_minutes: int = 30
    ) -> ToolResult:
        try:
            start_dt = self._parse_datetime(start_time)
            
            if end_time:
                end_dt = self._parse_datetime(end_time)
            else:
                end_dt = start_dt + timedelta(hours=1)
            
            event = {
                'summary': title,
                'description': description,
                'start': {
                    'dateTime': start_dt.isoformat(),
                    'timeZone': DEFAULT_TIMEZONE,
                },
                'end': {
                    'dateTime': end_dt.isoformat(),
                    'timeZone': DEFAULT_TIMEZONE,
                },
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'popup', 'minutes': reminder_minutes},
                    ],
                },
            }
            
            created = self.service.events().insert(calendarId='primary', body=event).execute()
            
            return ToolResult(success=True, data={
                "message": f"Event created: {title}",
                "event_id": created['id'],
                "start": start_dt.strftime("%Y-%m-%d %H:%M"),
                "link": created.get('htmlLink', '')
            })
        except Exception as e:
            return ToolResult(success=False, error=str(e))
    
    async def _get_upcoming(self, days: int = 7, max_results: int = 10) -> ToolResult:
        now = datetime.utcnow()
        time_min = now.isoformat() + 'Z'
        time_max = (now + timedelta(days=days)).isoformat() + 'Z'
        
        events_result = self.service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        if not events:
            return ToolResult(success=True, data="No upcoming events")
        
        lines = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            try:
                dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                date_str = dt.strftime("%a %b %d, %H:%M")
            except:
                date_str = start
            
            lines.append(f"[{event['id'][:8]}] {date_str}: {event['summary']}")
        
        return ToolResult(success=True, data="\n".join(lines))
    
    async def _get_today(self) -> ToolResult:
        now = datetime.utcnow()
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)
        
        events_result = self.service.events().list(
            calendarId='primary',
            timeMin=start_of_day.isoformat() + 'Z',
            timeMax=end_of_day.isoformat() + 'Z',
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        if not events:
            return ToolResult(success=True, data="No events today")
        
        lines = ["Today's Schedule:"]
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            try:
                dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                time_str = dt.strftime("%H:%M")
            except:
                time_str = "All day"
            
            lines.append(f"  {time_str} - {event['summary']}")
        
        return ToolResult(success=True, data="\n".join(lines))
    
    async def _delete_event(self, event_id: str) -> ToolResult:
        try:
            self.service.events().delete(calendarId='primary', eventId=event_id).execute()
            return ToolResult(success=True, data="Event deleted")
        except Exception as e:
            return ToolResult(success=False, error=str(e))
    
    async def _create_reminder(self, title: str, when: str) -> ToolResult:
        """Create a reminder as a short calendar event with popup notification"""
        try:
            remind_dt = self._parse_datetime(when)
            
            event = {
                'summary': f"🔔 {title}",
                'start': {
                    'dateTime': remind_dt.isoformat(),
                    'timeZone': DEFAULT_TIMEZONE,
                },
                'end': {
                    'dateTime': (remind_dt + timedelta(minutes=15)).isoformat(),
                    'timeZone': DEFAULT_TIMEZONE,
                },
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'popup', 'minutes': 0},  # At time of event
                        {'method': 'popup', 'minutes': 5},  # 5 min before
                    ],
                },
            }
            
            created = self.service.events().insert(calendarId='primary', body=event).execute()
            
            return ToolResult(success=True, data={
                "message": f"Reminder set: {title}",
                "when": remind_dt.strftime("%Y-%m-%d %H:%M"),
                "event_id": created['id']
            })
        except Exception as e:
            return ToolResult(success=False, error=str(e))
