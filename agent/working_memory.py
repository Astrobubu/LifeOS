"""
Working Memory - State management for the agentic system

Maintains state across:
- Steps within a single plan execution
- Turns within a conversation
- Sessions (persisted to disk)

This is the "scratchpad" that Anthropic recommends for long-horizon tasks.
"""
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Any

from config.settings import settings
from .planning import ExecutionPlan, PlanStep, SubAgentResult


@dataclass
class StepRecord:
    """Record of an executed step with its result"""
    step_id: str
    agent: str
    task: str
    result: SubAgentResult
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        return {
            "step_id": self.step_id,
            "agent": self.agent,
            "task": self.task,
            "result": self.result.to_dict(),
            "timestamp": self.timestamp.isoformat(),
        }


class WorkingMemory:
    """
    Structured state that flows between master and sub-agents.
    
    Key features:
    1. Step results - Context for dependent steps
    2. Session notes - Agent's own observations
    3. User context - Extracted entities and preferences
    4. Persistence - Survives restarts
    """
    
    def __init__(self):
        self.storage_path = settings.STORAGE_DIR / "working_memory"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Current state
        self.current_plan: Optional[ExecutionPlan] = None
        self.step_records: list[StepRecord] = []
        self.session_notes: list[dict] = []
        self.user_context: dict = {}
        
        # Load persisted state
        self._load()
    
    def set_plan(self, plan: ExecutionPlan):
        """Set the current execution plan"""
        self.current_plan = plan
        self._save()
    
    def clear_plan(self):
        """Clear current plan after completion"""
        self.current_plan = None
        self.step_records = []
        self._save()
    
    def record_step(self, step: PlanStep, result: SubAgentResult):
        """Record a completed step for context in future steps"""
        record = StepRecord(
            step_id=step.id,
            agent=step.agent.value,
            task=step.task,
            result=result
        )
        self.step_records.append(record)
        self._save()
    
    def get_context_for_step(self, step: PlanStep) -> dict:
        """
        Build context from previous steps for current step.
        Only includes results from steps this step depends on.
        """
        context = {
            "goal": self.current_plan.goal if self.current_plan else "",
            "previous_results": [],
            "session_notes": self.session_notes[-5:],  # Last 5 notes
            "user_context": self.user_context,
        }
        
        # Add results from dependency steps
        for record in self.step_records:
            if step.depends_on and record.step_id in step.depends_on:
                context["previous_results"].append({
                    "step": record.task,
                    "agent": record.agent,
                    "output": record.result.output,
                    "data": record.result.data,
                })
        
        return context
    
    def get_all_results(self) -> list[dict]:
        """Get all step results for synthesis"""
        return [
            {
                "step_id": r.step_id,
                "agent": r.agent,
                "task": r.task,
                "success": r.result.success,
                "output": r.result.output,
                "data": r.result.data,
                "error": r.result.error,
            }
            for r in self.step_records
        ]
    
    def add_note(self, note: str, category: str = "observation"):
        """
        Agent can add notes to working memory.
        Useful for tracking state, decisions, or observations.
        """
        self.session_notes.append({
            "content": note,
            "category": category,
            "timestamp": datetime.now().isoformat(),
        })
        # Keep last 20 notes
        if len(self.session_notes) > 20:
            self.session_notes = self.session_notes[-20:]
        self._save()
    
    def update_user_context(self, key: str, value: Any):
        """Update user context (entities, preferences)"""
        self.user_context[key] = value
        self._save()
    
    def get_user_context(self, key: str, default: Any = None) -> Any:
        """Get user context value"""
        return self.user_context.get(key, default)
    
    def _save(self):
        """Persist state to disk"""
        state = {
            "current_plan": self.current_plan.to_dict() if self.current_plan else None,
            "step_records": [r.to_dict() for r in self.step_records],
            "session_notes": self.session_notes,
            "user_context": self.user_context,
            "last_updated": datetime.now().isoformat(),
        }
        
        state_file = self.storage_path / "state.json"
        try:
            with open(state_file, "w") as f:
                json.dump(state, f, indent=2)
        except Exception:
            pass  # Non-critical
    
    def _load(self):
        """Load persisted state from disk"""
        state_file = self.storage_path / "state.json"
        if not state_file.exists():
            return
        
        try:
            with open(state_file) as f:
                state = json.load(f)
            
            if state.get("current_plan"):
                self.current_plan = ExecutionPlan.from_dict(state["current_plan"])
            
            self.session_notes = state.get("session_notes", [])
            self.user_context = state.get("user_context", {})
            
            # Note: step_records are not loaded as they're only relevant
            # for the current plan execution
            
        except Exception:
            pass  # Start fresh if load fails
    
    def reset(self):
        """Full reset of working memory"""
        self.current_plan = None
        self.step_records = []
        self.session_notes = []
        self.user_context = {}
        self._save()
