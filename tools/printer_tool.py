from typing import Dict, Any, List
from tools.base_tool import BaseTool, ToolResult
import sys
import os

# Add project root to path to import printer_control modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from printer_control.print_task import TaskPrinter, PRINTER_NAME
from printer_control.print_text import TextPrinter

class PrinterTool(BaseTool):
    name = "printer"
    description = "Print physical cards and text on thermal printer"
    
    def __init__(self):
        self.task_printer = TaskPrinter(PRINTER_NAME)
        self.text_printer = TextPrinter(PRINTER_NAME)

    def get_function_schemas(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "print_task",
                    "description": "Print a task CARD on thermal printer. Use ONLY for actionable tasks/reminders (max 5 words). Uses handwritten or urgent card style. Example: 'print task buy milk', 'print reminder call mom'",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task_description": {
                                "type": "string",
                                "description": "Short task text (max 5 words)"
                            },
                            "importance": {
                                "type": "integer",
                                "description": "1 (Normal), 2 (Important), 3 (Urgent)",
                                "enum": [1, 2, 3]
                            },
                            "style": {
                                "type": "string",
                                "enum": ["handwritten", "urgent"]
                            }
                        },
                        "required": ["task_description", "importance"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "print_text",
                    "description": "Print long text/paragraphs/notes on thermal printer. Use for ANY text that is NOT a short task - ideas, paragraphs, lists, notes, instructions. Example: 'print this paragraph', 'print out my notes', 'print this text'",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text": {
                                "type": "string",
                                "description": "The text content to print. Can be multiple lines."
                            },
                            "title": {
                                "type": "string",
                                "description": "Optional title/header"
                            }
                        },
                        "required": ["text"]
                    }
                }
            }
        ]

    async def execute(self, function_name: str, arguments: Dict[str, Any]) -> ToolResult:
        if function_name == "print_task":
            return await self._print_task(**arguments)
        elif function_name == "print_text":
            return await self._print_text(**arguments)
        return ToolResult(success=False, error=f"Unknown function: {function_name}")
    
    async def _print_task(self, task_description: str, importance: int, style: str = "handwritten") -> ToolResult:
        """Print short task card"""
        try:
            if not task_description:
                return ToolResult(success=False, error="No task provided")

            print(f"🖨️ Printing Task Card: '{task_description[:30]}' (Level {importance})...")
            self.task_printer.print_task(task_description, importance, style)
            return ToolResult(success=True, data="✓ Printed task card")
        
        except Exception as e:
            return ToolResult(success=False, error=f"Printer Error: {str(e)}")
    
    async def _print_text(self, text: str, title: str = None) -> ToolResult:
        """Print long text/notes/ideas - handles any text format naturally"""
        try:
            if not text:
                return ToolResult(success=False, error="No text provided")
            
            # Just pass raw text - renderer handles word-wrap via CSS
            print(f"🖨️ Printing: '{(title or text[:25])[:25]}...'")
            self.text_printer.print_long_text(text, title or "")
            return ToolResult(success=True, data="✓ Printed")
        
        except Exception as e:
            return ToolResult(success=False, error=f"Printer Error: {str(e)}")


