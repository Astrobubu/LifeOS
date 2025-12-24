"""
Hybrid Automations System
- Scheduled Actions (direct tool calls - no LLM cost)
- Scheduled Prompts (AI-powered - uses LLM)
- Pre-built Routines (email check, print agenda, task summary)
"""
import json
import uuid
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path

from config.settings import settings
from .base_tool import BaseTool, ToolResult, safe_load_json, safe_save_json


class AutomationsTool(BaseTool):
    name = "automations"
    description = "Manage scheduled automations and routines"
    
    def __init__(self):
        self.automations_file = settings.STORAGE_DIR / "automations" / "automations.json"
        self._ensure_file()
    
    def _ensure_file(self):
        """Ensure automations file exists"""
        self.automations_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.automations_file.exists():
            self._save_automations([])
    
    def _load_automations(self) -> list[dict]:
        """Load automations with data integrity check"""
        return safe_load_json(self.automations_file, default=[], expected_type=list)
    
    def _save_automations(self, automations: list[dict]):
        """Save automations with backup"""
        safe_save_json(self.automations_file, automations, backup=True)
    
    def get_function_schemas(self) -> list[dict]:
        return [
            self._make_schema(
                name="create_automation",
                description="""Create a scheduled automation. Types:
- 'action': Direct tool call (FREE, no AI) - e.g., print task, send preset email
- 'prompt': AI-powered prompt (uses LLM) - for complex multi-step tasks
- 'routine': Pre-built routine like 'daily_email_check', 'print_agenda', 'task_summary'""",
                parameters={
                    "name": {"type": "string", "description": "Automation name"},
                    "type": {"type": "string", "enum": ["action", "prompt", "routine"], "description": "Type of automation"},
                    "schedule": {"type": "string", "enum": ["hourly", "daily", "weekly", "on_start", "once"], "description": "When to run ('once' requires full ISO datetime in 'time')"},
                    "time": {"type": "string", "description": "Time to run (HH:MM for daily, or ISO datetime for 'once')"},
                    "action_tool": {"type": "string", "description": "For 'action' type: which tool to call (e.g., 'printer', 'gmail')"},
                    "action_function": {"type": "string", "description": "For 'action' type: which function (e.g., 'print_task', 'read_emails')"},
                    "action_args": {"type": "object", "description": "For 'action' type: arguments to pass to the function"},
                    "prompt": {"type": "string", "description": "For 'prompt' type: the prompt to send to AI"},
                    "routine_name": {"type": "string", "enum": ["daily_email_check", "print_agenda", "task_summary", "print_pending_tasks"], "description": "For 'routine' type: which routine"}
                },
                required=["name", "type", "schedule"]
            ),
            self._make_schema(
                name="list_automations",
                description="List all scheduled automations",
                parameters={},
                required=[]
            ),
            self._make_schema(
                name="delete_automation",
                description="Delete an automation",
                parameters={
                    "automation_id": {"type": "string", "description": "ID of automation to delete"}
                },
                required=["automation_id"]
            ),
            self._make_schema(
                name="run_automation",
                description="Manually trigger an automation now",
                parameters={
                    "automation_id": {"type": "string", "description": "ID of automation to run"}
                },
                required=["automation_id"]
            ),
            self._make_schema(
                name="toggle_automation",
                description="Enable or disable an automation",
                parameters={
                    "automation_id": {"type": "string", "description": "ID of automation"},
                    "enabled": {"type": "boolean", "description": "True to enable, False to disable"}
                },
                required=["automation_id", "enabled"]
            )
        ]
    
    async def execute(self, function_name: str, arguments: dict) -> ToolResult:
        try:
            if function_name == "create_automation":
                return await self._create_automation(**arguments)
            elif function_name == "list_automations":
                return await self._list_automations()
            elif function_name == "delete_automation":
                return await self._delete_automation(**arguments)
            elif function_name == "run_automation":
                return await self._run_automation(**arguments)
            elif function_name == "toggle_automation":
                return await self._toggle_automation(**arguments)
            else:
                return ToolResult(success=False, error=f"Unknown function: {function_name}")
        except Exception as e:
            return ToolResult(success=False, error=str(e))
    
    async def _create_automation(
        self,
        name: str,
        type: str,
        schedule: str,
        time: str = None,
        action_tool: str = None,
        action_function: str = None,
        action_args: dict = None,
        prompt: str = None,
        routine_name: str = None
    ) -> ToolResult:
        automations = self._load_automations()
        
        automation = {
            "id": str(uuid.uuid4())[:8],
            "name": name,
            "type": type,
            "schedule": schedule,
            "time": time,
            "enabled": True,
            "created_at": datetime.now().isoformat(),
            "last_run": None,
            "run_count": 0
        }
        
        # Type-specific fields
        if type == "action":
            if not action_tool or not action_function:
                return ToolResult(success=False, error="Action type requires action_tool and action_function")
            automation["action_tool"] = action_tool
            automation["action_function"] = action_function
            automation["action_args"] = action_args or {}
        elif type == "prompt":
            if not prompt:
                return ToolResult(success=False, error="Prompt type requires a prompt")
            automation["prompt"] = prompt
        elif type == "routine":
            if not routine_name:
                return ToolResult(success=False, error="Routine type requires routine_name")
            automation["routine_name"] = routine_name
        
        automations.append(automation)
        self._save_automations(automations)
        
        return ToolResult(success=True, data=f"✓ Automation created: {name} ({schedule})")
    
    async def _list_automations(self) -> ToolResult:
        automations = self._load_automations()
        
        if not automations:
            return ToolResult(success=True, data="No automations configured")
        
        lines = []
        for a in automations:
            status = "✓" if a["enabled"] else "○"
            time_str = f" @ {a['time']}" if a.get("time") else ""
            type_icon = {"action": "⚡", "prompt": "🤖", "routine": "📋"}.get(a["type"], "•")
            lines.append(f"{status} [{a['id']}] {type_icon} {a['name']} - {a['schedule']}{time_str}")
        
        return ToolResult(success=True, data="\n".join(lines))
    
    async def _delete_automation(self, automation_id: str) -> ToolResult:
        automations = self._load_automations()
        
        for i, a in enumerate(automations):
            if a["id"] == automation_id or a["id"].startswith(automation_id):
                removed = automations.pop(i)
                self._save_automations(automations)
                return ToolResult(success=True, data=f"✓ Deleted: {removed['name']}")
        
        return ToolResult(success=False, error=f"Automation {automation_id} not found")
    
    async def _toggle_automation(self, automation_id: str, enabled: bool) -> ToolResult:
        automations = self._load_automations()
        
        for a in automations:
            if a["id"] == automation_id or a["id"].startswith(automation_id):
                a["enabled"] = enabled
                self._save_automations(automations)
                status = "enabled" if enabled else "disabled"
                return ToolResult(success=True, data=f"✓ {a['name']} {status}")
        
        return ToolResult(success=False, error=f"Automation {automation_id} not found")
    
    async def _run_automation(self, automation_id: str) -> ToolResult:
        """Run an automation immediately"""
        automations = self._load_automations()
        
        for a in automations:
            if a["id"] == automation_id or a["id"].startswith(automation_id):
                result = await self._execute_automation(a)
                
                # Update run stats
                a["last_run"] = datetime.now().isoformat()
                a["run_count"] = a.get("run_count", 0) + 1
                self._save_automations(automations)
                
                return result
        
        return ToolResult(success=False, error=f"Automation {automation_id} not found")
    
    async def _execute_automation(self, automation: dict) -> ToolResult:
        """Execute a single automation"""
        auto_type = automation["type"]
        
        if auto_type == "action":
            # Direct tool call - no LLM
            return await self._execute_action(automation)
        elif auto_type == "prompt":
            # AI-powered - needs LLM (return prompt for agent to process)
            return ToolResult(success=True, data={
                "type": "prompt",
                "prompt": automation["prompt"],
                "automation_name": automation["name"]
            })
        elif auto_type == "routine":
            # Pre-built routine
            return await self._execute_routine(automation["routine_name"])
        
        return ToolResult(success=False, error=f"Unknown automation type: {auto_type}")
    
    async def _execute_action(self, automation: dict) -> ToolResult:
        """Execute a direct tool action (no LLM cost)"""
        from . import get_tool
        
        tool_name = automation["action_tool"]
        function_name = automation["action_function"]
        args = automation.get("action_args", {})
        
        try:
            tool = get_tool(tool_name)
            result = await tool.execute(function_name, args)
            return ToolResult(success=True, data=f"✓ {automation['name']}: {result.data}")
        except Exception as e:
            return ToolResult(success=False, error=f"Action failed: {e}")
    
    async def _execute_routine(self, routine_name: str) -> ToolResult:
        """Execute a pre-built routine"""
        from . import get_tool
        
        if routine_name == "daily_email_check":
            gmail = get_tool("gmail")
            result = await gmail.execute("read_emails", {"max_results": 5, "query": "is:unread"})
            if result.success:
                return ToolResult(success=True, data=f"✓ Email check: {len(result.data) if isinstance(result.data, list) else 0} unread")
            return result
        
        elif routine_name == "print_agenda":
            # Get today's calendar and print it
            calendar = get_tool("calendar")
            result = await calendar.execute("get_today_schedule", {})
            if result.success and result.data:
                printer = get_tool("printer")
                # Print a summary
                await printer.execute("print_task", {
                    "task_description": "Today's Agenda",
                    "importance": 2,
                    "style": "handwritten"
                })
                return ToolResult(success=True, data="✓ Printed today's agenda")
            return ToolResult(success=True, data="✓ No events today")
        
        elif routine_name == "task_summary":
            tasks = get_tool("tasks")
            result = await tasks.execute("list_tasks", {"status": "pending"})
            return result
        
        elif routine_name == "print_pending_tasks":
            tasks = get_tool("tasks")
            result = await tasks.execute("list_tasks", {"status": "pending", "limit": 5})
            if result.success:
                printer = get_tool("printer")
                # Print top priority task
                pending = result.data if isinstance(result.data, str) else ""
                if pending and "No tasks" not in pending:
                    await printer.execute("print_task", {
                        "task_description": "Top Tasks",
                        "importance": 2,
                        "style": "handwritten"
                    })
                    return ToolResult(success=True, data="✓ Printed pending tasks")
            return ToolResult(success=True, data="✓ No pending tasks to print")
        
        return ToolResult(success=False, error=f"Unknown routine: {routine_name}")
    
    async def check_and_run_due(self) -> list[ToolResult]:
        """Check all automations and run any that are due. Called by main loop.
        
        Includes catch-up logic: if a daily task hasn't run today and we're 
        past its scheduled time, it will run immediately (even if PC was off).
        """
        automations = self._load_automations()
        results = []
        now = datetime.now()
        
        for a in automations:
            if not a.get("enabled", True):
                continue
            
            should_run = False
            last_run = datetime.fromisoformat(a["last_run"]) if a.get("last_run") else None
            
            if a["schedule"] == "on_start":
                # Only run if never run before
                should_run = last_run is None
            elif a["schedule"] == "hourly":
                if last_run and last_run.tzinfo:
                    last_run = last_run.replace(tzinfo=None)
                should_run = last_run is None or (now - last_run) >= timedelta(hours=1)
            elif a["schedule"] == "daily":
                # Check if it hasn't run today
                if last_run and last_run.tzinfo:
                    last_run = last_run.replace(tzinfo=None)
                ran_today = last_run is not None and last_run.date() == now.date()
                
                if not ran_today:
                    if a.get("time"):
                        # Has specific time - check if we've passed it (catch-up logic)
                        target_hour, target_min = map(int, a["time"].split(":"))
                        current_minutes = now.hour * 60 + now.minute
                        target_minutes = target_hour * 60 + target_min
                        
                        # Run if current time >= scheduled time (catches missed tasks)
                        if current_minutes >= target_minutes:
                            should_run = True
                    else:
                        # No specific time - just run once per day
                        should_run = True

            elif a["schedule"] == "weekly":
                if last_run and last_run.tzinfo:
                    last_run = last_run.replace(tzinfo=None)
                should_run = last_run is None or (now - last_run) >= timedelta(days=7)
            
            elif a["schedule"] == "once":
                # Run once at specific datetime
                if a.get("time"):
                    try:
                        target_dt = datetime.fromisoformat(a["time"])
                        if target_dt.tzinfo:
                            target_dt = target_dt.replace(tzinfo=None)
                        if now >= target_dt:
                            should_run = True
                    except ValueError:
                        pass # Invalid time format
            
            if should_run:
                result = await self._execute_automation(a)
                a["last_run"] = now.isoformat()
                a["run_count"] = a.get("run_count", 0) + 1
                results.append(result)
                
                # Auto-delete "once" automations after success
                if a["schedule"] == "once":
                    a["enabled"] = False # Disable or delete? Disable allows history.
                    # Or maybe delete to keep list clean?
                    # Let's delete it from the next save
                    # We can't modify list while iterating easily, so mark for deletion
                    a["_delete_me"] = True
        
        if results:
            # Filter out deleted one-time automations
            automations = [a for a in automations if not a.get("_delete_me")]
            self._save_automations(automations)
        
        return results
