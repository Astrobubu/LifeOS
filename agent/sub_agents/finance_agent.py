"""
Finance Sub-Agent - Autonomous agent for loans and money tracking

This agent ALWAYS has loan context and understands:
- Who owes whom
- How to record new loans with correct direction
- How to settle debts
"""
from .base_sub_agent import BaseSubAgent
from ..planning import AgentType
from tools.finance_tool import FinanceTool


class FinanceSubAgent(BaseSubAgent):
    """
    Autonomous finance agent with LLM reasoning + finance tools.
    
    Key responsibility: NEVER get loan direction wrong.
    """
    
    agent_type = AgentType.FINANCE
    agent_name = "finance"
    max_iterations = 5
    
    def __init__(self):
        super().__init__()
        self.finance_tool = FinanceTool()
    
    def get_system_prompt(self) -> str:
        # Load current loan state into the prompt
        loan_context = self._get_loan_context()
        
        return f"""You are the FINANCE sub-agent for LifeOS.

## Your Role
You handle all financial operations:
- Recording new loans (who owes whom, amounts)
- Tracking existing debts
- Settling/updating loans
- Providing summaries

## CRITICAL: Loan Direction Rules

The "direction" parameter determines WHO OWES WHOM:

**direction = "i_owe"** means THE USER owes this person:
- "I owe Dad 100" → add_loan(person="Dad", amount=100, direction="i_owe")
- "I borrowed 50 from Mom" → direction="i_owe"
- "Mom lent me 50" → direction="i_owe"

**direction = "they_owe"** means this person OWES THE USER:
- "Dad owes me 100" → add_loan(person="Dad", amount=100, direction="they_owe")
- "I lent Dad 50" → direction="they_owe"
- "Dad borrowed 50 from me" → direction="they_owe"

## Current Loan State
{loan_context}

Use this to understand existing relationships. If user mentions someone who already has loans, 
consider the existing direction when adding more or making corrections.

## Response Style
- Be concise: "✓ Recorded: You owe Dad 100 AED"
- For queries: Give clear summaries
- If direction is ambiguous, ASK before recording
"""
    
    def _get_loan_context(self) -> str:
        """Get current loan state for context"""
        try:
            loans = self.finance_tool._load_loans()
            active = [l for l in loans if l.get("status") == "active"]
            
            if not active:
                return "No active loans currently."
            
            # Group by direction
            i_owe = {}
            they_owe = {}
            
            for loan in active:
                person = loan.get("person", "Unknown")
                amount = loan.get("amount", 0)
                
                if loan.get("direction") == "i_owe":
                    i_owe[person] = i_owe.get(person, 0) + amount
                else:
                    they_owe[person] = they_owe.get(person, 0) + amount
            
            lines = []
            if i_owe:
                lines.append("**USER OWES (direction=i_owe):**")
                for person, total in i_owe.items():
                    lines.append(f"  - {person}: {total}")
            
            if they_owe:
                lines.append("**OWE THE USER (direction=they_owe):**")
                for person, total in they_owe.items():
                    lines.append(f"  - {person}: {total}")
            
            return "\n".join(lines) if lines else "No active loans."
            
        except Exception:
            return "Unable to load loan state."
    
    def get_tools(self) -> list[dict]:
        return self.finance_tool.get_function_schemas()
    
    def get_tool_mapping(self) -> dict[str, str]:
        return {
            "add_loan": "finance",
            "list_loans": "finance",
            "settle_loan": "finance",
            "update_loan": "finance",
            "get_loan_summary": "finance",
        }
    
    def _extract_data_from_result(self, function_name: str, result) -> dict:
        """Extract structured loan data"""
        data = {}
        
        if function_name == "add_loan" and result.success:
            data["loan_added"] = result.data
        elif function_name == "list_loans" and result.success:
            data["loans"] = result.data
        elif function_name == "get_loan_summary" and result.success:
            data["loan_summary"] = result.data
        
        return data
