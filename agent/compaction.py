"""
Compaction - Intelligently summarize conversation history before truncation
Following Anthropic's compaction strategy for long-horizon tasks
"""
import json
from typing import Optional
from openai import AsyncOpenAI
from config.settings import settings
from utils.cost_tracker import cost_tracker


class ConversationCompactor:
    """
    Compacts conversation history to preserve important context while
    reducing token count. Key features:
    
    1. Tool result clearing - Remove raw tool outputs (low-value tokens)
    2. Intelligent summarization - Preserve decisions, entities, pending actions
    3. Message consolidation - Combine related exchanges
    """
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    
    def clear_tool_results(self, messages: list[dict]) -> list[dict]:
        """
        Clear tool call results from older messages.
        Tool results are valuable when fresh but low-value once processed.
        Keep only the last 2 tool exchanges intact.
        """
        cleaned = []
        tool_message_count = 0
        
        # Count tool messages from the end
        for msg in reversed(messages):
            if msg.get("role") == "tool":
                tool_message_count += 1
        
        # Keep last 4 tool messages, clear earlier ones
        current_tool_count = 0
        for msg in messages:
            if msg.get("role") == "tool":
                current_tool_count += 1
                if current_tool_count <= tool_message_count - 4:
                    # Clear old tool results, keep just a marker
                    cleaned.append({
                        "role": "tool",
                        "tool_call_id": msg.get("tool_call_id"),
                        "content": "[Result processed]"
                    })
                else:
                    cleaned.append(msg)
            else:
                cleaned.append(msg)
        
        return cleaned
    
    async def summarize_for_compaction(
        self, 
        messages: list[dict], 
        preserve_last_n: int = 4
    ) -> list[dict]:
        """
        Summarize older conversation while preserving recent messages.
        
        Args:
            messages: Full conversation history
            preserve_last_n: Number of recent message pairs to keep intact
            
        Returns:
            Compacted message list with summary + recent messages
        """
        if len(messages) <= preserve_last_n * 2:
            return messages  # Nothing to compact
        
        # Split into old (to summarize) and recent (to keep)
        cutoff = len(messages) - (preserve_last_n * 2)
        old_messages = messages[:cutoff]
        recent_messages = messages[cutoff:]
        
        # Build text to summarize
        summary_text = self._format_for_summary(old_messages)
        
        # Generate summary
        summary = await self._generate_summary(summary_text)
        
        if summary:
            # Create compacted history
            return [
                {"role": "system", "content": f"[Previous conversation summary]\n{summary}"},
                *recent_messages
            ]
        else:
            # Fallback: just truncate
            return recent_messages
    
    def _format_for_summary(self, messages: list[dict]) -> str:
        """Format messages into text for summarization"""
        lines = []
        for msg in messages:
            role = msg.get("role", "unknown").upper()
            content = msg.get("content", "")
            
            # Skip tool messages in summary
            if role == "TOOL":
                continue
            
            # Handle assistant messages with tool calls
            if role == "ASSISTANT" and not content:
                tool_calls = msg.get("tool_calls", [])
                if tool_calls:
                    tools_used = ", ".join(tc.function.name for tc in tool_calls if hasattr(tc, 'function'))
                    content = f"[Called tools: {tools_used}]"
            
            if content:
                # Truncate long content
                if len(content) > 300:
                    content = content[:300] + "..."
                lines.append(f"{role}: {content}")
        
        return "\n".join(lines)
    
    async def _generate_summary(self, conversation_text: str) -> Optional[str]:
        """Generate an intelligent summary of the conversation"""
        if not conversation_text.strip():
            return None
        
        system_prompt = """Summarize this conversation for continuation. Preserve:
1. Key decisions made
2. Important entities (names, amounts, dates)
3. Pending actions or unresolved questions
4. User preferences learned

Be concise but complete. Format as bullet points."""
        
        try:
            response = await self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": conversation_text}
                ],
                max_completion_tokens=300
            )
            
            if response.usage:
                cost_tracker.track(
                    model=settings.OPENAI_MODEL,
                    input_tokens=response.usage.prompt_tokens,
                    output_tokens=response.usage.completion_tokens
                )
            
            return response.choices[0].message.content
            
        except Exception:
            return None
    
    async def compact(
        self, 
        messages: list[dict], 
        max_messages: int = 20
    ) -> list[dict]:
        """
        Full compaction pipeline:
        1. Clear old tool results
        2. Summarize if over limit
        
        Args:
            messages: Conversation history
            max_messages: Maximum messages to keep
            
        Returns:
            Compacted message list
        """
        # Step 1: Clear old tool results
        cleaned = self.clear_tool_results(messages)
        
        # Step 2: Summarize if still too long
        if len(cleaned) > max_messages:
            cleaned = await self.summarize_for_compaction(
                cleaned, 
                preserve_last_n=max_messages // 4
            )
        
        return cleaned


# Singleton instance
compactor = ConversationCompactor()
