"""
Memory Sub-Agent - Autonomous agent for notes and memories
"""
from .base_sub_agent import BaseSubAgent
from ..planning import AgentType
from tools.memory_tool import MemoryTool

class MemorySubAgent(BaseSubAgent):
    """Autonomous memory agent for storage and retrieval."""
    
    agent_type = AgentType.MEMORY
    agent_name = "memory"
    max_iterations = 3
    
    def __init__(self):
        super().__init__()
        self.memory_tool = MemoryTool()
    
    def get_system_prompt(self) -> str:
        return """You are the MEMORY sub-agent for LifeOS.

## Your Role
Manage the user's long-term memory and notes:
- Store important facts, preferences, and events
- Write "notes" (which are just text memories)
- Retrieve information when asked

## MAPPING RULES
1. **Notes = Memories**
   - User says "Write a note about X" → Add memory about X
   - User says "Draft a note" → Add memory (type: general or insight)
   
2. **Remembering**
   - User says "Remember that..." → Add memory
   - User says "Don't forget..." → Add memory

3. **Retrieving**
   - User says "What did I say about..." → Search memory
   - User says "Show my notes" → List memories

## Types
- **fact**: Solid info (e.g., "Door code is 1234")
- **preference**: Likes/dislikes (e.g., "I hate mushrooms")
- **event**: Things that happened
- **insight**: Ideas or thoughts
- **general**: Everything else

## Response Style
- Be confirming: "✓ Notes saved" or "✓ Remembered"
- When listing, use bullet points
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
