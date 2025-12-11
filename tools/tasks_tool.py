import json
import uuid
from datetime import datetime
from typing import Optional
from difflib import SequenceMatcher
from config.settings import settings
from .base_tool import BaseTool, ToolResult


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
    
    def _ensure_file(self):
        """Ensure tasks file exists"""
        if not self.tasks_file.exists():
            self._save_tasks([])
    
    def _load_tasks(self) -> list[dict]:
        """Load tasks from file"""
        if self.tasks_file.exists():
            with open(self.tasks_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return []
    
    def _save_tasks(self, tasks: list[dict]):
        """Save tasks to file"""
        with open(self.tasks_file, "w", encoding="utf-8") as f:
            json.dump(tasks, f, indent=2, ensure_ascii=False)
    
    def get_function_schemas(self) -> list[dict]:
        return [
            self._make_schema(
                name="add_task",
                description="Add a new task",
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
            )
        ]
    
    async def execute(self, function_name: str, arguments: dict) -> ToolResult:
        try:
            if function_name == "add_task":
                return await self._add_task(**arguments)
            elif function_name == "complete_task":
                return await self._complete_task(**arguments)
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
        project: str = None
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
            "created_at": datetime.now().isoformat(),
            "completed_at": None
        }
        
        tasks.append(task)
        self._save_tasks(tasks)
        
        return ToolResult(success=True, data={
            "message": f"Task added: {title}",
            "task_id": task["id"]
        })
    
    async def _complete_task(self, task_id: str) -> ToolResult:
        tasks = self._load_tasks()
        
        task = fuzzy_find_task(task_id, tasks)
        if task:
            task["status"] = "completed"
            task["completed_at"] = datetime.now().isoformat()
            self._save_tasks(tasks)
            return ToolResult(success=True, data=f"Task '{task['title']}' marked as completed")
        
        pending = [t for t in tasks if t["status"] == "pending"]
        hint = f" Pending tasks: {', '.join(t['title'][:30] for t in pending[:3])}" if pending else ""
        return ToolResult(success=False, error=f"Task '{task_id}' not found.{hint}")
    
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
            return ToolResult(success=True, data=f"Task '{task['title']}' updated")
        
        return ToolResult(success=False, error=f"Task '{task_id}' not found")
    
    async def _get_task(self, task_id: str) -> ToolResult:
        tasks = self._load_tasks()
        
        task = fuzzy_find_task(task_id, tasks)
        if task:
            return ToolResult(success=True, data=task)
        
        return ToolResult(success=False, error=f"Task '{task_id}' not found")
