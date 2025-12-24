"""
Master Agent - The orchestrator that THINKS, PLANS, and DELEGATES

This is the brain of LifeOS. It:
1. Understands complex user requests using LLM
2. Creates execution plans with multiple steps
3. Delegates to specialized sub-agents
4. Synthesizes results into coherent responses
5. Maintains state through working memory

Following Anthropic's Orchestrator-Workers pattern.
"""
import json
import asyncio
from typing import Optional
from datetime import datetime
from dataclasses import dataclass
from openai import AsyncOpenAI

from config.settings import settings
from memory.vector_memory import VectorMemory
from profile.user_profile import get_profile
from utils.cost_tracker import cost_tracker
from utils.terminal_ui import terminal_ui

from .planning import (
    AgentType,
    ExecutionPlan,
    PlanStep,
    StepStatus,
    SubAgentResult,
    SynthesisResult,
)
from .working_memory import WorkingMemory
from .sub_agents import (
    FinanceSubAgent,
    TasksSubAgent,
    CalendarSubAgent,
    EmailSubAgent,
    NotesSubAgent,
    WebResearchSubAgent,
    PrintSubAgent,
    AutomationsSubAgent,
    MemorySubAgent,
)


@dataclass
class MasterResponse:
    """Response from the Master Agent"""
    text: str
    needs_confirmation: bool = False
    confirmation_action: str = None
    confirmation_description: str = None
    plan_executed: bool = True


# The Master Agent's planning prompt
PLANNER_PROMPT = """You are the MASTER PLANNER for LifeOS.

<role>
You receive a user request and create an execution plan by routing to the correct sub-agent(s).
Your ONLY job is to decide WHICH agent handles the request and WHAT task to give them.
</role>

<agents>
- finance: Loans, debts, money tracking
- automations: Recurring/scheduled actions, reprinting existing scheduled items
- calendar: Events, reminders (remind me = calendar event with notification)
- email: Gmail read/send/search
- memory: Notes, memories, things to remember
- web: Web search and browsing
- print: One-time physical thermal printer output
</agents>

<routing_rules>
Check these rules IN ORDER. First match wins.

1. **REPRINT / RUN AGAIN / TRIGGER EXISTING**
   Keywords: reprint, run again, trigger, execute [automation name]
   → Agent: automations
   → Task: run_automation for the matching automation
   
2. **RECURRING / SCHEDULED**
   Keywords: every day, weekly, daily, recurring, schedule
   → Agent: automations
   
3. **REMIND ME**
   Keywords: remind me, reminder at [time]
   → Agent: calendar (creates event + Telegram notification)
   
4. **REMEMBER / NOTES**
   Keywords: remember that, note, jot down, save this
   → Agent: memory
   
5. **ONE-TIME PRINT**
   Keywords: print [new content], print this [text]
   → Agent: print
   
6. **DEFAULT**: Route based on domain keywords
</routing_rules>

<examples>
User: "reprint laundry"
→ automations: "Run the laundry automation"

User: "print buy milk"  
→ print: "Print task card: buy milk"

User: "remind me at 3pm to call mom"
→ calendar: "Create reminder at 3pm to call mom"

User: "every morning print my schedule"
→ automations: "Create daily automation to print schedule"

User: "I owe dad 100"
→ finance: "Record loan: I owe dad 100"
</examples>

<planning_mode>
SIMPLE (single action):
- One step, no depends_on, no verification
- Examples: print X, remind me, add loan, reprint Y

COMPLEX (multi-step):
- Multiple steps, use depends_on ONLY if step B needs output from step A
- Prefer parallel execution
</planning_mode>

<output>
Always call create_plan with your plan. For simple requests, return exactly 1 step.
</output>
"""

PLANNER_TOOL = {
    "type": "function",
    "function": {
        "name": "create_plan",
        "description": "Create an execution plan to accomplish the user's request",
        "parameters": {
            "type": "object",
            "properties": {
                "goal": {
                    "type": "string",
                    "description": "A brief summary of what the user wants"
                },
                "steps": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {
                                "type": "string",
                                "description": "Unique step ID (e.g., step_1, step_2)"
                            },
                            "agent": {
                                "type": "string",
                                "enum": ["finance", "automations", "calendar", "email", "memory", "web", "print"],
                                "description": "Which sub-agent handles this step (use 'automations' for recurring/scheduled, 'memory' for notes/remember)"
                            },
                            "task": {
                                "type": "string",
                                "description": "Natural language description of what to do"
                            },
                            "depends_on": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Step IDs that must complete first"
                            },
                            "requires_confirmation": {
                                "type": "boolean",
                                "description": "True if this action needs user approval (e.g., sending email)"
                            }
                        },
                        "required": ["id", "agent", "task"]
                    }
                }
            },
            "required": ["goal", "steps"]
        }
    }
}

SYNTHESIZER_PROMPT = """You are synthesizing results from multiple sub-agents into a single coherent response.

## Context
The user asked: {goal}

## Step Results
{results}

## Instructions
1. Combine the results into a natural, conversational response
2. Be concise - don't repeat every detail
3. Highlight what was accomplished
4. If any step failed, mention what went wrong
5. If any step needs user confirmation, make that clear

Respond directly to the user - no meta-commentary about the process.
"""


class MasterAgent:
    """
    The orchestrating master agent.
    
    Uses LLM to:
    - Parse complex requests
    - Create execution plans
    - Delegate to sub-agents
    - Synthesize responses
    """
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.memory = VectorMemory()
        self.profile = get_profile()
        self.working_memory = WorkingMemory()
        
        # Initialize sub-agents
        self.sub_agents = {
            AgentType.FINANCE: FinanceSubAgent(),
            AgentType.TASKS: TasksSubAgent(),
            AgentType.CALENDAR: CalendarSubAgent(),
            AgentType.EMAIL: EmailSubAgent(),
            AgentType.NOTES: NotesSubAgent(),
            AgentType.WEB: WebResearchSubAgent(),
            AgentType.PRINT: PrintSubAgent(),
            AgentType.AUTOMATIONS: AutomationsSubAgent(),
            AgentType.MEMORY: MemorySubAgent(),
        }
        
        # Conversation history for context
        self.conversation_history: list[dict] = []
    
    async def process(self, user_message: str, user_id: int = 0) -> MasterResponse:
        """
        Main entry point - process user message through the agentic system.
        
        Flow:
        1. Create plan using LLM
        2. Execute plan steps (may run in parallel)
        3. Synthesize results
        4. Return response
        """
        terminal_ui.set_status("Planning...")
        terminal_ui.log_activity(f"Master: {user_message[:40]}...")
        
        try:
            # Step 1: Create execution plan
            plan = await self._create_plan(user_message)
            
            if not plan or not plan.steps:
                # Fallback: No plan needed, direct response
                return await self._direct_response(user_message)
            
            terminal_ui.log_activity(f"Plan: {len(plan.steps)} steps")
            self.working_memory.set_plan(plan)
            
            # Step 2: Execute plan
            terminal_ui.set_status("Executing...")
            await self._execute_plan(plan)
            
            # Step 3: Synthesize results
            terminal_ui.set_status("Synthesizing...")
            result = await self._synthesize(plan)
            
            # Update conversation history
            self._update_history(user_message, result.response)
            
            # Clear plan from working memory
            self.working_memory.clear_plan()
            
            terminal_ui.set_status("Running")
            
            return MasterResponse(
                text=result.response,
                needs_confirmation=result.needs_confirmation,
                confirmation_description=result.confirmation_details,
            )
            
        except Exception as e:
            terminal_ui.log_error(f"Master error: {str(e)[:100]}")
            return MasterResponse(
                text=f"I encountered an error: {str(e)}",
                plan_executed=False,
            )
    
    async def _create_plan(self, user_message: str) -> Optional[ExecutionPlan]:
        """Use LLM to create an execution plan"""
        
        # Get memory context
        memory_context = await self.memory.get_context(user_message, max_tokens=300)
        
        # Build planning prompt
        user_name = self.profile.get("name", "User")
        
        messages = [
            {"role": "system", "content": PLANNER_PROMPT},
            {"role": "user", "content": f"""User ({user_name}) says: {user_message}

Relevant memory context:
{memory_context or "No relevant memories."}

Recent conversation:
{self._get_recent_conversation()}

Create a plan to accomplish this request."""}
        ]
        
        try:
            terminal_ui.log_activity(f"[DEBUG] Planning for: {user_message[:50]}...")
            terminal_ui.log_activity(f"[DEBUG] Model: {settings.OPENAI_MODEL}")
            terminal_ui.log_activity(f"[DEBUG] Messages count: {len(messages)}")
            
            response = await self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=messages,
                tools=[PLANNER_TOOL],
                tool_choice={"type": "function", "function": {"name": "create_plan"}},
                max_completion_tokens=6000
            )
            
            terminal_ui.log_activity(f"[DEBUG] Response received, choices: {len(response.choices)}")
            
            # Check for truncation - error directly to user
            if response.choices[0].finish_reason == "length":
                raise Exception("❌ Planning was cut off (token limit hit). Try a simpler request.")
            
            # Track cost
            if response.usage:
                terminal_ui.log_activity(f"[DEBUG] Tokens - in: {response.usage.prompt_tokens}, out: {response.usage.completion_tokens}")
                cost_tracker.track(
                    model=settings.OPENAI_MODEL,
                    input_tokens=response.usage.prompt_tokens,
                    output_tokens=response.usage.completion_tokens
                )
            
            # Check what we got back
            msg = response.choices[0].message
            terminal_ui.log_activity(f"[DEBUG] Message content: {msg.content[:100] if msg.content else 'None'}")
            terminal_ui.log_activity(f"[DEBUG] Tool calls: {msg.tool_calls is not None and len(msg.tool_calls) if msg.tool_calls else 'None'}")
            terminal_ui.log_activity(f"[DEBUG] Finish reason: {response.choices[0].finish_reason}")
            
            # Parse the plan
            if response.choices[0].message.tool_calls:
                tc = response.choices[0].message.tool_calls[0]
                terminal_ui.log_activity(f"[DEBUG] Tool call func: {tc.function.name}")
                terminal_ui.log_activity(f"[DEBUG] Tool call args: {tc.function.arguments[:200]}...")
                
                plan_data = json.loads(tc.function.arguments)
                
                steps = []
                for step_data in plan_data.get("steps", []):
                    steps.append(PlanStep(
                        id=step_data["id"],
                        agent=AgentType(step_data["agent"]),
                        task=step_data["task"],
                        depends_on=step_data.get("depends_on", []),
                        requires_confirmation=step_data.get("requires_confirmation", False),
                    ))
                
                
                terminal_ui.log_activity(f"[DEBUG] Plan created with {len(steps)} steps")
                
                # Log the full plan for debugging
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"PLAN: {json.dumps(plan_data)}")
                
                return ExecutionPlan(
                    goal=plan_data.get("goal", user_message),
                    steps=steps,
                )
            
            terminal_ui.log_error("[DEBUG] No tool_calls in response - returning None")
            return None
            
        except Exception as e:
            terminal_ui.log_error(f"Planning failed: {str(e)[:200]}")
            import traceback
            terminal_ui.log_error(f"Traceback: {traceback.format_exc()[:300]}")
            return None
    
    async def _execute_plan(self, plan: ExecutionPlan):
        """
        Execute plan steps, respecting dependencies.
        Independent steps can run in parallel.
        """
        while True:
            # Get steps that are ready (dependencies met, not yet run)
            ready_steps = plan.get_ready_steps()
            
            if not ready_steps:
                # Check if we're done or stuck
                pending = [s for s in plan.steps if s.status == StepStatus.PENDING]
                if not pending:
                    break  # All done
                else:
                    # Stuck - dependencies not met
                    terminal_ui.log_error("Plan stuck: unmet dependencies")
                    break
            
            # Execute ready steps in parallel
            tasks = []
            for step in ready_steps:
                step.status = StepStatus.RUNNING
                step.started_at = datetime.now()
                tasks.append(self._execute_step(step, plan))
            
            # Wait for all parallel steps
            await asyncio.gather(*tasks)
    
    async def _execute_step(self, step: PlanStep, plan: ExecutionPlan):
        """Execute a single plan step using the appropriate sub-agent"""
        terminal_ui.log_activity(f"Step {step.id}: {step.agent.value}")
        
        # Get context for this step
        context = self.working_memory.get_context_for_step(step)
        
        # Get sub-agent
        sub_agent = self.sub_agents.get(step.agent)
        if not sub_agent:
            step.status = StepStatus.FAILED
            step.result = SubAgentResult(
                success=False,
                output="",
                error=f"No sub-agent for {step.agent.value}"
            )
            return
        
        # Execute
        try:
            result = await sub_agent.execute(step.task, context)
            
            step.status = StepStatus.COMPLETED if result.success else StepStatus.FAILED
            step.result = result
            step.completed_at = datetime.now()
            
            # Record in working memory
            self.working_memory.record_step(step, result)
            
        except Exception as e:
            step.status = StepStatus.FAILED
            step.result = SubAgentResult(
                success=False,
                output="",
                error=str(e)
            )
    
    async def _synthesize(self, plan: ExecutionPlan) -> SynthesisResult:
        """Synthesize all step results into a coherent response"""
        
        # Gather all results
        results = self.working_memory.get_all_results()
        
        if not results:
            return SynthesisResult(response="I couldn't complete your request.")
        
        # Format results for synthesis
        results_text = ""
        for r in results:
            status = "✓" if r["success"] else "✗"
            results_text += f"\n{status} [{r['agent']}] {r['task']}\n"
            results_text += f"   Output: {r['output'][:300]}\n"
            if r.get("error"):
                results_text += f"   Error: {r['error']}\n"
        
        # For simple plans (1 step), just return the output directly
        if len(results) == 1 and results[0]["success"]:
            return SynthesisResult(
                response=results[0]["output"],
                needs_confirmation=any(
                    s.requires_confirmation and s.status == StepStatus.COMPLETED
                    for s in plan.steps
                )
            )
        
        # For complex plans, synthesize with LLM
        prompt = SYNTHESIZER_PROMPT.format(
            goal=plan.goal,
            results=results_text
        )
        
        try:
            response = await self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_completion_tokens=6000
            )
            
            # Check for truncation - error directly to user
            if response.choices[0].finish_reason == "length":
                return SynthesisResult(response="❌ Response was cut off. Try asking for less detail.")
            
            if response.usage:
                cost_tracker.track(
                    model=settings.OPENAI_MODEL,
                    input_tokens=response.usage.prompt_tokens,
                    output_tokens=response.usage.completion_tokens
                )
            
            return SynthesisResult(
                response=response.choices[0].message.content or "",
                needs_confirmation=any(
                    s.requires_confirmation and s.status == StepStatus.COMPLETED
                    for s in plan.steps
                ),
                plan_summary={
                    "goal": plan.goal,
                    "steps_completed": len([s for s in plan.steps if s.status == StepStatus.COMPLETED]),
                    "steps_failed": len([s for s in plan.steps if s.status == StepStatus.FAILED]),
                }
            )
            
        except Exception as e:
            # Fallback: Just concatenate outputs
            combined = "\n".join(r["output"] for r in results if r["success"])
            return SynthesisResult(response=combined or "Done.")
    
    async def _direct_response(self, user_message: str) -> MasterResponse:
        """Handle simple queries without full planning"""
        # This is for truly simple cases where planning is overkill
        return MasterResponse(
            text="I couldn't understand how to help with that. Could you rephrase?",
            plan_executed=False,
        )
    
    def _get_recent_conversation(self) -> str:
        """Get recent conversation for context"""
        if not self.conversation_history:
            return "No previous conversation."
        
        recent = self.conversation_history[-6:]  # Last 3 exchanges
        lines = []
        for msg in recent:
            role = "User" if msg["role"] == "user" else "Assistant"
            content = msg["content"][:100] + "..." if len(msg["content"]) > 100 else msg["content"]
            lines.append(f"{role}: {content}")
        
        return "\n".join(lines)
    
    def _update_history(self, user_msg: str, assistant_msg: str):
        """Update conversation history"""
        self.conversation_history.append({"role": "user", "content": user_msg})
        self.conversation_history.append({"role": "assistant", "content": assistant_msg})
        
        # Keep last 20 messages
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]
    
    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []
        self.working_memory.reset()
