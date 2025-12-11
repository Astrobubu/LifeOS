"""
Automatic Memory Extraction
Analyzes conversations and extracts important information without user asking
"""
import json
from openai import AsyncOpenAI
from config.settings import settings


EXTRACTION_PROMPT = """Analyze this conversation and extract any important information worth remembering long-term.

Conversation:
User: {user_message}
Assistant: {assistant_message}

Extract information in these categories:
- fact: Concrete facts about the user (name, job, location, relationships, etc.)
- preference: User preferences (likes, dislikes, how they want things done)
- event: Important events (meetings, deadlines, appointments mentioned)
- insight: Patterns or insights about the user's behavior/needs
- task: Commitments or tasks mentioned (things user needs to do)

Rules:
1. Only extract genuinely useful long-term information
2. Don't extract trivial or temporary things
3. Be specific - "user likes coffee" not "user mentioned a beverage"
4. Rate importance 0.0-1.0 (1.0 = critical to remember)
5. If nothing worth remembering, return empty array

Output JSON:
{
    "memories": [
        {
            "content": "specific information to remember",
            "type": "fact|preference|event|insight|task",
            "importance": 0.0-1.0,
            "reasoning": "why this is worth remembering"
        }
    ]
}

Return {"memories": []} if nothing worth storing.
"""


class MemoryExtractor:
    """Automatically extracts memorable information from conversations"""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    
    async def extract(self, user_message: str, assistant_message: str) -> list[dict]:
        """Extract memories from a conversation exchange"""
        
        # Skip very short exchanges
        if len(user_message) < 20 and len(assistant_message) < 50:
            return []
        
        prompt = EXTRACTION_PROMPT.format(
            user_message=user_message,
            assistant_message=assistant_message
        )
        
        try:
            response = await self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=1,
                max_completion_tokens=500,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            if not content:
                return []
            
            result = json.loads(content)
            memories = result.get("memories", [])
            
            if not isinstance(memories, list):
                return []
            
            # Filter out low importance
            return [m for m in memories if isinstance(m, dict) and m.get("importance", 0) >= 0.4]
            
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            # Silently fail - memory extraction is not critical
            return []
        except Exception:
            return []
    
    async def extract_from_input(self, user_message: str) -> list[dict]:
        """Extract memories from user input alone (before response)"""
        
        if len(user_message) < 30:
            return []
        
        prompt = f"""Extract any important facts from this user message that should be remembered.

User message: {user_message}

Only extract clear facts, preferences, or events. Not questions or requests.

Output JSON:
{{"memories": [{{"content": "...", "type": "fact|preference|event", "importance": 0.0-1.0}}]}}

Return {{"memories": []}} if nothing to extract.
"""
        
        try:
            response = await self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=1,
                max_completion_tokens=300,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            if not content:
                return []
                
            result = json.loads(content)
            memories = result.get("memories", [])
            
            if not isinstance(memories, list):
                return []
                
            return [m for m in memories if isinstance(m, dict) and m.get("importance", 0) >= 0.5]
            
        except Exception:
            return []
