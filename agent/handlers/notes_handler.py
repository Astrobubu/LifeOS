"""
Notes Handler - Specialized handler for notes and document management
"""
from .base_handler import BaseHandler
from tools.notes_tool import NotesTool


class NotesHandler(BaseHandler):
    """Handler for note-taking and document management"""
    
    handler_name = "notes"
    
    def __init__(self):
        super().__init__()
        self.notes_tool = NotesTool()
    
    def get_system_prompt(self) -> str:
        return """You are LifeOS Notes Assistant, specialized in note-taking and documentation.

## Your Role
- Create and organize notes
- Search existing notes
- Help draft and edit documents
- Manage ideas and thoughts

## Note Guidelines
- Notes have titles and content
- Can be tagged for organization
- Support markdown formatting

## Response Style
- For creation: "✓ Saved note: [title]"
- For search: Show relevant excerpts
- Engage thoughtfully with ideas before saving
"""
    
    def get_tools(self) -> list[dict]:
        return self.notes_tool.get_function_schemas()
    
    def get_tool_mapping(self) -> dict:
        return {
            "create_note": "notes",
            "read_note": "notes",
            "update_note": "notes",
            "delete_note": "notes",
            "search_notes": "notes",
            "list_notes": "notes",
        }
    
    async def get_domain_context(self, user_message: str) -> str:
        """Load notes context - recent notes or search results"""
        try:
            # List recent notes
            result = await self.notes_tool.execute("list_notes", {})
            
            if result.success and result.data:
                return f"""EXISTING NOTES:
{result.data[:500] if len(result.data) > 500 else result.data}

You can search notes for specific content or create new ones."""
            else:
                return "No existing notes. Ready to help you create new ones."
                
        except Exception as e:
            return f"Error loading notes: {str(e)}"
