import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Base paths
    BASE_DIR = Path(__file__).parent.parent
    STORAGE_DIR = BASE_DIR / "storage"
    MEMORIES_DIR = STORAGE_DIR / "memories"
    TASKS_DIR = STORAGE_DIR / "tasks"
    
    # Telegram
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    ALLOWED_USER_IDS = []
    
    @classmethod
    def _parse_user_ids(cls):
        """Parse user IDs, ignoring invalid values"""
        ids = []
        raw = os.getenv("ALLOWED_USER_IDS", "")
        for uid in raw.split(","):
            uid = uid.strip()
            if uid.isdigit():
                ids.append(int(uid))
        return ids
    
    # OpenAI
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")
    OPENAI_VISION_MODEL = os.getenv("OPENAI_VISION_MODEL", "gpt-5")
    
    # Google OAuth
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
    
    # Bot settings
    BOT_NAME = os.getenv("BOT_NAME", "HAL 9000")
    
    # Memory settings
    MAX_CONTEXT_MEMORIES = 10
    MAX_CONVERSATION_HISTORY = 20
    
    def __init__(self):
        self.ALLOWED_USER_IDS = self._parse_user_ids()
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Create storage directories if they don't exist"""
        for dir_path in [self.MEMORIES_DIR, self.TASKS_DIR]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def validate(self) -> list[str]:
        """Validate required settings, return list of missing items"""
        missing = []
        if not self.TELEGRAM_BOT_TOKEN:
            missing.append("TELEGRAM_BOT_TOKEN")
        if not self.OPENAI_API_KEY:
            missing.append("OPENAI_API_KEY")
        return missing

settings = Settings()
