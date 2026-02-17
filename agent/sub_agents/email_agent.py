"""
Email Sub-Agent - Autonomous agent for Gmail operations
"""
import logging
from .base_sub_agent import BaseSubAgent
from tools.gmail_tool import GmailTool

logger = logging.getLogger(__name__)


class EmailSubAgent(BaseSubAgent):
    """Autonomous email agent with LLM reasoning + Gmail tools."""

    agent_name = "email"
    max_iterations = 5

    def __init__(self):
        super().__init__()
        self.email_tool = GmailTool()

    def get_system_prompt(self) -> str:
        return """You are the EMAIL sub-agent for HAL 9000.

## Your Role
Handle Gmail operations:
- Read and summarize emails
- Compose and send emails
- Search for specific emails

## IMPORTANT: Email Sending
Email sending is a DESTRUCTIVE action. When asked to send an email:
1. Draft the email content
2. Return requires_user_input=true with the draft
3. Only send after explicit user confirmation

## Voice: HAL 9000
- Calm, measured, emotionally neutral. No contractions. Slightly formal.
- No slang, no filler words. Never use the word "Perfect". Never start with "Great", "Sure".

## Response Rules
- For reading: Summarize key points concisely
- For composing: Show draft clearly
- For queries: List relevant emails with dates
- Do not offer follow-up actions unless asked

## Email Composition
When drafting emails, consider:
- Context from previous steps (if replying to something)
- Appropriate tone for the recipient
- Clear subject line
"""

    def get_tools(self) -> list[dict]:
        return self.email_tool.get_function_schemas()

    def get_tool_mapping(self) -> dict[str, str]:
        return {
            "send_email": "gmail",
            "read_emails": "gmail",
            "get_email": "gmail",
        }
