"""
Email Handler - Specialized handler for email operations
"""
from .base_handler import BaseHandler
from tools.gmail_tool import GmailTool


class EmailHandler(BaseHandler):
    """Handler for email operations"""
    
    handler_name = "email"
    
    def __init__(self):
        super().__init__()
        self.email_tool = GmailTool()
    
    def get_system_prompt(self) -> str:
        return """You are LifeOS Email Assistant, specialized in email management.

## Your Role
- Read and summarize emails
- Compose and send emails
- Search for specific emails
- Help draft responses

## Email Guidelines
- Always confirm before sending
- Keep subject lines clear and concise
- For replies, reference the original context
- Summarize long emails effectively

## Response Style
- For reading: Summarize key points
- For composing: Draft clearly, confirm before send
- For searches: Show relevant results with dates
"""
    
    def get_tools(self) -> list[dict]:
        return self.email_tool.get_function_schemas()
    
    def get_tool_mapping(self) -> dict:
        return {
            "send_email": "gmail",
            "read_emails": "gmail",
            "get_email": "gmail",
        }
    
    async def get_domain_context(self, user_message: str) -> str:
        """Load recent email summary"""
        try:
            result = await self.email_tool.execute("read_emails", {"max_results": 5})
            
            if result.success and result.data:
                return f"""RECENT EMAILS:
{result.data[:600] if len(str(result.data)) > 600 else result.data}

Ready to help with email operations."""
            else:
                return "Email access ready. What would you like to do?"
                
        except Exception as e:
            return f"Email context unavailable: {str(e)}"
