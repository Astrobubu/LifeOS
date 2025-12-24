"""
Base Handler - Abstract base class for all specialized handlers
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from datetime import datetime
from openai import AsyncOpenAI

from config.settings import settings
from memory.vector_memory import VectorMemory
from profile.user_profile import get_profile
from utils.cost_tracker import cost_tracker


@dataclass
class HandlerResponse:
    """Response from a handler"""
    text: str
    needs_confirmation: bool = False
    confirmation_action: str = None
    confirmation_description: str = None
    handler_used: str = None


class BaseHandler(ABC):
    """
    Base class for specialized domain handlers.
    Each handler has:
    - A focused system prompt for its domain
    - Access to only relevant tools
    - Domain-specific context loading
    """
    
    # Override in subclasses
    handler_name: str = "base"
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.memory = VectorMemory()
        self.profile = get_profile()
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return the specialized system prompt for this handler"""
        pass
    
    @abstractmethod
    def get_tools(self) -> list[dict]:
        """Return only the tools relevant to this handler"""
        pass
    
    @abstractmethod
    async def get_domain_context(self, user_message: str) -> str:
        """Load domain-specific context for this handler"""
        pass
    
    def get_tool_mapping(self) -> dict:
        """Return mapping of function names to tool names for execution"""
        return {}
    
    async def handle(
        self, 
        user_message: str, 
        conversation_history: list[dict],
        entities: dict = None
    ) -> HandlerResponse:
        """
        Process user message with domain-specific context and tools.
        
        Args:
            user_message: The user's message
            conversation_history: Recent conversation history
            entities: Extracted entities from routing
            
        Returns:
            HandlerResponse with the response text
        """
        from tools import get_tool
        from tools.base_tool import ToolResult
        from agent.confirmation import confirmation_manager
        
        # Build system prompt with domain context
        domain_context = await self.get_domain_context(user_message)
        memory_context = await self.memory.get_context(user_message, max_tokens=500)
        
        system_prompt = self._build_full_prompt(domain_context, memory_context)
        
        # Build messages
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add recent history (limited)
        for msg in conversation_history[-10:]:
            messages.append(msg)
        
        messages.append({"role": "user", "content": user_message})
        
        # Get tools for this handler
        tools = self.get_tools()
        tool_mapping = self.get_tool_mapping()
        
        # Call LLM
        response = await self._call_llm(messages, tools)
        
        # Handle tool calls
        while response.choices[0].message.tool_calls:
            tool_calls = response.choices[0].message.tool_calls
            
            # Check for confirmation-required actions
            for tc in tool_calls:
                if confirmation_manager.requires_confirmation(tc.function.name):
                    import json
                    args = json.loads(tc.function.arguments)
                    # Return confirmation request (let main agent handle this)
                    return HandlerResponse(
                        text=f"**Confirm:** {tc.function.name} with {args}",
                        needs_confirmation=True,
                        confirmation_action=tc.function.name,
                        handler_used=self.handler_name
                    )
            
            # Execute tools
            tool_results = await self._execute_tools(tool_calls, tool_mapping)
            
            # Add to conversation
            messages.append(response.choices[0].message)
            for tc, result in tool_results:
                import json
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result.to_dict())
                })
            
            # Get next response
            response = await self._call_llm(messages, tools)
        
        # Return final response
        return HandlerResponse(
            text=response.choices[0].message.content or "",
            handler_used=self.handler_name
        )
    
    def _build_full_prompt(self, domain_context: str, memory_context: str) -> str:
        """Build the complete system prompt"""
        user_name = self.profile.get("name", "User")
        user_profile = self.profile.get_context_for_ai() if self.profile.is_setup else ""
        
        base_prompt = self.get_system_prompt()
        
        return f"""{base_prompt}

## User Profile
{user_profile}

## Domain Context (IMPORTANT - Use this information)
{domain_context}

## Memory Context
{memory_context or "No relevant memories."}

## Current Time
{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
    
    async def _call_llm(self, messages: list[dict], tools: list[dict] = None):
        """Call OpenAI with tools"""
        try:
            response = await self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=messages,
                tools=tools if tools else None,
                tool_choice="auto" if tools else None,
                temperature=1,
                max_completion_tokens=6000
            )
            
            # Check for truncation - error directly to user
            if response.choices[0].finish_reason == "length":
                raise Exception("❌ Response was cut off (token limit hit). Try a simpler request.")
            
            # Track cost
            if response.usage:
                cost_tracker.track(
                    model=settings.OPENAI_MODEL,
                    input_tokens=response.usage.prompt_tokens,
                    output_tokens=response.usage.completion_tokens
                )
            
            return response
            
        except Exception as e:
            raise Exception(f"LLM error in {self.handler_name}: {str(e)}")
    
    async def _execute_tools(self, tool_calls: list, tool_mapping: dict) -> list[tuple]:
        """Execute tool calls"""
        from tools import get_tool
        from tools.base_tool import ToolResult
        import json
        
        results = []
        
        for tc in tool_calls:
            func_name = tc.function.name
            try:
                args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                args = {}
            
            # Get tool using mapping
            tool_name = tool_mapping.get(func_name)
            tool = get_tool(tool_name) if tool_name else None
            
            if tool:
                result = await tool.execute(func_name, args)
            else:
                result = ToolResult(success=False, error=f"Unknown tool: {func_name}")
            
            results.append((tc, result))
        
        return results
