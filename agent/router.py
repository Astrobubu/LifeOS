"""
Intent Router - Classifies user messages and routes to specialized handlers
Following Anthropic's routing workflow pattern
"""
from dataclasses import dataclass
from typing import Optional
import re


@dataclass
class RoutingResult:
    """Result of intent classification"""
    handler: str  # Handler name to use
    intent: str  # Detected intent
    confidence: float  # 0-1 confidence score
    entities: dict  # Extracted entities (names, amounts, etc.)


class IntentRouter:
    """
    Lightweight intent classifier that routes messages to specialized handlers.
    Uses keyword matching + entity detection (no LLM call needed for routing).
    """
    
    # Intent patterns - order matters (more specific first)
    INTENT_PATTERNS = {
        # Finance/Loans - very specific patterns
        "finance": {
            "keywords": [
                "owe", "owes", "owed", "loan", "lend", "lent", "borrow", "borrowed",
                "debt", "pay back", "paid back", "repay", "settle", "settled",
                "money", "cash", "aed", "usd", "sar", "egp", "dirhams", "dollars",
                "how much do i owe", "who owes me", "loan summary"
            ],
            "patterns": [
                r"i owe (\w+)",
                r"(\w+) owes me",
                r"borrowed .* from (\w+)",
                r"lent .* to (\w+)",
                r"(\d+) (?:aed|usd|dirhams|\$)",
            ],
            "handler": "finance"
        },
        
        # Tasks/Reminders
        "tasks": {
            "keywords": [
                "task", "tasks", "todo", "to-do", "to do", "remind", "reminder",
                "add task", "new task", "complete task", "done with", "finish",
                "pending", "overdue", "deadline", "due date", "priority"
            ],
            "patterns": [
                r"remind me to",
                r"add (?:a )?task",
                r"mark .* (?:as )?(?:done|complete)",
                r"what.*(?:tasks|todos)",
            ],
            "handler": "tasks"
        },
        
        # Notes
        "notes": {
            "keywords": [
                "note", "notes", "write down", "jot down", "draft", "document",
                "save this", "remember this", "keep note", "my notes"
            ],
            "patterns": [
                r"(?:create|make|write|save) (?:a )?note",
                r"note about",
                r"search (?:my )?notes",
            ],
            "handler": "notes"
        },
        
        # Calendar/Schedule
        "calendar": {
            "keywords": [
                "calendar", "schedule", "event", "meeting", "appointment",
                "tomorrow", "next week", r"at \d+(?:am|pm)", "o'clock",
                "today's schedule", "what's on", "busy", "free time"
            ],
            "patterns": [
                r"schedule (?:a|an)?",
                r"(?:create|add|set) (?:an? )?(?:event|meeting|appointment)",
                r"what(?:'s| is) (?:on )?(?:my )?(?:schedule|calendar)",
                r"(?:am i |are we )?(?:free|busy|available)",
            ],
            "handler": "calendar"
        },
        
        # Email
        "email": {
            "keywords": [
                "email", "mail", "inbox", "send email", "compose", "reply",
                "unread", "gmail", "message to", "write to"
            ],
            "patterns": [
                r"send (?:an? )?(?:email|mail) to",
                r"check (?:my )?(?:email|inbox|mail)",
                r"read (?:my )?emails",
                r"email from",
            ],
            "handler": "email"
        },
        
        # Print - Direct action, highest priority when detected
        "print": {
            "keywords": [
                "print", "printer", "printout", "print this", "print out"
            ],
            "patterns": [
                r"^print\b",
                r"print (?:this|it|the)",
            ],
            "handler": "print"
        },
        
        # Web/Search
        "web": {
            "keywords": [
                "search", "google", "look up", "find out", "what is", "who is",
                "weather", "news", "browse", "website"
            ],
            "patterns": [
                r"search (?:for|about)",
                r"what(?:'s| is) the weather",
                r"look up",
            ],
            "handler": "web"
        },
    }
    
    def __init__(self, known_entities: dict = None):
        """
        Initialize router with known entities for better detection.
        
        Args:
            known_entities: Dict of entity types to values, e.g.:
                {"loan_people": ["Dad", "Mom", "Ali"], "task_projects": ["Work", "Home"]}
        """
        self.known_entities = known_entities or {}
    
    def update_entities(self, entity_type: str, values: list):
        """Update known entities for better routing"""
        self.known_entities[entity_type] = [v.lower() for v in values]
    
    def route(self, message: str, conversation_context: list = None) -> RoutingResult:
        """
        Route a message to the appropriate handler.
        
        Args:
            message: User message to classify
            conversation_context: Recent messages for follow-up detection
            
        Returns:
            RoutingResult with handler, intent, confidence, and entities
        """
        msg_lower = message.lower().strip()
        
        # Check for follow-up context first
        if conversation_context:
            follow_up_result = self._check_follow_up(msg_lower, conversation_context)
            if follow_up_result:
                return follow_up_result
        
        # Score each intent
        scores = {}
        entities = {}
        
        for intent, config in self.INTENT_PATTERNS.items():
            score, found_entities = self._score_intent(msg_lower, config)
            scores[intent] = score
            if found_entities:
                entities.update(found_entities)
        
        # Check for known entities (loan people, etc.)
        entity_boost = self._check_known_entities(msg_lower)
        for intent, boost in entity_boost.items():
            scores[intent] = scores.get(intent, 0) + boost
        
        # Get best match
        if scores:
            best_intent = max(scores, key=scores.get)
            best_score = scores[best_intent]
            
            # Normalize to 0-1 confidence
            confidence = min(best_score / 3.0, 1.0)  # 3+ matches = 100% confidence
            
            if confidence >= 0.3:  # Minimum threshold
                return RoutingResult(
                    handler=self.INTENT_PATTERNS[best_intent]["handler"],
                    intent=best_intent,
                    confidence=confidence,
                    entities=entities
                )
        
        # Default to general handler
        return RoutingResult(
            handler="general",
            intent="general",
            confidence=0.5,
            entities=entities
        )
    
    def _score_intent(self, message: str, config: dict) -> tuple[float, dict]:
        """Score how well a message matches an intent config"""
        score = 0
        entities = {}
        
        # Keyword matching
        for keyword in config["keywords"]:
            if keyword in message:
                score += 1
                # Boost for exact/strong matches
                if message.startswith(keyword) or f" {keyword}" in message:
                    score += 0.5
        
        # Pattern matching
        for pattern in config.get("patterns", []):
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                score += 1.5  # Patterns are stronger signals
                # Extract entities from groups
                if match.groups():
                    entities["matched_groups"] = match.groups()
        
        return score, entities
    
    def _check_known_entities(self, message: str) -> dict:
        """Check for known entities and return intent boosts"""
        boosts = {}
        
        # Check loan-related people
        if "loan_people" in self.known_entities:
            for person in self.known_entities["loan_people"]:
                if person in message:
                    boosts["finance"] = boosts.get("finance", 0) + 2  # Strong boost
        
        # Can add more entity checks here
        
        return boosts
    
    def _check_follow_up(self, message: str, context: list) -> Optional[RoutingResult]:
        """Check if this is a follow-up to a previous handler"""
        # Short messages that look like responses
        if len(message.split()) <= 5:
            # Check for affirmative/corrective responses
            affirmatives = ["yes", "yeah", "yep", "correct", "right", "ok", "okay", "sure"]
            negatives = ["no", "nope", "wrong", "not", "idiot", "incorrect"]
            
            if any(word in message for word in affirmatives + negatives):
                # Look at last assistant message to determine context
                for msg in reversed(context[-4:]):
                    if msg.get("role") == "assistant":
                        content = msg.get("content", "").lower()
                        # Detect what domain the last response was about
                        if any(word in content for word in ["loan", "owe", "owes", "debt"]):
                            return RoutingResult(
                                handler="finance",
                                intent="finance_correction",
                                confidence=0.8,
                                entities={"is_correction": True}
                            )
                        if any(word in content for word in ["task", "reminder", "todo"]):
                            return RoutingResult(
                                handler="tasks",
                                intent="tasks_correction",
                                confidence=0.8,
                                entities={"is_correction": True}
                            )
        
        return None
