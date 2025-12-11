from typing import Dict, Any, List
from tools.base_tool import BaseTool, ToolResult
import sys
import os

# Add project root to path to import printer_control modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from printer_control.print_task import TaskPrinter, PRINTER_NAME

class PrinterTool(BaseTool):
    def __init__(self):
        self.printer = TaskPrinter(PRINTER_NAME)

    def get_function_schemas(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "print_task",
                    "description": "Prints a physical task card on the thermal printer. Requires a description and an importance level.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task_description": {
                                "type": "string",
                                "description": "The clean text content of the task to print (e.g. 'Buy Milk'). Do NOT include importance indicators like 'Urgent' or '***' here. Keep it under 5 words."
                            },
                            "importance": {
                                "type": "integer",
                                "description": "The importance level: 1 (Normal/Low), 2 (Important/Medium), 3 (Urgent/Critical/High/3 Stars). Map user's urgency words or stars to this number.",
                                "enum": [1, 2, 3]
                            },
                            "style": {
                                "type": "string",
                                "description": "The visual style of the printed card. Defaults to 'handwritten'. Use 'urgent' for warning style.",
                                "enum": ["handwritten", "urgent"]
                            }
                        },
                        "required": ["task_description", "importance"]
                    }
                }
            }
        ]

    async def execute(self, function_name: str, arguments: Dict[str, Any]) -> ToolResult:
        if function_name == "print_task":
            try:
                task_text = arguments.get("task_description")
                importance = arguments.get("importance")
                style = arguments.get("style", "handwritten") # Default to handwritten

                if not task_text or importance is None:
                    return ToolResult(success=False, error="Missing task_description or importance.")

                # Enforce 5-word limit for physical printout
                words = task_text.split()
                if len(words) > 5:
                    truncated_task_text = " ".join(words[:5]) + "..."
                else:
                    truncated_task_text = task_text

                print(f"🖨️ Printing Task: '{truncated_task_text}' (Level {importance}, Style: {style})...")
                
                # Invoke the printer logic with the original text (no truncation)
                self.printer.print_task(task_text, importance, style)
                
                return ToolResult(success=True, data="Printed.")
            
            except Exception as e:
                return ToolResult(success=False, error=f"Printer Error: {str(e)}")
        
        return ToolResult(success=False, error=f"Unknown function: {function_name}")
