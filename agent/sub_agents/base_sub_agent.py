"""
Base Sub-Agent - Abstract base class for all autonomous sub-agents (v2)

Each sub-agent:
1. Has its own LLM with domain-specific prompt
2. Has access to domain-specific tools
3. Operates in an AGENTIC LOOP until task complete
4. Receives conversation context from SmartAgent
"""
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from openai import AsyncOpenAI

from config.settings import settings
from tools import get_tool
from tools.base_tool import ToolResult
from utils.cost_tracker import cost_tracker

logger = logging.getLogger(__name__)


class SubAgentResult:
    """Result returned by a sub-agent after executing a task."""

    def __init__(
        self,
        success: bool,
        output: str,
        data: dict = None,
        error: str = None,
        needs_confirmation: bool = False,
        confirmation_action: str = None,
        confirmation_description: str = None,
    ):
        self.success = success
        self.output = output
        self.data = data or {}
        self.error = error
        self.needs_confirmation = needs_confirmation
        self.confirmation_action = confirmation_action
        self.confirmation_description = confirmation_description


class BaseSubAgent(ABC):
    """
    Abstract base class for autonomous sub-agents (v2).

    Key change from v1: sub-agents now receive conversation history
    and memory context via the context dict, so they understand
    references like "the event I just mentioned".
    """

    agent_name: str = "base"
    max_iterations: int = 10

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

        Runs an AGENTIC LOOP:
        1. Send task + context to LLM
        2. If LLM returns tool calls, execute them
        3. Add tool results to conversation
        4. Repeat until LLM returns final response (no tool calls)
        """
        logger.info(f"[{self.agent_name}] Starting: {task[:60]}...")

        messages = self._build_messages(task, context)
        tools = self.get_tools()
        tool_mapping = self.get_tool_mapping()

        iterations = 0

        while iterations < self.max_iterations:
            iterations += 1

            try:
                response = await self._call_llm(messages, tools)

                if response.choices[0].message.tool_calls:
                    tool_calls = response.choices[0].message.tool_calls
                    messages.append(response.choices[0].message)

                    for tc in tool_calls:
                        func_name = tc.function.name
                        try:
                            args = json.loads(tc.function.arguments)
                        except json.JSONDecodeError:
                            args = {}

                        logger.info(f"[{self.agent_name}] Tool: {func_name}")
                        result = await self._execute_tool(func_name, args, tool_mapping)

                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": json.dumps(result.to_dict()),
                        })
                    continue

                # No tool calls = done
                final_response = response.choices[0].message.content or ""
                logger.info(f"[{self.agent_name}] Complete ({iterations} iterations)")

                return SubAgentResult(success=True, output=final_response)

            except Exception as e:
                logger.error(f"[{self.agent_name}] Error: {e}")
                return SubAgentResult(success=False, output="", error=str(e))

        # Max iterations
        return SubAgentResult(
            success=False,
            output="Max iterations reached without completing task.",
            error="iteration_limit",
        )

    def _build_messages(self, task: str, context: dict = None) -> list[dict]:
        """Build initial messages with conversation context injected."""
        system_prompt = self.get_system_prompt()

        if context:
            # Inject user profile
            if context.get("user_profile"):
                system_prompt += f"\n\n## User Profile\n{context['user_profile']}"

            # Inject memory context
            if context.get("memory_context"):
                system_prompt += f"\n\n## Relevant Memories\n{context['memory_context']}"

            # Inject current time
            if context.get("current_time"):
                system_prompt += f"\n\n## Current Time\n{context['current_time']}"

        messages = [{"role": "system", "content": system_prompt}]

        # Inject recent conversation history so sub-agent has context
        if context and context.get("conversation_history"):
            for msg in context["conversation_history"]:
                messages.append(msg)

        messages.append({"role": "user", "content": task})
        return messages

    async def _call_llm(self, messages: list[dict], tools: list[dict] = None):
        """Call OpenAI API with cost tracking."""
        response = await self.client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=messages,
            tools=tools if tools else None,
            tool_choice="auto" if tools else None,
            max_completion_tokens=6000,
        )

        if response.choices[0].finish_reason == "length":
            raise Exception("Response was cut off (token limit). Try a simpler request.")

        if response.usage:
            cost_tracker.track(
                model=settings.OPENAI_MODEL,
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
            )

        return response

    async def _execute_tool(self, function_name: str, arguments: dict, tool_mapping: dict) -> ToolResult:
        """Execute a tool and return result."""
        tool_name = tool_mapping.get(function_name)
        if not tool_name:
            return ToolResult(success=False, error=f"Unknown function: {function_name}")

        tool = get_tool(tool_name)
        if not tool:
            return ToolResult(success=False, error=f"Tool not found: {tool_name}")

        return await tool.execute(function_name, arguments)
