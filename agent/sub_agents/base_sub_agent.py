"""
Base Sub-Agent - Abstract base class for all autonomous sub-agents

Each sub-agent:
1. Has its own LLM with domain-specific prompt
2. Has access to domain-specific tools
3. Operates in an AGENTIC LOOP until task complete
4. Returns structured results to master agent
"""
import json
from abc import ABC, abstractmethod
from typing import Optional
from datetime import datetime
from openai import AsyncOpenAI

from config.settings import settings
from tools import get_tool
from tools.base_tool import ToolResult
from ..planning import AgentType, SubAgentResult
from utils.cost_tracker import cost_tracker
from utils.terminal_ui import terminal_ui


class BaseSubAgent(ABC):
    """
    Abstract base class for autonomous sub-agents.
    
    Key features:
    - Domain-specific LLM prompt
    - Domain-specific tools
    - Agentic loop (LLM + tools until complete)
    - Structured result output
    """
    
    # Override in subclasses
    agent_type: AgentType = None
    agent_name: str = "base"
    max_iterations: int = 10  # Safety limit
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return the specialized system prompt for this agent"""
        pass
    
    @abstractmethod
    def get_tools(self) -> list[dict]:
        """Return the OpenAI function schemas for this agent's tools"""
        pass
    
    @abstractmethod
    def get_tool_mapping(self) -> dict[str, str]:
        """Return mapping of function_name -> tool_name for execution"""
        pass
    
    async def execute(self, task: str, context: dict = None) -> SubAgentResult:
        """
        Execute a task using this sub-agent's capabilities.
        
        This runs an AGENTIC LOOP:
        1. Send task + context to LLM
        2. If LLM returns tool calls, execute them
        3. Add tool results to conversation
        4. Repeat until LLM returns final response (no tool calls)
        
        Args:
            task: Natural language description of what to do
            context: Optional context from previous steps
            
        Returns:
            SubAgentResult with output, data, and metadata
        """
        terminal_ui.log_activity(f"[{self.agent_name}] Starting: {task[:50]}...")
        
        # Build initial messages
        messages = self._build_messages(task, context)
        tools = self.get_tools()
        tool_mapping = self.get_tool_mapping()
        
        # Track execution
        iterations = 0
        tools_called = []
        extracted_data = {}
        
        # === AGENTIC LOOP ===
        while iterations < self.max_iterations:
            iterations += 1
            
            try:
                # Call LLM
                response = await self._call_llm(messages, tools)
                
                # Check for tool calls
                if response.choices[0].message.tool_calls:
                    tool_calls = response.choices[0].message.tool_calls
                    
                    # Execute each tool
                    messages.append(response.choices[0].message)
                    
                    for tc in tool_calls:
                        func_name = tc.function.name
                        tools_called.append(func_name)
                        
                        try:
                            args = json.loads(tc.function.arguments)
                        except json.JSONDecodeError:
                            args = {}
                        
                        terminal_ui.log_activity(f"[{self.agent_name}] Tool: {func_name}")
                        
                        # Execute tool
                        result = await self._execute_tool(func_name, args, tool_mapping)
                        
                        # Extract any structured data from result
                        if result.success and result.data:
                            extracted_data.update(self._extract_data_from_result(func_name, result))
                        
                        # Add to conversation
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": json.dumps(result.to_dict())
                        })
                    
                    # Continue loop for next LLM response
                    continue
                
                # No tool calls = LLM is done
                final_response = response.choices[0].message.content or ""
                
                terminal_ui.log_activity(f"[{self.agent_name}] Complete ({iterations} iterations)")
                
                return SubAgentResult(
                    success=True,
                    output=final_response,
                    data=extracted_data,
                    agent_type=self.agent_type,
                    iterations_used=iterations,
                    tools_called=tools_called,
                )
                
            except Exception as e:
                terminal_ui.log_error(f"[{self.agent_name}] Error: {str(e)[:100]}")
                
                return SubAgentResult(
                    success=False,
                    output="",
                    error=str(e),
                    agent_type=self.agent_type,
                    iterations_used=iterations,
                    tools_called=tools_called,
                )
        
        # Max iterations reached
        return SubAgentResult(
            success=False,
            output="Max iterations reached without completing task",
            error="iteration_limit",
            requires_replanning=True,  # Master should reconsider
            agent_type=self.agent_type,
            iterations_used=iterations,
            tools_called=tools_called,
        )
    
    def _build_messages(self, task: str, context: dict = None) -> list[dict]:
        """Build the initial messages for the LLM"""
        system_prompt = self.get_system_prompt()
        
        # Add context to system prompt if provided
        if context:
            context_str = self._format_context(context)
            system_prompt += f"\n\n## Context from Previous Steps\n{context_str}"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": task}
        ]
        
        return messages
    
    def _format_context(self, context: dict) -> str:
        """Format context dict into readable string"""
        parts = []
        
        if context.get("goal"):
            parts.append(f"**Overall Goal:** {context['goal']}")
        
        if context.get("previous_results"):
            parts.append("**Results from previous steps:**")
            for r in context["previous_results"]:
                parts.append(f"- {r['agent']}: {r['output'][:200]}")
                if r.get("data"):
                    parts.append(f"  Data: {json.dumps(r['data'])}")
        
        if context.get("session_notes"):
            parts.append("**Session notes:**")
            for note in context["session_notes"][-3:]:
                parts.append(f"- {note['content']}")
        
        return "\n".join(parts) if parts else "No additional context."
    
    async def _call_llm(self, messages: list[dict], tools: list[dict] = None):
        """Call OpenAI API"""
        response = await self.client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=messages,
            tools=tools if tools else None,
            tool_choice="auto" if tools else None,
            max_completion_tokens=6000
        )
        
        # Check for truncation - error directly to user
        if response.choices[0].finish_reason == "length":
            raise Exception("❌ Response was cut off (token limit hit). Try a simpler request or break it into parts.")
        
        # Track cost
        if response.usage:
            cost_tracker.track(
                model=settings.OPENAI_MODEL,
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens
            )
        
        return response
    
    async def _execute_tool(
        self, 
        function_name: str, 
        arguments: dict,
        tool_mapping: dict
    ) -> ToolResult:
        """Execute a tool and return result"""
        tool_name = tool_mapping.get(function_name)
        
        if not tool_name:
            return ToolResult(
                success=False,
                error=f"Unknown function: {function_name}"
            )
        
        tool = get_tool(tool_name)
        if not tool:
            return ToolResult(
                success=False,
                error=f"Tool not found: {tool_name}"
            )
        
        return await tool.execute(function_name, arguments)
    
    def _extract_data_from_result(self, function_name: str, result: ToolResult) -> dict:
        """
        Extract structured data from tool results.
        Override in subclasses for domain-specific extraction.
        """
        if result.data:
            return {function_name: result.data}
        return {}
