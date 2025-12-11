from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ToolResult:
    success: bool
    data: Any = None
    error: str = None
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error
        }
    
    def __str__(self) -> str:
        if self.success:
            return f"Success: {self.data}"
        return f"Error: {self.error}"


class BaseTool(ABC):
    """Base class for all tools"""
    
    name: str = "base_tool"
    description: str = "Base tool description"
    
    @abstractmethod
    def get_function_schemas(self) -> list[dict]:
        """Return OpenAI function calling schemas for this tool's functions"""
        pass
    
    @abstractmethod
    async def execute(self, function_name: str, arguments: dict) -> ToolResult:
        """Execute a function with given arguments"""
        pass
    
    def _make_schema(
        self,
        name: str,
        description: str,
        parameters: dict,
        required: list[str] = None
    ) -> dict:
        """Helper to create OpenAI function schema"""
        return {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": {
                    "type": "object",
                    "properties": parameters,
                    "required": required or []
                }
            }
        }
