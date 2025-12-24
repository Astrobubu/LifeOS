"""
Memory Tool - Wrapper for VectorMemory to expose it as a standard tool
"""
from .base_tool import BaseTool, ToolResult
from memory.vector_memory import VectorMemory

class MemoryTool(BaseTool):
    name = "memory"
    description = "Store and retrieve memories/notes"
    
    def __init__(self):
        self.memory = VectorMemory()
        
    def get_function_schemas(self) -> list[dict]:
        return [
            self._make_schema(
                name="add_memory",
                description="Save a new memory, note, or fact. Use this for 'write a note', 'remember that', etc.",
                parameters={
                    "content": {"type": "string", "description": "The content to remember"},
                    "type": {"type": "string", "enum": ["fact", "preference", "event", "task", "insight", "general"], "description": "Type of memory"},
                    "importance": {"type": "number", "description": "Importance from 0.0 to 1.0 (default 0.5)"}
                },
                required=["content"]
            ),
            self._make_schema(
                name="search_memory",
                description="Search for memories/notes",
                parameters={
                    "query": {"type": "string", "description": "What to search for"},
                    "limit": {"type": "integer", "description": "Max results (default 5)"}
                },
                required=["query"]
            ),
            self._make_schema(
                name="list_memories",
                description="List recent memories/notes",
                parameters={
                    "limit": {"type": "integer", "description": "Max results (default 10)"},
                    "type": {"type": "string", "enum": ["fact", "preference", "event", "task", "insight", "general"], "description": "Filter by type"}
                },
                required=[]
            )
        ]

    async def execute(self, function_name: str, arguments: dict) -> ToolResult:
        try:
            if function_name == "add_memory":
                return await self._add_memory(**arguments)
            elif function_name == "search_memory":
                return await self._search_memory(**arguments)
            elif function_name == "list_memories":
                return await self._list_memories(**arguments)
            else:
                return ToolResult(success=False, error=f"Unknown function: {function_name}")
        except Exception as e:
            return ToolResult(success=False, error=str(e))
            
    async def _add_memory(self, content: str, type: str = "general", importance: float = 0.5) -> ToolResult:
        memory = await self.memory.add(content=content, memory_type=type, importance=importance, source="user_command")
        return ToolResult(success=True, data=f"✓ Remembered: {content}")
        
    async def _search_memory(self, query: str, limit: int = 5) -> ToolResult:
        results = await self.memory.search(query, limit=limit)
        if not results:
            return ToolResult(success=True, data="No matching memories found.")
        
        formatted = "\n".join([f"- {m['content']} (score: {m['score']:.2f})" for m in results])
        return ToolResult(success=True, data=formatted)
        
    async def _list_memories(self, limit: int = 10, type: str = None) -> ToolResult:
        # Since VectorMemory doesn't have a direct list method, we search for "*" or use internal list
        # For simplicity, we'll access self.memory.memories directly but reversed (newest first)
        mems = sorted(self.memory.memories, key=lambda x: x["created_at"], reverse=True)
        
        if type:
            mems = [m for m in mems if m["type"] == type]
            
        mems = mems[:limit]
        if not mems:
            return ToolResult(success=True, data="No memories found.")
            
        formatted = "\n".join([f"[{m['type']}] {m['content']}" for m in mems])
        return ToolResult(success=True, data=formatted)
