"""Smart Agent - Autonomous AI with TRUE agentic architecture

Following Anthropic Orchestrator-Workers pattern:
- Master Agent: Uses LLM to THINK, PLAN, and DELEGATE
- Sub-Agents: Autonomous agents for each domain with their own LLM + tools
- Working Memory: State persistence across steps and sessions
"""
import json
from typing import Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from openai import AsyncOpenAI

from config.settings import settings
from memory.vector_memory import VectorMemory
from profile.user_profile import get_profile
from tools import get_all_tool_schemas, get_tool
from tools.base_tool import ToolResult
from tools.finance_tool import FinanceTool
from .memory_extractor import MemoryExtractor
from .confirmation import confirmation_manager
from .master_agent import MasterAgent
from utils.cost_tracker import cost_tracker
from utils.terminal_ui import terminal_ui


@dataclass
class AgentResponse:
    """Response from agent"""
    text: str
    needs_confirmation: bool = False
    confirmation_action: str = None
    confirmation_description: str = None

# Context timeout - clear after 1 hour of inactivity
CONTEXT_TIMEOUT_HOURS = 1

SYSTEM_PROMPT = """You are LifeOS, an intelligent autonomous AI assistant for {user_name}.

## Who You're Helping
{user_profile}

## Your Capabilities
- Long-term memory with semantic search
- Notes, tasks, email, calendar, finance tracking
- Web search and browsing
- Proactive learning - remember important things automatically

## VOCABULARY (Understand These as Equivalent)
- **Tasks** = todos, reminders, action items, things to do, projects, goals
- **Notes** = ideas, thoughts, drafts, documents, writings, brainstorms
- **Projects** = collections of tasks, big goals, initiatives

## INTELLIGENCE RULES

### 1. UNDERSTAND INTENT
- If user shares an IDEA → engage thoughtfully, ask questions, help develop it, then offer to save as a note
- If user wants ACTION → execute immediately, be concise
- If user is VENTING → listen, acknowledge, don't try to fix
- If user asks QUESTION → answer directly, don't over-explain

### 2. BE AUTONOMOUS
- Execute tasks without asking "are you sure?"
- Only confirm DESTRUCTIVE actions (delete, send email)
- Use context from conversation - never ask user to repeat themselves
- If something fails, try to fix it yourself before asking for help

### 3. BE CONCISE
- Task/note operations: "✓ Added: [title]" - nothing more
- Don't repeat what user said
- Don't explain what you're doing unless asked
- Short responses unless user needs explanation

### 3.5. PRINT = JUST DO IT
- When user says "print" (print task, print text, print this) → CALL THE PRINTER TOOL IMMEDIATELY
- NO analyzing, NO questioning, NO explaining what you're about to print
- Extract the key content and print_task or print_text directly
- Response after printing: "✓ Printed" - that's it

### 4. PROACTIVE THINKING
- Notice patterns in what user asks for
- Suggest improvements when appropriate
- Remember preferences without being asked
- Connect related information across conversations

### 5. ERROR RECOVERY
- If a tool fails, try alternative approaches
- If you don't understand, ask ONE clarifying question
- If something seems wrong, flag it briefly

## Memory Context
{memory_context}

## Domain Context
{domain_context}

## Current Time
{current_time}
"""


class SmartAgent:
    """
    Autonomous agent with TRUE agentic architecture.
    
    Uses MasterAgent (orchestrator) which:
    - Uses LLM to understand and PLAN complex requests
    - Delegates to specialized sub-agents (each with own LLM + tools)
    - Synthesizes results into coherent responses
    
    Falls back to legacy processing if master agent fails.
    """
    
    # Use TRUE agentic system (set to False for legacy mode)
    USE_MASTER_AGENT = True
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.memory = VectorMemory()
        self.profile = get_profile()
        self.extractor = MemoryExtractor()
        self.tool_schemas = get_all_tool_schemas()
        self.conversation_history: list[dict] = []
        # Context management
        self.last_interaction_time: datetime = datetime.now()
        
        # NEW: Master Agent for true agentic processing
        self.master_agent = MasterAgent()
    
    async def process(self, user_message: str, user_id: int) -> AgentResponse:
        """Main entry point - process through master agent or legacy"""
        terminal_ui.set_status("Thinking...")
        terminal_ui.log_activity(f"Message: {user_message[:40]}...")
        
        # Cancel any pending confirmations if user sends new message
        if confirmation_manager.get_pending_action(user_id):
            confirmation_manager.cancel_action(user_id)
        
        # Check for context timeout (1 hour) - summarize and clear if stale
        time_since_last = datetime.now() - self.last_interaction_time
        if time_since_last > timedelta(hours=CONTEXT_TIMEOUT_HOURS) and self.conversation_history:
            await self._summarize_and_clear_context()
        
        # Update interaction time
        self.last_interaction_time = datetime.now()
        
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
        
        # === FAST-PATH ROUTING (skip planning for simple requests) ===
        fast_route = self._detect_fast_path(user_message)
        if fast_route:
            terminal_ui.log_activity(f"Fast-path: {fast_route['agent']}")
            try:
                result = await self._execute_fast_path(fast_route, user_message)
                self._update_history(user_message, result.text)
                terminal_ui.set_status("Running")
                return result
            except Exception as e:
                terminal_ui.log_activity(f"Fast-path failed, using master: {str(e)[:50]}")
        
        # === TRUE AGENTIC SYSTEM ===
        if self.USE_MASTER_AGENT:
            try:
                # Process through Master Agent
                master_response = await self.master_agent.process(user_message, user_id)
                
                # Update our conversation history from master
                self._update_history(user_message, master_response.text)
                
                # Extract and store memories (background)
                await self._extract_memories(user_message, master_response.text)
                
                terminal_ui.set_status("Running")
                
                return AgentResponse(
                    text=master_response.text,
                    needs_confirmation=master_response.needs_confirmation,
                    confirmation_action=master_response.confirmation_action,
                    confirmation_description=master_response.confirmation_description
                )
                
            except Exception as e:
                # Fallback to legacy processing on master agent error
                terminal_ui.log_error(f"Master agent error: {str(e)[:100]}", "Agentic")
                terminal_ui.log_activity("Falling back to legacy processing")
        
        # === LEGACY PROCESSING (fallback) ===
        return await self._process_legacy(user_message, user_id)
    
    async def _process_legacy(self, user_message: str, user_id: int) -> AgentResponse:
        """Legacy processing method - used as fallback"""
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
        user_name = self.profile.get("name", "User")
        user_profile = self.profile.get_context_for_ai() if self.profile.is_setup else "Profile not set up yet."
        
        # Detect intent and load relevant domain context
        domain_context = self._get_domain_context(user_message)
        
        system = SYSTEM_PROMPT.format(
            user_name=user_name,
            user_profile=user_profile,
            memory_context=memory_context or "No relevant memories.",
            domain_context=domain_context,
            current_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        
        messages = [{"role": "system", "content": system}]
        
        # Add recent conversation history
        for msg in self.conversation_history[-20:]:
            messages.append(msg)
        
        messages.append({"role": "user", "content": user_message})
        return messages
    
    def _detect_intent(self, message: str) -> list[str]:
        """Detect message intent to load relevant context"""
        msg_lower = message.lower()
        intents = []
        
        # Loan/money keywords
        loan_keywords = ["owe", "owes", "loan", "lend", "lent", "borrow", "borrowed", "debt", "pay back", "paid", "money", "aed", "usd", "dirhams", "$"]
        if any(kw in msg_lower for kw in loan_keywords):
            intents.append("loans")
        
        # Check for person names that have active loans
        try:
            finance = FinanceTool()
            loans = finance._load_loans()
            loan_people = {l.get("person", "").lower() for l in loans if l.get("status") == "active"}
            if any(person in msg_lower for person in loan_people if person):
                intents.append("loans")
        except Exception:
            pass
        
        # Notes keywords  
        note_keywords = ["note", "notes", "write", "wrote", "jot", "draft", "document"]
        if any(kw in msg_lower for kw in note_keywords):
            intents.append("notes")
        
        # Task keywords
        task_keywords = ["task", "todo", "remind", "reminder", "do", "doing", "done"]
        if any(kw in msg_lower for kw in task_keywords):
            intents.append("tasks")
        
        return list(set(intents))  # Remove duplicates
    
    def _get_domain_context(self, user_message: str) -> str:
        """Get domain-specific context based on detected intent"""
        intents = self._detect_intent(user_message)
        
        if not intents:
            return "No specific domain context needed."
        
        context_parts = []
        
        if "loans" in intents:
            context_parts.append(self._get_loans_context())
        
        # Can add more domain contexts here as needed:
        # if "notes" in intents:
        #     context_parts.append(self._get_notes_context())
        
        return "\n\n".join(context_parts) if context_parts else "No specific domain context."
    
    def _get_loans_context(self) -> str:
        """Get active loans formatted for context"""
        try:
            finance = FinanceTool()
            loans = finance._load_loans()
            active = [l for l in loans if l.get("status") == "active"]
            
            if not active:
                return "LOANS: No active loans."
            
            # Group by person
            i_owe = []
            they_owe = []
            for loan in active:
                person = loan.get("person", "Unknown")
                amount = loan.get("amount", 0)
                if loan.get("direction") == "i_owe":
                    i_owe.append(f"  - {person}: {amount}")
                else:
                    they_owe.append(f"  - {person}: {amount}")
            
            lines = ["LOANS (use this to understand who owes whom):"]
            if i_owe:
                lines.append("YOU OWE these people (direction=i_owe):")
                lines.extend(i_owe)
            if they_owe:
                lines.append("These people OWE YOU (direction=they_owe):")
                lines.extend(they_owe)
            
            return "\n".join(lines)
        except Exception:
            return "LOANS: Unable to load."
    
    async def _call_llm(self, messages: list[dict]):
        """Call OpenAI with tools - with comprehensive error handling"""
        try:
            response = await self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=messages,
                tools=self.tool_schemas if self.tool_schemas else None,
                tool_choice="auto" if self.tool_schemas else None,
                temperature=1,
                max_completion_tokens=6000
            )
            
            # Check for truncation - error directly to user
            if response.choices[0].finish_reason == "length":
                raise Exception("❌ Response was cut off (token limit hit). Try a simpler request.")
            
            # Track token usage
            if response.usage:
                cost_tracker.track(
                    model=settings.OPENAI_MODEL,
                    input_tokens=response.usage.prompt_tokens,
                    output_tokens=response.usage.completion_tokens
                )
            
            # Check for empty response
            if not response.choices:
                raise ValueError("LLM returned no choices - possibly content filtered or token limit hit")
            
            return response
            
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e) if str(e) else "Unknown error (empty message)"
            
            # Log detailed error
            terminal_ui.log_error(f"{error_type}: {error_msg[:100]}", "LLM")
            
            # Enhance error message based on type
            if "context_length" in error_msg.lower() or "token" in error_msg.lower():
                raise Exception(f"❌ Prompt too long ({error_type}). Try a shorter message or /clear to reset context.")
            elif "rate_limit" in error_msg.lower():
                raise Exception(f"❌ Rate limited. Wait a moment and try again.")
            elif "authentication" in error_msg.lower() or "api_key" in error_msg.lower():
                raise Exception(f"❌ API key error. Check your OpenAI configuration.")
            elif "timeout" in error_msg.lower():
                raise Exception(f"❌ Request timed out. Try a simpler request.")
            elif "content_filter" in error_msg.lower() or "filtered" in error_msg.lower():
                raise Exception(f"❌ Content was filtered. Try rephrasing.")
            else:
                # Include full error for debugging
                raise Exception(f"❌ {error_type}: {error_msg[:200]}")
    
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
            'add_tasks': 'tasks',
            'update_task': 'tasks',
            'list_tasks': 'tasks',
            'complete_task': 'tasks',
            'complete_tasks': 'tasks',
            'delete_task': 'tasks',
            'get_task': 'tasks',
            'get_calendar_events': 'calendar',
            'add_calendar_event': 'calendar',
            'create_event': 'calendar',
            'get_upcoming_events': 'calendar',
            'get_today_schedule': 'calendar',
            'create_reminder': 'calendar',
            'delete_event': 'calendar',
            'create_note': 'notes',
            'read_note': 'notes',
            'update_note': 'notes',
            'delete_note': 'notes',
            'search_notes': 'notes',
            'list_notes': 'notes',
            'send_email': 'gmail',
            'read_emails': 'gmail',
            'get_email': 'gmail',
            'add_loan': 'finance',
            'list_loans': 'finance',
            'settle_loan': 'finance',
            'update_loan': 'finance',
            'get_loan_summary': 'finance',
            'browse_website': 'browser',
            'web_search': 'web_search',
            'print_task': 'printer',
            'print_text': 'printer',
            'create_automation': 'automations',
            'list_automations': 'automations',
            'delete_automation': 'automations',
            'run_automation': 'automations',
            'toggle_automation': 'automations'
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
        # Skip extraction for short confirmations (saves API calls)
        if len(assistant_msg) < 100 and "✓" in assistant_msg:
            return
        
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
    
    def _detect_fast_path(self, message: str) -> dict | None:
        """
        Detect if message matches a simple pattern that can skip planning.
        Returns routing info or None if planning is needed.
        """
        import re
        msg = message.lower().strip()
        
        # Pattern → (agent, task_extractor)
        patterns = [
            # Reprint / run automation (HIGHEST PRIORITY)
            (r'^reprint\s+(.+)', 'automations', lambda m: f"Run the automation matching: {m.group(1)}"),
            (r'^run\s+(.+)\s+again', 'automations', lambda m: f"Run the automation matching: {m.group(1)}"),
            
            # One-time print
            (r'^print\s+(?:task\s+)?(.+)', 'print', lambda m: f"Print task card: {m.group(1)}"),
            
            # Reminders
            (r'^remind\s+me\s+(.+)', 'calendar', lambda m: f"Create reminder: {m.group(1)}"),
            
            # Loans (simple patterns)
            (r'^i\s+owe\s+(\w+)\s+(\d+)', 'finance', lambda m: f"Record loan: I owe {m.group(1)} {m.group(2)}"),
            (r'^(\w+)\s+owes\s+me\s+(\d+)', 'finance', lambda m: f"Record loan: {m.group(1)} owes me {m.group(2)}"),
            
            # List commands
            (r'^list\s+(automations?|tasks?|loans?|notes?)', 'automations', lambda m: f"List all {m.group(1)}"),
        ]
        
        for pattern, agent, task_fn in patterns:
            match = re.match(pattern, msg)
            if match:
                return {
                    'agent': agent,
                    'task': task_fn(match),
                    'original': message
                }
        
        return None
    
    async def _execute_fast_path(self, route: dict, original_message: str) -> AgentResponse:
        """Execute a fast-path route directly through sub-agent."""
        from .sub_agents import (
            PrintSubAgent, AutomationsSubAgent, CalendarSubAgent, FinanceSubAgent
        )
        
        agent_map = {
            'print': PrintSubAgent,
            'automations': AutomationsSubAgent,
            'calendar': CalendarSubAgent,
            'finance': FinanceSubAgent,
        }
        
        agent_class = agent_map.get(route['agent'])
        if not agent_class:
            raise ValueError(f"No fast-path agent for: {route['agent']}")
        
        agent = agent_class()
        result = await agent.execute(route['task'], {'original_message': original_message})
        
        if result.success:
            return AgentResponse(text=result.output)
        else:
            raise Exception(result.error or "Sub-agent failed")
    
    async def _summarize_and_clear_context(self):
        """Summarize old conversation and clear history after timeout"""
        if not self.conversation_history:
            return
        
        # Build conversation text for summarization
        conv_text = "\n".join([
            f"{msg['role'].upper()}: {msg['content'][:200]}"
            for msg in self.conversation_history[-10:]
        ])
        
        try:
            # Ask LLM to summarize
            response = await self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{
                    "role": "user",
                    "content": f"Summarize this conversation in 1-2 sentences for future reference:\n\n{conv_text}"
                }],
                max_completion_tokens=150
            )
            
            summary = response.choices[0].message.content
            if summary:
                # Store as a session memory
                await self.memory.add(
                    content=f"Previous session summary: {summary}",
                    memory_type="insight",
                    importance=0.6,
                    source="session_summary"
                )
                terminal_ui.log_activity("Context cleared (1hr timeout)")
        except Exception:
            pass
        
        # Clear history
        self.conversation_history = []
    
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
            model="gpt-4o-transcribe",
            file=("voice.ogg", audio_bytes, "audio/ogg")
        )
        return transcript.text
    
    async def _detect_image_intent(self, caption: str, extracted_info: str) -> dict:
        """
        Detect user intent from image caption using LLM analysis.
        Returns structured intent with confidence score.
        """
        if not caption or len(caption.strip()) < 3:
            return {
                "intent": "analyze",
                "confidence": 0.9,
                "reasoning": "No caption provided, assuming user wants basic analysis",
                "suggested_action": "Provide visual description"
            }
        
        intent_prompt = f"""Analyze the user's caption and determine their intent for this image.

Caption: "{caption}"
Image content summary: {extracted_info[:300]}

Possible intents:
- print: wants to PRINT this (keywords: print, printer, output, physical copy). HIGH PRIORITY - if any print keyword found, choose this.
- contact: wants to reach out to someone (email, call, add contact)
- save_note: wants to save this information as a note
- remember: wants to store specific facts from the image
- analyze: just wants analysis/explanation of what's in the image
- no_action: casual sharing, no specific action needed

Return JSON with:
{{
  "intent": "print|contact|save_note|remember|analyze|no_action",
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation of why you chose this intent",
  "suggested_action": "what the user likely wants done"
}}"""

        try:
            response = await self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{"role": "user", "content": intent_prompt}],
                temperature=1,
                max_completion_tokens=200,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
        except Exception:
            # Fallback to analyze intent
            return {
                "intent": "analyze",
                "confidence": 0.5,
                "reasoning": "Failed to detect intent, defaulting to analysis",
                "suggested_action": "Provide description"
            }
    
    async def process_image(self, image_bytes: bytes, caption: str = "", user_id: int = 0) -> AgentResponse:
        """
        Generalized image processing with:
        - LLM-based intent detection (no hard-coded keywords)
        - Automatic background memory storage
        - Smart action execution based on confidence
        """
        import base64
        b64 = base64.b64encode(image_bytes).decode()
        
        # Step 1: Extract detailed information from image
        # Step 1: Extract detailed information from image
        extraction_prompt = f"""Extract text and key info from this image CONCISELY.

User's caption: {caption or "No caption"}

Instructions:
1. READ ALL VISIBLE TEXT VERBATIM.
2. List key facts (dates, names, prices, locations).
3. NO visual descriptions (don't describe colors, layout, fonts).
4. Keep it short and direct.

Output format:
- Text: "..."
- Key Details: ..."""

        try:
            terminal_ui.log_activity(f"Vision: Analyzing image ({len(b64[:100])}... chars base64)")
            response = await self.client.chat.completions.create(
                model=settings.OPENAI_VISION_MODEL,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": extraction_prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                    ]
                }],
                max_completion_tokens=5000
            )
            
            terminal_ui.log_activity(f"Vision: Got response from {settings.OPENAI_VISION_MODEL}")
            image_info = response.choices[0].message.content
            terminal_ui.log_activity(f"Vision: Content length = {len(image_info) if image_info else 0}")
            
            if not image_info or len(image_info.strip()) == 0:
                error_msg = "Vision model returned empty content"
                terminal_ui.log_error(error_msg, "Vision")
                terminal_ui.log_error(f"Response object: {response}", "Vision")
                image_info = "Unable to extract information from this image."
        except Exception as e:
            # Vision model failed - return error gracefully
            error_detail = f"Vision error: {type(e).__name__}: {str(e)}"
            terminal_ui.log_error(error_detail, "Image")
            terminal_ui.log_error(f"Full error: {repr(e)}", "Image")
            return AgentResponse(text=f"❌ Could not analyze image: {str(e)[:150]}")
        
        # Step 2: Detect user intent using LLM (not keywords)
        intent_result = await self._detect_image_intent(caption, image_info)
        intent = intent_result.get("intent", "analyze")
        confidence = intent_result.get("confidence", 0.5)
        
        # Step 3: Store image description as memory automatically (background)
        try:
            # Extract key entities for metadata
            entities_prompt = f"""From this information, extract key entities (names, companies, locations, emails, phones).
            
Information: {image_info[:500]}

Return a simple comma-separated list of key entities (max 10)."""
            
            entities_response = await self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{"role": "user", "content": entities_prompt}],
                temperature=1,
                max_completion_tokens=100
            )
            entities = entities_response.choices[0].message.content.strip()
            
            # Store as image memory
            memory_content = f"Image received: {image_info[:400]}"
            await self.memory.add(
                content=memory_content,
                memory_type="image_memory",
                importance=0.7,
                source="image_upload",
                metadata={
                    "caption": caption or "",
                    "entities": entities,
                    "timestamp": datetime.now().isoformat(),
                    "detected_intent": intent,
                    "full_description": image_info
                }
            )
        except Exception:
            pass  # Memory storage is non-critical
        
        # Step 4: Execute action based on intent and confidence
        
        # PRINT INTENT - fast path, no overthinking
        if intent == "print" and confidence >= 0.5:
            # Extract just the essential text/task from image_info for printing
            print_text = image_info.strip()
            # Keep it short - just the key text, no descriptions
            if len(print_text) > 300:
                # Let agent decide what to print but with clear instruction
                return await self.process(
                    f"Print this exactly, no questions: {print_text[:500]}",
                    user_id
                )
            else:
                return await self.process(
                    f"Print this task: {print_text}",
                    user_id
                )
        
        if confidence >= 0.6 and intent in ["contact", "save_note", "remember"] and user_id:
            # High confidence action intent - process through main agent
            enhanced_message = f"""Based on this image, the user wants to: {caption}

Information extracted from image:
{image_info}

User Profile for context:
{self.profile.get_context_for_ai()}

Detected intent: {intent} (confidence: {confidence:.0%})
Suggested action: {intent_result.get('suggested_action', 'Process request')}

Take the appropriate action based on the user's intent."""
            
            return await self.process(enhanced_message, user_id)
        else:
            # Low confidence or analyze intent - just return the analysis
            response_text = image_info or "Could not analyze image - please try again."
            if intent != "analyze" and image_info:
                response_text = f"📸 {intent_result.get('suggested_action', 'Image analyzed')}\n\n{image_info}"
            
            # Update history so context is preserved for follow-up questions
            user_msg = f"[User sent an image] {caption}" if caption else "[User sent an image]"
            self._update_history(user_msg, response_text)
            
            return AgentResponse(text=response_text)
    
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
