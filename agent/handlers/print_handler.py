"""
Print Handler - Specialized handler for printing operations
Optimized for fast, direct action with minimal context
"""
from .base_handler import BaseHandler
from tools.printer_tool import PrinterTool


class PrintHandler(BaseHandler):
    """
    Handler for print operations.
    
    This handler is optimized for speed - printing should be immediate
    with minimal analysis or questioning.
    """
    
    handler_name = "print"
    
    def __init__(self):
        super().__init__()
        self.printer_tool = PrinterTool()
    
    def get_system_prompt(self) -> str:
        return """You are LifeOS Print Assistant. Your job is simple: PRINT things FAST.

## Rules
1. When user says "print" - DO IT IMMEDIATELY
2. Don't analyze, don't ask questions, don't explain
3. Extract the content and call the appropriate print function
4. Response after printing: "✓ Printed" - that's it

## Print Functions
- print_task: For task-formatted output (title + description)
- print_text: For general text/content

## Examples
"Print: buy groceries" → print_task(title="buy groceries")
"Print this note: meeting at 3pm" → print_text(text="meeting at 3pm")
"""
    
    def get_tools(self) -> list[dict]:
        return self.printer_tool.get_function_schemas()
    
    def get_tool_mapping(self) -> dict:
        return {
            "print_task": "printer",
            "print_text": "printer",
        }
    
    async def get_domain_context(self, user_message: str) -> str:
        """Minimal context for print - speed is priority"""
        return "Printer ready. Extract content and print immediately."
