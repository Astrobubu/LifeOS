"""
Notes Sub-Agent - Autonomous agent for note-taking and documents
"""
from .base_sub_agent import BaseSubAgent
from ..planning import AgentType
from tools.memory_tool import MemoryTool  # Switched from NotesTool


class NotesSubAgent(BaseSubAgent):
    """Autonomous notes agent - NOW REDIRECTS TO MEMORY."""
    
    agent_type = AgentType.NOTES
    agent_name = "notes"
    max_iterations = 5
    
    def __init__(self):
        super().__init__()
        self.memory_tool = MemoryTool()  # Use memory tool
    
    def get_system_prompt(self) -> str:
        return """You are the NOTES sub-agent for LifeOS (Deprecated).

## CRITICAL CHANGE
The "Notes" system has been merged into "Memory".
You are now just a wrapper for the Memory system.

## Your Role
- "Write a note" → Add to memory
- "Read notes" → Search/List memory
- "Update note" → (Explain that notes are immutable memories now, add new version)

## Response Style
- "✓ Saved to memory: [content]"
"""
    
    def get_tools(self) -> list[dict]:
        return self.memory_tool.get_function_schemas()
    
    def get_tool_mapping(self) -> dict[str, str]:
        return {
            "add_memory": "memory",
            "search_memory": "memory",
            "list_memories": "memory",
        }
    
    def _extract_data_from_result(self, function_name: str, result) -> dict:
        data = {}
        if result.success and function_name == "list_memories":
            data["memories"] = result.data
        return data
