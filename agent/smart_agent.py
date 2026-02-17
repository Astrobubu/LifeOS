"""
SmartAgent v2 - Single clean code path

Flow: Message → LLM Router (1 call) → SubAgent (1-3 calls) = 2-4 LLM calls total
"""
import asyncio
import json
import logging
import base64
from dataclasses import dataclass
from datetime import datetime, timedelta
from openai import AsyncOpenAI

from config.settings import settings
from memory.vector_memory import VectorMemory
from profile.user_profile import get_profile
from tools import get_tool
from tools.base_tool import ToolResult
from .router import LLMRouter, RouteDecision
from .memory_extractor import MemoryExtractor
from .confirmation import confirmation_manager
from .compaction import compactor
from .sub_agents import (
    FinanceSubAgent,
    CalendarSubAgent,
    EmailSubAgent,
    PrintSubAgent,
    AutomationsSubAgent,
    MemorySubAgent,
    GeneralSubAgent,
)
from utils.cost_tracker import cost_tracker

logger = logging.getLogger(__name__)

# Context timeout - clear after 1 hour of inactivity
CONTEXT_TIMEOUT_HOURS = 1


@dataclass
class AgentResponse:
    """Response from agent"""
    text: str
    needs_confirmation: bool = False
    confirmation_action: str = None
    confirmation_description: str = None


# Map agent names to classes
AGENT_MAP = {
    "finance": FinanceSubAgent,
    "calendar": CalendarSubAgent,
    "email": EmailSubAgent,
    "print": PrintSubAgent,
    "automations": AutomationsSubAgent,
    "memory": MemorySubAgent,
    "general": GeneralSubAgent,
}


class SmartAgent:
    """
    SmartAgent v2 - Single code path for every message.

    1. Context timeout check
    2. Get memory context
    3. LLM Router → RouteDecision (1 call)
    4. SubAgent.execute(task, context) (1-3 calls)
    5. Update history, compact if needed
    6. Fire-and-forget memory extraction
    """

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.memory = VectorMemory()
        self.profile = get_profile()
        self.extractor = MemoryExtractor()
        self.router = LLMRouter()
        self.conversation_history: list[dict] = []
        self.last_interaction_time: datetime = datetime.now()

    async def process(self, user_message: str, user_id: int) -> AgentResponse:
        """Main entry point - single code path for every message."""
        logger.info(f"Processing: {user_message[:50]}...")

        # 1. Cancel pending confirmations
        if confirmation_manager.get_pending_action(user_id):
            confirmation_manager.cancel_action(user_id)

        # 2. Context timeout check (1hr) → summarize + clear if stale
        time_since_last = datetime.now() - self.last_interaction_time
        if time_since_last > timedelta(hours=CONTEXT_TIMEOUT_HOURS) and self.conversation_history:
            await self._summarize_and_clear_context()
        self.last_interaction_time = datetime.now()

        # 3. Get memory context
        memory_context = await self.memory.get_context(user_message)

        # 4. Build brief conversation summary for router
        conversation_summary = self._build_conversation_summary()

        # 5. Route (1 LLM call)
        route = await self.router.route(user_message, conversation_summary)
        logger.info(f"Routed to: {route.agent}")

        # 6. Build context dict for sub-agent
        user_profile = self.profile.get_context_for_ai() if self.profile.is_setup else ""
        context = {
            "user_profile": user_profile,
            "memory_context": memory_context or "",
            "conversation_history": self.conversation_history[-8:],
            "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S (%A)"),
        }

        # 7. Execute sub-agent (1-3 LLM calls)
        agent_class = AGENT_MAP.get(route.agent, GeneralSubAgent)
        agent = agent_class()
        result = await agent.execute(route.task, context)

        if not result.success:
            response_text = result.error or "Something went wrong. Please try again."
        else:
            response_text = result.output

        # 8. Update conversation history
        self._update_history(user_message, response_text)

        # 9. Compact if over 20 messages
        if len(self.conversation_history) > 20:
            try:
                self.conversation_history = await compactor.compact(self.conversation_history)
            except Exception:
                self.conversation_history = self.conversation_history[-16:]

        # 10. Fire-and-forget memory extraction
        asyncio.create_task(self._extract_memories(user_message, response_text))

        return AgentResponse(
            text=response_text,
            needs_confirmation=result.needs_confirmation if hasattr(result, 'needs_confirmation') else False,
            confirmation_action=getattr(result, 'confirmation_action', None),
            confirmation_description=getattr(result, 'confirmation_description', None),
        )

    def _build_conversation_summary(self) -> str:
        """Build a brief summary of recent conversation for the router."""
        if not self.conversation_history:
            return ""

        # Last 4 messages as brief summary
        recent = self.conversation_history[-4:]
        parts = []
        for msg in recent:
            role = msg.get("role", "?")
            content = msg.get("content", "")
            if content:
                parts.append(f"{role}: {content[:100]}")
        return "\n".join(parts)

    def _update_history(self, user_msg: str, assistant_msg: str):
        """Update conversation history."""
        self.conversation_history.append({"role": "user", "content": user_msg})
        self.conversation_history.append({"role": "assistant", "content": assistant_msg})

    async def _extract_memories(self, user_msg: str, assistant_msg: str):
        """Extract and store memories from conversation (fire-and-forget)."""
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
                        source="conversation",
                    )
        except Exception:
            pass

    async def _summarize_and_clear_context(self):
        """Summarize old conversation and clear history after timeout."""
        if not self.conversation_history:
            return

        conv_text = "\n".join([
            f"{msg['role'].upper()}: {msg['content'][:200]}"
            for msg in self.conversation_history[-10:]
            if msg.get('content')
        ])

        try:
            response = await self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{
                    "role": "user",
                    "content": f"Summarize this conversation in 1-2 sentences for future reference:\n\n{conv_text}",
                }],
                max_completion_tokens=150,
            )
            summary = response.choices[0].message.content
            if summary:
                await self.memory.add(
                    content=f"Previous session summary: {summary}",
                    memory_type="insight",
                    importance=0.6,
                    source="session_summary",
                )
                logger.info("Context cleared (1hr timeout)")
        except Exception:
            pass

        self.conversation_history = []

    async def handle_confirmation(self, user_id: int, confirmed: bool) -> str:
        """Handle confirmation button press."""
        if confirmed:
            pending = confirmation_manager.confirm_action(user_id)
            if pending:
                tool = get_tool(self._action_to_tool(pending.action_name))
                if tool:
                    result = await tool.execute(pending.action_name, pending.arguments)
                    if result.success:
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

    def _action_to_tool(self, action_name: str) -> str:
        """Map action name to tool name."""
        mapping = {
            "send_email": "gmail",
            "create_event": "calendar",
            "create_reminder": "calendar",
            "delete_event": "calendar",
            "settle_loan": "finance",
            "add_loan": "finance",
        }
        return mapping.get(action_name, action_name)

    async def process_voice(self, audio_bytes: bytes) -> str:
        """Transcribe voice message."""
        transcript = await self.client.audio.transcriptions.create(
            model="whisper-1",
            file=("voice.ogg", audio_bytes, "audio/ogg"),
        )
        return transcript.text

    async def process_image(self, image_bytes: bytes, caption: str = "", user_id: int = 0) -> AgentResponse:
        """Process image with vision model, detect intent, and route."""
        b64 = base64.b64encode(image_bytes).decode()

        # Step 1: Extract info from image
        extraction_prompt = f"""Extract the MAIN CONTENT from this image. Focus on what matters.

User's caption: {caption or "No caption"}

CRITICAL RULES:
1. IGNORE phone/device UI elements: status bar, battery %, signal, time, network speed
2. IGNORE screenshot chrome, navigation bars, system UI
3. Focus ONLY on the ACTUAL CONTENT - the main subject of the image
4. Extract: event names, dates, times, locations, names, amounts, descriptions
5. If it's a screenshot of an event/appointment/message - extract THAT content

Output format:
- Main Content: [the actual important information]
- Key Details: [dates, times, names, locations, amounts if any]"""

        try:
            response = await self.client.chat.completions.create(
                model=settings.OPENAI_VISION_MODEL,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": extraction_prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                    ],
                }],
                max_completion_tokens=5000,
            )

            if response.usage:
                cost_tracker.track(
                    model=settings.OPENAI_VISION_MODEL,
                    input_tokens=response.usage.prompt_tokens,
                    output_tokens=response.usage.completion_tokens,
                )

            image_info = response.choices[0].message.content
            if not image_info or len(image_info.strip()) == 0:
                image_info = "Unable to extract information from this image."
        except Exception as e:
            logger.error(f"Vision error: {e}")
            return AgentResponse(text=f"Could not analyze image: {str(e)[:150]}")

        # Step 2: Detect intent
        intent_result = await self._detect_image_intent(caption, image_info)
        intent = intent_result.get("intent", "analyze")
        confidence = intent_result.get("confidence", 0.5)

        # Step 3: Store image as memory (background)
        asyncio.create_task(self._store_image_memory(image_info, caption, intent))

        # Step 4: Act based on intent
        if intent == "calendar" and confidence >= 0.5:
            date_time = intent_result.get("date_time_detected", "")
            response_text = f"I noticed this contains a date/time: **{date_time}**\n\n{image_info}\n\n**Would you like me to add this to your calendar?** Just reply 'yes' or tell me any changes."
            user_msg = f"[User sent an image with date/time] {caption}" if caption else "[User sent an image with date/time]"
            self._update_history(user_msg, response_text)
            return AgentResponse(text=response_text)

        if intent == "print" and confidence >= 0.5:
            print_text = image_info.strip()
            return await self.process(f"Print this: {print_text[:500]}", user_id)

        if confidence >= 0.6 and intent in ["contact", "save_note", "remember"] and user_id:
            enhanced = f"Based on this image, the user wants to: {caption}\n\nImage info:\n{image_info}"
            return await self.process(enhanced, user_id)

        # Default: return analysis
        response_text = image_info or "Could not analyze image."
        user_msg = f"[User sent an image] {caption}" if caption else "[User sent an image]"
        self._update_history(user_msg, response_text)
        return AgentResponse(text=response_text)

    async def _detect_image_intent(self, caption: str, extracted_info: str) -> dict:
        """Detect user intent from image caption using LLM."""
        if not caption or len(caption.strip()) < 3:
            return {"intent": "analyze", "confidence": 0.9}

        intent_prompt = f"""Analyze the user's caption and determine their intent for this image.

Caption: "{caption}"
Image content summary: {extracted_info[:300]}

Possible intents:
- calendar: image contains a DATE, TIME, APPOINTMENT, or EVENT
- print: wants to PRINT this (keywords: print, printer, output)
- contact: wants to reach out to someone
- save_note: wants to save this information
- remember: wants to store specific facts
- analyze: just wants analysis/explanation
- no_action: casual sharing

Return JSON with:
{{"intent": "...", "confidence": 0.0-1.0, "reasoning": "...", "suggested_action": "...", "date_time_detected": null}}"""

        try:
            response = await self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{"role": "user", "content": intent_prompt}],
                temperature=1,
                max_completion_tokens=200,
                response_format={"type": "json_object"},
            )
            if response.usage:
                cost_tracker.track(
                    model=settings.OPENAI_MODEL,
                    input_tokens=response.usage.prompt_tokens,
                    output_tokens=response.usage.completion_tokens,
                )
            return json.loads(response.choices[0].message.content)
        except Exception:
            return {"intent": "analyze", "confidence": 0.5}

    async def _store_image_memory(self, image_info: str, caption: str, intent: str):
        """Store image description as memory (fire-and-forget)."""
        try:
            memory_content = f"Image received: {image_info[:400]}"
            await self.memory.add(
                content=memory_content,
                memory_type="image_memory",
                importance=0.7,
                source="image_upload",
                metadata={
                    "caption": caption or "",
                    "timestamp": datetime.now().isoformat(),
                    "detected_intent": intent,
                },
            )
        except Exception:
            pass

    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []

    def get_memory_stats(self) -> dict:
        """Get memory statistics."""
        return self.memory.get_stats()

    @property
    def needs_setup(self) -> bool:
        return not self.profile.is_setup

    def setup_profile(self, **kwargs):
        self.profile.setup(**kwargs)

    def update_profile(self, **kwargs):
        self.profile.update(**kwargs)

    def get_profile_data(self) -> dict:
        return self.profile.data
