"""
Planning Schemas - Core data structures for the agentic system

These define the structured outputs that flow between:
- Master Agent (creates plans, synthesizes results)
- Sub-Agents (execute steps, return results)
"""
from dataclasses import dataclass, field
from typing import Optional, Any
from enum import Enum
from datetime import datetime
import json


class StepStatus(Enum):
    """Status of a plan step"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class AgentType(Enum):
    """Available sub-agent types"""
    FINANCE = "finance"
    TASKS = "tasks"  # Legacy - now routes to print
    CALENDAR = "calendar"
    EMAIL = "email"
    NOTES = "notes"  # Legacy - now routes to memory
    WEB = "web"
    PRINT = "print"
    AUTOMATIONS = "automations"  # NEW: All recurring/scheduled actions
    MEMORY = "memory"  # NEW: Notes + memories combined


@dataclass
class PlanStep:
    """
    A single step in an execution plan.
    
    Created by Master Agent, executed by Sub-Agents.
    """
    id: str                          # Unique step identifier
    agent: AgentType                 # Which sub-agent handles this
    task: str                        # Natural language task description
    depends_on: list[str] = field(default_factory=list)  # Step IDs that must complete first
    requires_confirmation: bool = False  # Needs user approval before executing
    status: StepStatus = StepStatus.PENDING
    
    # Filled after execution
    result: Optional['SubAgentResult'] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "agent": self.agent.value,
            "task": self.task,
            "depends_on": self.depends_on,
            "requires_confirmation": self.requires_confirmation,
            "status": self.status.value,
            "result": self.result.to_dict() if self.result else None,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'PlanStep':
        return cls(
            id=data["id"],
            agent=AgentType(data["agent"]),
            task=data["task"],
            depends_on=data.get("depends_on", []),
            requires_confirmation=data.get("requires_confirmation", False),
            status=StepStatus(data.get("status", "pending")),
        )


@dataclass
class ExecutionPlan:
    """
    A plan created by the Master Agent to accomplish a user request.
    
    Contains multiple steps that may have dependencies on each other.
    """
    goal: str                        # Original user request / goal
    steps: list[PlanStep]            # Ordered list of steps
    created_at: datetime = field(default_factory=datetime.now)
    
    # Execution state
    current_step_index: int = 0
    is_complete: bool = False
    requires_user_input: bool = False
    user_input_reason: str = ""
    
    def get_ready_steps(self) -> list[PlanStep]:
        """Get steps that are ready to execute (dependencies met)"""
        completed_ids = {s.id for s in self.steps if s.status == StepStatus.COMPLETED}
        ready = []
        
        for step in self.steps:
            if step.status != StepStatus.PENDING:
                continue
            
            # Check if all dependencies are met
            deps_met = all(dep in completed_ids for dep in step.depends_on)
            if deps_met:
                ready.append(step)
        
        return ready
    
    def get_step(self, step_id: str) -> Optional[PlanStep]:
        """Get a step by ID"""
        for step in self.steps:
            if step.id == step_id:
                return step
        return None
    
    def mark_complete(self):
        """Mark plan as complete"""
        self.is_complete = True
    
    def to_dict(self) -> dict:
        return {
            "goal": self.goal,
            "steps": [s.to_dict() for s in self.steps],
            "created_at": self.created_at.isoformat(),
            "current_step_index": self.current_step_index,
            "is_complete": self.is_complete,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ExecutionPlan':
        return cls(
            goal=data["goal"],
            steps=[PlanStep.from_dict(s) for s in data["steps"]],
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())),
            current_step_index=data.get("current_step_index", 0),
            is_complete=data.get("is_complete", False),
        )


@dataclass
class SubAgentResult:
    """
    Result returned by a sub-agent after executing a step.
    
    Contains both the response text and any structured data.
    """
    success: bool
    output: str                      # Natural language response
    data: dict = field(default_factory=dict)  # Structured data (e.g., loan amounts, task IDs)
    error: Optional[str] = None
    requires_replanning: bool = False  # If true, master should revise the plan
    requires_user_input: bool = False  # If true, need user confirmation/input
    user_input_reason: str = ""
    
    # Metadata
    agent_type: Optional[AgentType] = None
    iterations_used: int = 0          # How many LLM calls the sub-agent made
    tools_called: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "output": self.output,
            "data": self.data,
            "error": self.error,
            "requires_replanning": self.requires_replanning,
            "requires_user_input": self.requires_user_input,
            "user_input_reason": self.user_input_reason,
            "agent_type": self.agent_type.value if self.agent_type else None,
            "iterations_used": self.iterations_used,
            "tools_called": self.tools_called,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'SubAgentResult':
        return cls(
            success=data["success"],
            output=data["output"],
            data=data.get("data", {}),
            error=data.get("error"),
            requires_replanning=data.get("requires_replanning", False),
            requires_user_input=data.get("requires_user_input", False),
            user_input_reason=data.get("user_input_reason", ""),
            agent_type=AgentType(data["agent_type"]) if data.get("agent_type") else None,
            iterations_used=data.get("iterations_used", 0),
            tools_called=data.get("tools_called", []),
        )


@dataclass 
class SynthesisResult:
    """
    Final result from the Master Agent after synthesizing all sub-agent results.
    """
    response: str                    # Final response to user
    needs_confirmation: bool = False  # If any action needs user confirmation
    confirmation_details: str = ""
    plan_summary: Optional[dict] = None  # Summary of what was executed
    
    def to_dict(self) -> dict:
        return {
            "response": self.response,
            "needs_confirmation": self.needs_confirmation,
            "confirmation_details": self.confirmation_details,
            "plan_summary": self.plan_summary,
        }
