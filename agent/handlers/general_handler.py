"""
General Handler - Fallback handler for general queries
Uses full tool set and memory for flexible handling
"""
from .base_handler import BaseHandler
from tools import get_all_tool_schemas


class GeneralHandler(BaseHandler):
    """
    General purpose handler for queries that don't fit specialized domains.
    Has access to all tools and uses memory for context.
    """
    
    handler_name = "general"
    
    def get_system_prompt(self) -> str:
        return """You are LifeOS, an intelligent personal assistant.

## Your Capabilities
- Long-term memory with semantic search
- Web search and browsing
- Tasks, notes, calendar, email
- Finance tracking (loans)
- Printing

## Intelligence Rules

### 1. UNDERSTAND INTENT
- If user shares an IDEA → engage thoughtfully, help develop it
- If user wants ACTION → execute immediately, be concise
- If user is VENTING → listen, acknowledge, don't try to fix
- If user asks QUESTION → answer directly, don't over-explain

### 2. BE AUTONOMOUS
- Execute tasks without asking "are you sure?"
- Only confirm DESTRUCTIVE actions (delete, send email)
- Use context from conversation - never ask user to repeat

### 3. BE CONCISE
- Task/note operations: "✓ Added: [title]" - nothing more
- Don't repeat what user said
- Short responses unless user needs explanation

### 4. ERROR RECOVERY
- If a tool fails, try alternative approaches
- If you don't understand, ask ONE clarifying question
"""
    
    def get_tools(self) -> list[dict]:
        """General handler has access to all tools"""
        return get_all_tool_schemas()
    
    def get_tool_mapping(self) -> dict:
        """Full tool mapping"""
        return {
            # Tasks
            'add_task': 'tasks',
            'add_tasks': 'tasks',
            'update_task': 'tasks',
            'list_tasks': 'tasks',
            'complete_task': 'tasks',
            'complete_tasks': 'tasks',
            'delete_task': 'tasks',
            'get_task': 'tasks',
            # Calendar
            'get_calendar_events': 'calendar',
            'add_calendar_event': 'calendar',
            'create_event': 'calendar',
            'get_upcoming_events': 'calendar',
            'get_today_schedule': 'calendar',
            'create_reminder': 'calendar',
            'delete_event': 'calendar',
            # Notes
            'create_note': 'notes',
            'read_note': 'notes',
            'update_note': 'notes',
            'delete_note': 'notes',
            'search_notes': 'notes',
            'list_notes': 'notes',
            # Email
            'send_email': 'gmail',
            'read_emails': 'gmail',
            'get_email': 'gmail',
            # Finance
            'add_loan': 'finance',
            'list_loans': 'finance',
            'settle_loan': 'finance',
            'update_loan': 'finance',
            'get_loan_summary': 'finance',
            # Browser/Web
            'browse_website': 'browser',
            'web_search': 'web_search',
            # Printer
            'print_task': 'printer',
            'print_text': 'printer',
            # Automations
            'create_automation': 'automations',
            'list_automations': 'automations',
            'delete_automation': 'automations',
            'run_automation': 'automations',
            'toggle_automation': 'automations',
        }
    
    async def get_domain_context(self, user_message: str) -> str:
        """Use memory search for general context"""
        # Memory is already loaded by base handler
        return "General assistant mode. All capabilities available."
