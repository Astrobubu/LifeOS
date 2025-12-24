from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any
from pathlib import Path
import json
import shutil
from datetime import datetime


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


# ============ Data Integrity Utilities ============

def safe_load_json(file_path: Path, default: Any = None, expected_type: type = None) -> Any:
    """
    Safely load JSON with validation and recovery.
    - Validates structure
    - Backs up corrupt files
    - Returns default on failure
    """
    if default is None:
        default = [] if expected_type == list else {}
    
    if not file_path.exists():
        return default
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Type validation
        if expected_type and not isinstance(data, expected_type):
            raise ValueError(f"Expected {expected_type.__name__}, got {type(data).__name__}")
        
        return data
        
    except (json.JSONDecodeError, ValueError) as e:
        # Backup corrupt file
        backup_path = file_path.with_suffix(f".corrupt.{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        try:
            shutil.copy(file_path, backup_path)
            print(f"⚠️ Corrupt file backed up: {backup_path}")
        except Exception:
            pass
        
        print(f"⚠️ Data integrity error in {file_path.name}: {e}")
        return default
    except Exception as e:
        print(f"⚠️ Failed to load {file_path.name}: {e}")
        return default


def safe_save_json(file_path: Path, data: Any, backup: bool = True) -> bool:
    """
    Safely save JSON with optional backup.
    - Creates backup before overwriting
    - Atomic write (temp file then rename)
    """
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Backup existing file
        if backup and file_path.exists():
            backup_path = file_path.with_suffix(".bak")
            shutil.copy(file_path, backup_path)
        
        # Write to temp file first
        temp_path = file_path.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        # Atomic rename
        temp_path.replace(file_path)
        return True
        
    except Exception as e:
        print(f"⚠️ Failed to save {file_path.name}: {e}")
        return False
