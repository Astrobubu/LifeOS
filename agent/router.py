"""
LLM Router - Single LLM call to classify and route user messages.

Replaces the old regex fast-path + MasterAgent planning with one cheap call.
"""
import json
import logging
from dataclasses import dataclass
from openai import AsyncOpenAI

from config.settings import settings
from utils.cost_tracker import cost_tracker

logger = logging.getLogger(__name__)

ROUTER_PROMPT = """You are a message router for HAL 9000, a personal assistant.

Classify the user's message into ONE agent and rewrite it as a clear task.

## Agents
- finance: loans, debts, money owed, payments, "I owe", "owes me"
- calendar: events, schedule, meetings, "remind me at [time]", appointments, "what's today"
- email: emails, inbox, send email, compose, reply
- memory: "remember that", "what did I say about", store/recall information, notes
- print: "print X", "task X", "add task", physical printouts
- automations: "every day/week/hour do X", "reprint X", "run X again", recurring, scheduled
- general: casual chat, questions, greetings, anything that doesn't fit above

## Priority Rules (check in order)
1. "reprint X" or "run X again" → automations
2. "every day/week/hour" or recurring → automations
3. "remind me at [specific time]" → calendar
4. "print" or "task" (one-time) → print
5. Money/loan keywords → finance
6. Email keywords → email
7. Memory/remember keywords → memory
8. Everything else → general

## Context
{context}

Return JSON: {{"agent": "...", "task": "..."}}
- agent: one of the agent names above
- task: clear instruction for that agent (rewrite ambiguous messages into clear tasks)
"""


@dataclass
class RouteDecision:
    agent: str
    task: str


class LLMRouter:
    """Routes messages to the right sub-agent with a single LLM call."""

    VALID_AGENTS = {"finance", "calendar", "email", "memory", "print", "automations", "general"}

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def route(self, user_message: str, conversation_summary: str = "") -> RouteDecision:
        """Route a user message to the appropriate agent."""
        context = conversation_summary if conversation_summary else "No prior conversation."

        prompt = ROUTER_PROMPT.format(context=context)

        try:
            response = await self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": user_message},
                ],
                response_format={"type": "json_object"},
                temperature=1,
                max_completion_tokens=300,
            )

            if response.usage:
                cost_tracker.track(
                    model=settings.OPENAI_MODEL,
                    input_tokens=response.usage.prompt_tokens,
                    output_tokens=response.usage.completion_tokens,
                )

            content = response.choices[0].message.content
            result = json.loads(content)

            agent = result.get("agent", "general")
            task = result.get("task", user_message)

            # Validate agent name
            if agent not in self.VALID_AGENTS:
                logger.warning(f"Router returned invalid agent '{agent}', falling back to general")
                agent = "general"

            logger.info(f"Router: '{user_message[:40]}...' -> {agent}")
            return RouteDecision(agent=agent, task=task)

        except Exception as e:
            logger.error(f"Router error: {e}")
            return RouteDecision(agent="general", task=user_message)
