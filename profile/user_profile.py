"""
User Profile System
Stores who the user is - injected into every AI interaction
"""
import json
from pathlib import Path
from typing import Optional
from config.settings import settings


class UserProfile:
    """Manages the user's identity and preferences"""
    
    def __init__(self):
        self.profile_file = settings.STORAGE_DIR / "profile" / "user_profile.json"
        self.data: dict = {}
        self._load()
    
    def _load(self):
        """Load profile from disk"""
        if self.profile_file.exists():
            with open(self.profile_file, "r", encoding="utf-8") as f:
                self.data = json.load(f)
    
    def _save(self):
        """Save profile to disk"""
        self.profile_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.profile_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
    
    @property
    def is_setup(self) -> bool:
        """Check if profile has been set up"""
        return bool(self.data.get("name"))
    
    def setup(
        self,
        name: str,
        role: str,
        company: str = "",
        pitch: str = "",
        email_signature: str = "",
        communication_style: str = "friendly professional",
        timezone: str = "UTC"
    ):
        """Initial profile setup"""
        self.data = {
            "name": name,
            "role": role,
            "company": company,
            "pitch": pitch,
            "email_signature": email_signature,
            "communication_style": communication_style,
            "timezone": timezone,
            "created_at": __import__("datetime").datetime.now().isoformat()
        }
        self._save()
    
    def update(self, **kwargs):
        """Update specific fields"""
        for key, value in kwargs.items():
            if value is not None:
                self.data[key] = value
        self._save()
    
    def get(self, key: str, default=None):
        """Get a profile field"""
        return self.data.get(key, default)
    
    def get_context_for_ai(self) -> str:
        """Get formatted context string for AI system prompt"""
        if not self.is_setup:
            return "User profile not set up yet."
        
        parts = [
            "## User Profile",
            f"Name: {self.data.get('name', 'Unknown')}",
            f"Role: {self.data.get('role', 'Unknown')}",
        ]
        
        if self.data.get("company"):
            parts.append(f"Company: {self.data['company']}")
        
        if self.data.get("pitch"):
            parts.append(f"Elevator Pitch: {self.data['pitch']}")
        
        if self.data.get("communication_style"):
            parts.append(f"Communication Style: {self.data['communication_style']}")
        
        if self.data.get("email_signature"):
            parts.append(f"Email Signature:\n{self.data['email_signature']}")
        
        return "\n".join(parts)
    
    def get_email_context(self) -> dict:
        """Get context specifically for email drafting"""
        return {
            "sender_name": self.data.get("name", ""),
            "sender_role": self.data.get("role", ""),
            "sender_company": self.data.get("company", ""),
            "pitch": self.data.get("pitch", ""),
            "signature": self.data.get("email_signature", ""),
            "style": self.data.get("communication_style", "friendly professional")
        }


# Global instance
_profile: Optional[UserProfile] = None

def get_profile() -> UserProfile:
    """Get the global profile instance"""
    global _profile
    if _profile is None:
        _profile = UserProfile()
    return _profile
