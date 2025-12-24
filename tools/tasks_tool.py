import json
import uuid
from datetime import datetime, timedelta
from typing import Optional
from difflib import SequenceMatcher
from config.settings import settings
from .base_tool import BaseTool, ToolResult, safe_load_json, safe_save_json


def fuzzy_find_task(query: str, tasks: list[dict]) -> dict | None:
    """Find a task by ID or fuzzy title match"""
    query_lower = query.lower().strip()
    
    # Try exact ID match first
    for task in tasks:
        if task["id"] == query or task["id"].startswith(query_lower):
            return task
    
    # Try fuzzy title match
    best_match = None
    best_score = 0.4  # Minimum threshold
    
    for task in tasks:
        title_lower = task["title"].lower()
        
        # Exact title match
        if query_lower == title_lower:
            return task
        
        # Contains match
        if query_lower in title_lower or title_lower in query_lower:
            return task
        
        # Word overlap
        query_words = set(query_lower.split())
        title_words = set(title_lower.split())
        overlap = len(query_words & title_words)
        if overlap > 0:
            score = overlap / max(len(query_words), len(title_words))
            if score > best_score:
                best_score = score
                best_match = task
                continue
        
        # Sequence similarity
        ratio = SequenceMatcher(None, query_lower, title_lower).ratio()
        if ratio > best_score:
            best_score = ratio
            best_match = task
    
    return best_match


class TasksTool(BaseTool):
    name = "tasks"
    description = "Manage tasks and to-do items"
    
    def __init__(self):
        self.tasks_file = settings.TASKS_DIR / "tasks.json"
        self._ensure_file()
        # Process recurring tasks on init
        self._process_recurring_tasks()
    
    def _ensure_file(self):
        """Ensure tasks file exists"""
        if not self.tasks_file.exists():
            self._save_tasks([])
    
    def _load_tasks(self) -> list[dict]:
        """Load tasks with data integrity check"""
        return safe_load_json(self.tasks_file, default=[], expected_type=list)
    
    def _save_tasks(self, tasks: list[dict]):
        """Save tasks with backup"""
        safe_save_json(self.tasks_file, tasks, backup=True)
    
    def _process_recurring_tasks(self):
        """Check and create instances of recurring tasks"""
        tasks = self._load_tasks()
        today = datetime.now().date()
        new_tasks = []
        
        for task in tasks:
            if task.get("recurrence") and task["status"] == "completed":
                # Check if we need to create a new instance
                last_completed = task.get("completed_at")
                if last_completed:
                    last_date = datetime.fromisoformat(last_completed).date()
                    recurrence = task["recurrence"]
                    
                    should_create = False
                    if recurrence == "daily" and (today - last_date).days >= 1:
                        should_create = True
                    elif recurrence == "weekly" and (today - last_date).days >= 7:
                        should_create = True
                    elif recurrence == "monthly" and (today - last_date).days >= 30:
                        should_create = True
                    
                    if should_create:
                        new_task = {
                            "id": str(uuid.uuid4())[:8],
                            "title": task["title"],
                            "status": "pending",
                            "priority": task.get("priority", "medium"),
                            "due_date": today.isoformat(),
                            "tags": task.get("tags", []),
                            "project": task.get("project"),
                            "recurrence": recurrence,
                            "created_at": datetime.now().isoformat(),
                            "completed_at": None
                        }
                        new_tasks.append(new_task)
        
        if new_tasks:
            tasks.extend(new_tasks)
            self._save_tasks(tasks)
    
    def get_function_schemas(self) -> list[dict]:
        return [
            self._make_schema(
                name="add_task",
                description="Add a new task (one-time only). For recurring tasks, use the Automations agent.",
                parameters={
                    "title": {"type": "string", "description": "Task title/description"},
                    "priority": {"type": "string", "enum": ["low", "medium", "high"], "description": "Task priority"},
                    "due_date": {"type": "string", "description": "Due date in YYYY-MM-DD format"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags for the task"},
                    "project": {"type": "string", "description": "Project this task belongs to"}
                },
                required=["title"]
            ),
            self._make_schema(
                name="complete_task",
                description="Mark a task as completed",
                parameters={
                    "task_id": {"type": "string", "description": "ID of the task to complete"}
                },
                required=["task_id"]
            ),
            self._make_schema(
                name="delete_task",
                description="Delete a task",
                parameters={
                    "task_id": {"type": "string", "description": "ID of the task to delete"}
                },
                required=["task_id"]
            ),
            self._make_schema(
                name="list_tasks",
                description="List tasks with optional filters",
                parameters={
                    "status": {"type": "string", "enum": ["pending", "completed", "all"], "description": "Filter by status"},
                    "priority": {"type": "string", "enum": ["low", "medium", "high"], "description": "Filter by priority"},
                    "project": {"type": "string", "description": "Filter by project"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Filter by tags"}
                },
                required=[]
            ),
            self._make_schema(
                name="update_task",
                description="Update a task's details",
                parameters={
                    "task_id": {"type": "string", "description": "ID of the task to update"},
                    "title": {"type": "string", "description": "New title"},
                    "priority": {"type": "string", "enum": ["low", "medium", "high"], "description": "New priority"},
                    "due_date": {"type": "string", "description": "New due date"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "New tags"},
                    "project": {"type": "string", "description": "New project"}
                },
                required=["task_id"]
            ),
            self._make_schema(
                name="get_task",
                description="Get details of a specific task",
                parameters={
                    "task_id": {"type": "string", "description": "ID of the task"}
                },
                required=["task_id"]
            ),
            self._make_schema(
                name="add_tasks",
                description="Add multiple tasks at once (batch operation)",
                parameters={
                    "tasks": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "priority": {"type": "string", "enum": ["low", "medium", "high"]},
                                "due_date": {"type": "string"},
                                "project": {"type": "string"}
                            },
                            "required": ["title"]
                        },
                        "description": "Array of task objects to add"
                    }
                },
                required=["tasks"]
            ),
            self._make_schema(
                name="complete_tasks",
                description="Complete multiple tasks at once (batch operation)",
                parameters={
                    "task_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Array of task IDs to complete"
                    }
                },
                required=["task_ids"]
            )
        ]
    
    async def execute(self, function_name: str, arguments: dict) -> ToolResult:
        try:
            if function_name == "add_task":
                return await self._add_task(**arguments)
            elif function_name == "add_tasks":
                return await self._add_tasks(**arguments)
            elif function_name == "complete_task":
                return await self._complete_task(**arguments)
            elif function_name == "complete_tasks":
                return await self._complete_tasks(**arguments)
            elif function_name == "delete_task":
                return await self._delete_task(**arguments)
            elif function_name == "list_tasks":
                return await self._list_tasks(**arguments)
            elif function_name == "update_task":
                return await self._update_task(**arguments)
            elif function_name == "get_task":
                return await self._get_task(**arguments)
            else:
                return ToolResult(success=False, error=f"Unknown function: {function_name}")
        except Exception as e:
            return ToolResult(success=False, error=str(e))
    
    async def _add_task(
        self,
        title: str,
        priority: str = "medium",
        due_date: str = None,
        tags: list = None,
        project: str = None,
        recurrence: str = None
    ) -> ToolResult:
        tasks = self._load_tasks()
        
        task = {
            "id": str(uuid.uuid4())[:8],
            "title": title,
            "status": "pending",
            "priority": priority,
            "due_date": due_date,
            "tags": tags or [],
            "project": project,
            "recurrence": recurrence,
            "created_at": datetime.now().isoformat(),
            "completed_at": None
        }
        
        tasks.append(task)
        self._save_tasks(tasks)
        
        recurrence_text = f" (repeats {recurrence})" if recurrence else ""
        return ToolResult(success=True, data=f"✓ Added: {title}{recurrence_text}")
    
    async def _complete_task(self, task_id: str) -> ToolResult:
        tasks = self._load_tasks()
        
        task = fuzzy_find_task(task_id, tasks)
        if task:
            task["status"] = "completed"
            task["completed_at"] = datetime.now().isoformat()
            self._save_tasks(tasks)
            return ToolResult(success=True, data=f"✓ Done: {task['title']}")
        
        pending = [t for t in tasks if t["status"] == "pending"]
        hint = f" Pending: {', '.join(t['title'][:20] for t in pending[:3])}" if pending else ""
        return ToolResult(success=False, error=f"Not found: {task_id}.{hint}")
    
    async def _delete_task(self, task_id: str) -> ToolResult:
        tasks = self._load_tasks()
        
        task = fuzzy_find_task(task_id, tasks)
        if task:
            tasks.remove(task)
            self._save_tasks(tasks)
            return ToolResult(success=True, data=f"Task '{task['title']}' deleted")
        
        hint = f" Available: {', '.join(t['title'][:30] for t in tasks[:3])}" if tasks else ""
        return ToolResult(success=False, error=f"Task '{task_id}' not found.{hint}")
    
    async def _list_tasks(
        self,
        status: str = "pending",
        priority: str = None,
        project: str = None,
        tags: list = None
    ) -> ToolResult:
        tasks = self._load_tasks()
        filtered = []
        
        for task in tasks:
            # Status filter
            if status != "all" and task["status"] != status:
                continue
            
            # Priority filter
            if priority and task.get("priority") != priority:
                continue
            
            # Project filter
            if project and task.get("project") != project:
                continue
            
            # Tags filter
            if tags:
                task_tags = set(task.get("tags", []))
                if not any(t in task_tags for t in tags):
                    continue
            
            filtered.append(task)
        
        # Sort by priority and due date
        priority_order = {"high": 0, "medium": 1, "low": 2}
        filtered.sort(key=lambda t: (
            priority_order.get(t.get("priority", "medium"), 1),
            t.get("due_date") or "9999-99-99"
        ))
        
        return ToolResult(success=True, data=filtered)
    
    async def _update_task(self, task_id: str, **kwargs) -> ToolResult:
        tasks = self._load_tasks()
        
        task = fuzzy_find_task(task_id, tasks)
        if task:
            for key, value in kwargs.items():
                if key != "task_id" and value is not None:
                    task[key] = value
            self._save_tasks(tasks)
            return ToolResult(success=True, data=f"✓ Updated: {task['title']}")
        
        return ToolResult(success=False, error=f"Not found: {task_id}")
    
    async def _get_task(self, task_id: str) -> ToolResult:
        tasks = self._load_tasks()
        
        task = fuzzy_find_task(task_id, tasks)
        if task:
            return ToolResult(success=True, data=task)
        
        return ToolResult(success=False, error=f"Not found: {task_id}")
    
    async def _add_tasks(self, tasks: list[dict]) -> ToolResult:
        """Add multiple tasks at once (batch)"""
        added = []
        for task_data in tasks:
            result = await self._add_task(
                title=task_data.get("title", "Untitled"),
                priority=task_data.get("priority", "medium"),
                due_date=task_data.get("due_date"),
                tags=task_data.get("tags"),
                project=task_data.get("project")
            )
            if result.success:
                added.append(task_data.get("title", "task"))
        return ToolResult(success=True, data=f"✓ Added {len(added)} tasks")
    
    async def _complete_tasks(self, task_ids: list[str]) -> ToolResult:
        """Complete multiple tasks at once (batch)"""
        completed = []
        for tid in task_ids:
            result = await self._complete_task(tid)
            if result.success:
                completed.append(tid)
        return ToolResult(success=True, data=f"✓ Completed {len(completed)} tasks")
