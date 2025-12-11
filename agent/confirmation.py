"""
Confirmation system for sensitive actions - uses buttons, not text
"""
import json
import uuid
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime, timedelta

# Actions that require confirmation - ONLY final/destructive actions
SENSITIVE_ACTIONS = {
    # Email
    "send_email": "Send email to {to} - Subject: {subject}",
    # Calendar
    "create_event": "Create event: {title} at {start_time}",
    "create_reminder": "Set reminder: {title} at {when}",
    "delete_event": "Delete calendar event",
    # Finance
    "settle_loan": "Mark loan as settled",
    # Deletions
    "delete_note": "Delete note '{title}'",
    "delete_task": "Delete task",
}

@dataclass
class PendingAction:
    action_name: str
    arguments: dict
    description: str
    action_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: datetime = field(default_factory=lambda: datetime.now() + timedelta(minutes=5))
    
    def is_expired(self) -> bool:
        return datetime.now() > self.expires_at


class ConfirmationManager:
    def __init__(self):
        self.pending_actions: dict[int, PendingAction] = {}  # user_id -> pending action
    
    def requires_confirmation(self, action_name: str) -> bool:
        """Check if an action requires confirmation"""
        return action_name in SENSITIVE_ACTIONS
    
    def create_pending_action(
        self,
        user_id: int,
        action_name: str,
        arguments: dict
    ) -> PendingAction:
        """Create a pending action awaiting confirmation"""
        # Format description with all available details
        template = SENSITIVE_ACTIONS.get(action_name, action_name)
        
        # Build a safe arguments dict with defaults
        safe_args = {k: v for k, v in arguments.items() if v is not None}
        
        try:
            description = template.format(**safe_args)
        except KeyError:
            # If template fields missing, build a readable description
            parts = [action_name.replace("_", " ").title()]
            for key, val in safe_args.items():
                if key not in ['reminder_minutes', 'description'] and val:
                    parts.append(f"{key}: {val}")
            description = " | ".join(parts)
        
        # Add timezone info for calendar events
        if action_name in ["create_event", "create_reminder"]:
            from tools.calendar_tool import DEFAULT_TIMEZONE
            description += f" ({DEFAULT_TIMEZONE})"
        
        pending = PendingAction(
            action_name=action_name,
            arguments=arguments,
            description=description,
        )
        
        # Add expiry warning to description
        pending.description += "\n\n⏱️ _Expires in 5 minutes_"
        
        self.pending_actions[user_id] = pending
        return pending
    
    def get_pending_action(self, user_id: int) -> Optional[PendingAction]:
        """Get pending action for user if exists and not expired"""
        pending = self.pending_actions.get(user_id)
        if pending:
            if pending.is_expired():
                del self.pending_actions[user_id]
                return None
            return pending
        return None
    
    def confirm_action(self, user_id: int) -> Optional[PendingAction]:
        """Confirm and return the pending action, then clear it"""
        pending = self.get_pending_action(user_id)
        if pending:
            del self.pending_actions[user_id]
            return pending
        return None
    
    def cancel_action(self, user_id: int) -> bool:
        """Cancel pending action"""
        if user_id in self.pending_actions:
            del self.pending_actions[user_id]
            return True
        return False


# Global instance
confirmation_manager = ConfirmationManager()
