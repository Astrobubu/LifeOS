"""
Token and Cost Tracking
"""
import json
from datetime import datetime, date
from pathlib import Path
from config.settings import settings

COSTS_FILE = settings.STORAGE_DIR / "usage_costs.json"

# Pricing per 1M tokens (as of model config)
PRICING = {
    "gpt-5-mini": {"input": 0.25, "output": 2.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini-transcribe": {"input": 1.25, "output": 5.00},  # per 1M tokens
    "text-embedding-3-small": {"input": 0.02, "output": 0},
}


class CostTracker:
    def __init__(self):
        self.data = self._load()
    
    def _load(self) -> dict:
        if COSTS_FILE.exists():
            with open(COSTS_FILE, "r") as f:
                return json.load(f)
        return {
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_cost": 0.0,
            "by_date": {},
            "by_model": {}
        }
    
    def _save(self):
        COSTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(COSTS_FILE, "w") as f:
            json.dump(self.data, f, indent=2)
    
    def track(self, model: str, input_tokens: int, output_tokens: int):
        """Track token usage"""
        today = date.today().isoformat()
        
        # Get pricing for model
        pricing = PRICING.get(model, PRICING.get("gpt-4o-mini"))
        
        # Calculate cost
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        total_cost = input_cost + output_cost
        
        # Update totals
        self.data["total_input_tokens"] += input_tokens
        self.data["total_output_tokens"] += output_tokens
        self.data["total_cost"] += total_cost
        
        # Update by date
        if today not in self.data["by_date"]:
            self.data["by_date"][today] = {"input": 0, "output": 0, "cost": 0.0}
        self.data["by_date"][today]["input"] += input_tokens
        self.data["by_date"][today]["output"] += output_tokens
        self.data["by_date"][today]["cost"] += total_cost
        
        # Update by model
        if model not in self.data["by_model"]:
            self.data["by_model"][model] = {"input": 0, "output": 0, "cost": 0.0}
        self.data["by_model"][model]["input"] += input_tokens
        self.data["by_model"][model]["output"] += output_tokens
        self.data["by_model"][model]["cost"] += total_cost
        
        self._save()
        return total_cost
    
    def get_today_stats(self) -> dict:
        """Get today's usage"""
        today = date.today().isoformat()
        return self.data["by_date"].get(today, {"input": 0, "output": 0, "cost": 0.0})
    
    def get_total_stats(self) -> dict:
        """Get total usage"""
        return {
            "total_input_tokens": self.data["total_input_tokens"],
            "total_output_tokens": self.data["total_output_tokens"],
            "total_cost": self.data["total_cost"],
            "days_tracked": len(self.data["by_date"])
        }
    
    def get_summary(self) -> str:
        """Get formatted summary"""
        today = self.get_today_stats()
        total = self.get_total_stats()
        
        return f"""📊 **Usage Stats**

**Today:**
• Input: {today['input']:,} tokens
• Output: {today['output']:,} tokens
• Cost: ${today['cost']:.4f}

**All Time:**
• Input: {total['total_input_tokens']:,} tokens
• Output: {total['total_output_tokens']:,} tokens
• Total Cost: ${total['total_cost']:.4f}
• Days Tracked: {total['days_tracked']}"""
    
    def reset(self):
        """Reset all tracking data"""
        self.data = {
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_cost": 0.0,
            "by_date": {},
            "by_model": {}
        }
        self._save()


# Global instance
cost_tracker = CostTracker()
