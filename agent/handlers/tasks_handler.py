"""
Tasks Handler - Specialized handler for tasks, todos, and reminders
"""
from .base_handler import BaseHandler
from tools.tasks_tool import TasksTool


class TasksHandler(BaseHandler):
    """Handler for task management operations"""
    
    handler_name = "tasks"
    
    def __init__(self):
        super().__init__()
        self.tasks_tool = TasksTool()
    
    def get_system_prompt(self) -> str:
        return """You are LifeOS Tasks Assistant, specialized in task and reminder management.

## Your Role
- Add new tasks and reminders
- Track pending and overdue items
- Mark tasks as complete
- Manage task priorities and due dates

## Task Guidelines
- Tasks can have optional due dates and priorities
- Reminders are tasks with specific times
- Projects group related tasks together

## Response Style
- Be concise: "✓ Added: [task title]"
- For listings, use clean formatting
- Highlight overdue items when relevant
"""
    
    def get_tools(self) -> list[dict]:
        return self.tasks_tool.get_function_schemas()
    
    def get_tool_mapping(self) -> dict:
        return {
            "add_task": "tasks",
            "add_tasks": "tasks",
            "update_task": "tasks",
            "list_tasks": "tasks",
            "complete_task": "tasks",
            "complete_tasks": "tasks",
            "delete_task": "tasks",
            "get_task": "tasks",
        }
    
    async def get_domain_context(self, user_message: str) -> str:
        """Load current task state"""
        try:
            # Get pending tasks
            pending_result = await self.tasks_tool.execute("list_tasks", {"status": "pending"})
            
            if pending_result.success:
                return f"""CURRENT TASKS:
{pending_result.data if pending_result.data else "No pending tasks"}

When adding tasks, extract the key action clearly.
When listing, show status and any due dates."""
            else:
                return "Unable to load tasks."
                
        except Exception as e:
            return f"Error loading tasks: {str(e)}"
