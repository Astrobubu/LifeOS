"""
Smart Agent - Autonomous AI with planning, memory, and self-correction
"""
import json
from typing import Optional
from dataclasses import dataclass
from openai import AsyncOpenAI

from config.settings import settings
from memory.vector_memory import VectorMemory
from profile.user_profile import get_profile
from tools import get_all_tool_schemas, get_tool
from tools.base_tool import ToolResult
from .memory_extractor import MemoryExtractor
from .confirmation import confirmation_manager
from utils.cost_tracker import cost_tracker
from utils.terminal_ui import terminal_ui


@dataclass
class AgentResponse:
    """Response from agent"""
    text: str
    needs_confirmation: bool = False
    confirmation_action: str = None
    confirmation_description: str = None


SYSTEM_PROMPT = """You are LifeOS, an intelligent autonomous AI assistant for {user_name}.

## Who You're Helping
{user_profile}

## Your Capabilities
- Long-term memory with semantic search
- Notes, tasks, email, calendar, finance tracking
- Web search and research
- Proactive learning - you remember important things automatically

## CRITICAL Behavior Rules
1. **USE CONVERSATION CONTEXT** - When user says "try again", "do it", "yes", or refers to something recent, LOOK AT THE CONVERSATION HISTORY. Don't ask them to repeat themselves.
2. Be concise and action-oriented
3. You know who your user is - use that context when drafting emails
4. Execute tasks autonomously - only confirm FINAL actions (send email, create event, delete)
5. For emails: use the user's profile, pitch, and signature automatically
6. **NEVER ask the user to clarify something obvious from recent messages**

## EMAIL WORKFLOW (IMPORTANT)
When user wants to contact/email someone:
1. FIRST: Search for their contact info (email address) using web_search
2. ONLY if you find an email: Draft the email using user's profile
3. If NO email found: Tell the user you couldn't find contact info, suggest alternatives
4. NEVER draft an email without having a valid recipient email address
5. Show the draft AND the recipient email for confirmation before sending

## Memory Context
{memory_context}

## Current Time
{current_time}
"""


class SmartAgent:
    """
    Autonomous agent with:
    - Vector memory for semantic search
    - User profile awareness
    - Automatic memory extraction
    - Autonomous execution (confirm only final actions)
    """
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.memory = VectorMemory()
        self.profile = get_profile()
        self.extractor = MemoryExtractor()
        self.tool_schemas = get_all_tool_schemas()
        self.conversation_history: list[dict] = []
    
    async def process(self, user_message: str, user_id: int) -> AgentResponse:
        """Main entry point - process user message intelligently"""
        terminal_ui.set_status("Thinking...")
        terminal_ui.log_activity(f"Message: {user_message[:40]}...")
        
        # Cancel any pending confirmations if user sends new message
        if confirmation_manager.get_pending_action(user_id):
            confirmation_manager.cancel_action(user_id)
        
        # Extract memories from user input (proactive)
        try:
            input_memories = await self.extractor.extract_from_input(user_message)
            for mem in input_memories:
                if isinstance(mem, dict) and mem.get("content"):
                    await self.memory.add(
                        content=mem.get("content", ""),
                        memory_type=mem.get("type", "general"),
                        importance=mem.get("importance", 0.5),
                        source="user_input"
                    )
        except Exception:
            pass  # Non-critical
        
        # Get relevant memory context
        memory_context = await self.memory.get_context(user_message)
        
        # Build conversation for LLM
        messages = self._build_messages(user_message, memory_context)
        
        # Get LLM response with tools
        response = await self._call_llm(messages)
        
        # Handle tool calls
        while response.choices[0].message.tool_calls:
            tool_calls = response.choices[0].message.tool_calls
            
            # Check for confirmation-required actions
            for tc in tool_calls:
                if confirmation_manager.requires_confirmation(tc.function.name):
                    args = json.loads(tc.function.arguments)
                    pending = confirmation_manager.create_pending_action(
                        user_id=user_id,
                        action_name=tc.function.name,
                        arguments=args
                    )
                    return AgentResponse(
                        text=f"**Confirm:** {pending.description}",
                        needs_confirmation=True,
                        confirmation_action=pending.action_name,
                        confirmation_description=pending.description
                    )
            
            # Execute tools
            tool_results = await self._execute_tools(tool_calls)
            
            # Add to conversation
            messages.append(response.choices[0].message)
            for tc, result in tool_results:
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result.to_dict())
                })
            
            # Get next response
            response = await self._call_llm(messages)
        
        # Get final text response
        assistant_message = response.choices[0].message.content or ""
        terminal_ui.set_status("Running")
        
        # Update conversation history
        self._update_history(user_message, assistant_message)
        
        # Extract and store memories from this exchange (background)
        await self._extract_memories(user_message, assistant_message)
        
        return AgentResponse(text=assistant_message)
    
    def _build_messages(self, user_message: str, memory_context: str) -> list[dict]:
        """Build messages array for LLM"""
        from datetime import datetime
        
        user_name = self.profile.get("name", "User")
        user_profile = self.profile.get_context_for_ai() if self.profile.is_setup else "Profile not set up yet."
        
        system = SYSTEM_PROMPT.format(
            user_name=user_name,
            user_profile=user_profile,
            memory_context=memory_context or "No relevant memories.",
            current_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        
        messages = [{"role": "system", "content": system}]
        
        # Add recent conversation history (more context = better "try again" understanding)
        for msg in self.conversation_history[-20:]:
            messages.append(msg)
        
        messages.append({"role": "user", "content": user_message})
        return messages
    
    async def _call_llm(self, messages: list[dict]):
        """Call OpenAI with tools"""
        response = await self.client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=messages,
            tools=self.tool_schemas if self.tool_schemas else None,
            tool_choice="auto" if self.tool_schemas else None,
            temperature=1,
            max_completion_tokens=2000
        )
        
        # Track token usage
        if response.usage:
            cost_tracker.track(
                model=settings.OPENAI_MODEL,
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens
            )
        
        return response
    
    async def _execute_tools(self, tool_calls: list) -> list[tuple]:
        """Execute tool calls with activity logging"""
        results = []
        
        # Friendly names for activities
        activity_names = {
            "web_search": "Searching the web",
            "browse_website": "Browsing website",
            "search_and_browse": "Searching & browsing",
            "read_emails": "Reading emails",
            "send_email": "Sending email",
            "get_email": "Getting email",
            "create_event": "Creating calendar event",
            "get_upcoming_events": "Checking calendar",
            "get_today_schedule": "Getting today's schedule",
            "create_reminder": "Setting reminder",
            "create_note": "Creating note",
            "read_note": "Reading note",
            "search_notes": "Searching notes",
            "list_notes": "Listing notes",
            "add_task": "Adding task",
            "list_tasks": "Listing tasks",
            "complete_task": "Completing task",
            "add_loan": "Recording loan",
            "list_loans": "Checking loans",
            "get_loan_summary": "Getting loan summary",
        }
        
        for tc in tool_calls:
            func_name = tc.function.name
            try:
                args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                args = {}
            
            # Log activity
            activity = activity_names.get(func_name, f"Running {func_name}")
            if func_name == "web_search" and args.get("query"):
                activity = f"Searching: {args['query'][:30]}..."
            elif func_name == "browse_website" and args.get("url"):
                activity = f"Browsing: {args['url'][:30]}..."
            terminal_ui.log_activity(activity)
            terminal_ui.set_status(activity)
            
            tool = self._get_tool(func_name)
            if tool:
                result = await tool.execute(func_name, args)
            else:
                result = ToolResult(success=False, error=f"Unknown function: {func_name}")
            
            results.append((tc, result))
        
        terminal_ui.set_status("Running")
        return results
    
    def _get_tool(self, function_name: str):
        """Get tool for function"""
        mapping = {
            'add_task': 'tasks',
            'update_task': 'tasks',
            'list_tasks': 'tasks',
            'complete_task': 'tasks',
            'delete_task': 'tasks',
            'get_calendar_events': 'calendar',
            'add_calendar_event': 'calendar',
            'add_note': 'notes',
            'search_notes': 'notes',
            'list_notes': 'notes',
            'send_email': 'gmail',
            'read_emails': 'gmail',
            'add_transaction': 'finance',
            'get_balance': 'finance',
            'get_transactions': 'finance',
            'browse_website': 'browser',
            'google_search': 'web_search',
            'print_task': 'printer'
        }
        tool_name = mapping.get(function_name)
        return get_tool(tool_name) if tool_name else None
    
    def _update_history(self, user_msg: str, assistant_msg: str):
        """Update conversation history"""
        self.conversation_history.append({"role": "user", "content": user_msg})
        self.conversation_history.append({"role": "assistant", "content": assistant_msg})
        
        # Keep last 20 messages
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]
    
    async def _extract_memories(self, user_msg: str, assistant_msg: str):
        """Extract and store memories from conversation"""
        try:
            memories = await self.extractor.extract(user_msg, assistant_msg)
            for mem in memories:
                if isinstance(mem, dict) and mem.get("content"):
                    await self.memory.add(
                        content=mem.get("content", ""),
                        memory_type=mem.get("type", "general"),
                        importance=mem.get("importance", 0.5),
                        source="conversation"
                    )
        except Exception:
            pass  # Memory extraction is non-critical
    
    async def handle_confirmation(self, user_id: int, confirmed: bool) -> str:
        """Handle confirmation button press"""
        if confirmed:
            pending = confirmation_manager.confirm_action(user_id)
            if pending:
                tool = self._get_tool(pending.action_name)
                if tool:
                    result = await tool.execute(pending.action_name, pending.arguments)
                    if result.success:
                        # Format the result nicely
                        data = result.data
                        if isinstance(data, dict):
                            return data.get("message", "Done!")
                        return f"Done! {data}"
                    return f"Failed: {result.error}"
                return "Could not execute."
            return "Action expired."
        else:
            confirmation_manager.cancel_action(user_id)
            return "Cancelled."
    
    async def process_voice(self, audio_bytes: bytes) -> str:
        """Transcribe voice"""
        transcript = await self.client.audio.transcriptions.create(
            model="gpt-4o-mini-transcribe",
            file=("voice.ogg", audio_bytes, "audio/ogg")
        )
        return transcript.text
    
    async def process_image(self, image_bytes: bytes, caption: str = "", user_id: int = 0) -> AgentResponse:
        """
        Smart image processing:
        - If caption indicates intent (contact, email, remember), take action
        - Extract info from image and feed into agent loop
        """
        import base64
        b64 = base64.b64encode(image_bytes).decode()
        
        # First, analyze the image and extract relevant info
        extraction_prompt = f"""Analyze this image and extract ALL relevant information.

User's intent: {caption or "Just analyzing"}

Extract:
1. Any business/company names
2. Contact info (phone, email, website, address)
3. Names of people
4. Any other relevant details

Return a structured summary of what you found."""

        response = await self.client.chat.completions.create(
            model=settings.OPENAI_VISION_MODEL,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": extraction_prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                ]
            }],
            max_completion_tokens=1000
        )
        
        image_info = response.choices[0].message.content
        
        # Check if user wants to take action (contact, email, save, etc.)
        action_keywords = ["contact", "email", "reach out", "call", "save", "remember", "note"]
        caption_lower = caption.lower() if caption else ""
        wants_action = any(kw in caption_lower for kw in action_keywords)
        
        if wants_action and user_id:
            # Feed the extracted info + user intent into the main agent loop
            enhanced_message = f"""Based on this image, the user wants to: {caption}

Information extracted from image:
{image_info}

User Profile for context:
{self.profile.get_context_for_ai()}

Take the appropriate action based on the user's intent. If they want to contact/email someone, draft an email using the user's profile and pitch."""
            
            return await self.process(enhanced_message, user_id)
        else:
            # Just return the analysis
            return AgentResponse(text=image_info)
    
    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []
    
    def get_memory_stats(self) -> dict:
        """Get memory statistics"""
        return self.memory.get_stats()
    
    @property
    def needs_setup(self) -> bool:
        """Check if user profile needs setup"""
        return not self.profile.is_setup
    
    def setup_profile(self, **kwargs):
        """Setup user profile"""
        self.profile.setup(**kwargs)
    
    def update_profile(self, **kwargs):
        """Update user profile"""
        self.profile.update(**kwargs)
    
    def get_profile_data(self) -> dict:
        """Get profile data"""
        return self.profile.data
