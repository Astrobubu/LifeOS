"""
Finance Handler - Specialized handler for loans, money, and financial operations
This handler ALWAYS has loans context loaded to prevent direction errors
"""
from .base_handler import BaseHandler
from tools.finance_tool import FinanceTool


class FinanceHandler(BaseHandler):
    """
    Handler for financial operations including loans and money tracking.
    
    Key feature: Always loads current loan state into context so the LLM
    knows existing relationships (who owes whom) and doesn't make errors
    like reversing loan directions.
    """
    
    handler_name = "finance"
    
    def __init__(self):
        super().__init__()
        self.finance_tool = FinanceTool()
    
    def get_system_prompt(self) -> str:
        return """You are LifeOS Finance Assistant, specialized in tracking loans and money.

## Your Role
- Track who owes money to whom
- Record new loans accurately
- Help settle and update existing loans
- Provide loan summaries

## CRITICAL: Loan Direction Rules
When recording loans, you MUST correctly determine the direction:

**direction = "i_owe"** (User owes the person):
- "I owe [person]"
- "I borrowed from [person]"
- "[Person] lent me"
- "Borrowed X from [person]"

**direction = "they_owe"** (Person owes the user):
- "[Person] owes me"
- "I lent [person]"
- "[Person] borrowed from me"
- "Lent X to [person]"

## IMPORTANT: Use Domain Context
Look at the Active Loans section below. If the user mentions a person who already
has loans, consider the existing direction when they add more or make corrections.

## Response Style
- Be concise: "✓ Recorded: You owe [person] X AED"
- For corrections, acknowledge the fix: "✓ Fixed: Changed to [correct direction]"
- For summaries, use clear formatting
"""
    
    def get_tools(self) -> list[dict]:
        """Only return finance-related tools"""
        return self.finance_tool.get_function_schemas()
    
    def get_tool_mapping(self) -> dict:
        """Map function names to tool names"""
        return {
            "add_loan": "finance",
            "list_loans": "finance",
            "settle_loan": "finance",
            "update_loan": "finance",
            "get_loan_summary": "finance",
        }
    
    async def get_domain_context(self, user_message: str) -> str:
        """
        Load ALL active loans into context.
        This is the key fix - the LLM always knows existing loan relationships.
        """
        try:
            loans = self.finance_tool._load_loans()
            active = [l for l in loans if l.get("status") == "active"]
            
            if not active:
                return """ACTIVE LOANS: None

You can help the user record new loans. Remember:
- "I owe X" or "borrowed from X" → direction = i_owe
- "X owes me" or "lent to X" → direction = they_owe"""
            
            # Group by person and direction for clarity
            i_owe = {}
            they_owe = {}
            
            for loan in active:
                person = loan.get("person", "Unknown")
                amount = loan.get("amount", 0)
                note = loan.get("note", "")
                loan_id = loan.get("id", "")
                
                if loan.get("direction") == "i_owe":
                    if person not in i_owe:
                        i_owe[person] = []
                    i_owe[person].append({"amount": amount, "note": note, "id": loan_id})
                else:
                    if person not in they_owe:
                        they_owe[person] = []
                    they_owe[person].append({"amount": amount, "note": note, "id": loan_id})
            
            # Format context
            lines = ["ACTIVE LOANS (Use this to understand existing relationships):"]
            lines.append("")
            
            if i_owe:
                lines.append("💸 USER OWES THESE PEOPLE (direction=i_owe):")
                for person, entries in i_owe.items():
                    total = sum(e["amount"] for e in entries)
                    lines.append(f"  • {person}: {total} total")
                    for e in entries:
                        lines.append(f"    - [{e['id']}] {e['amount']} ({e['note'][:30] if e['note'] else 'no note'})")
                lines.append("")
            
            if they_owe:
                lines.append("💰 THESE PEOPLE OWE USER (direction=they_owe):")
                for person, entries in they_owe.items():
                    total = sum(e["amount"] for e in entries)
                    lines.append(f"  • {person}: {total} total")
                    for e in entries:
                        lines.append(f"    - [{e['id']}] {e['amount']} ({e['note'][:30] if e['note'] else 'no note'})")
                lines.append("")
            
            # Summary
            total_i_owe = sum(sum(e["amount"] for e in entries) for entries in i_owe.values())
            total_they_owe = sum(sum(e["amount"] for e in entries) for entries in they_owe.values())
            lines.append(f"SUMMARY: User owes {total_i_owe} | Others owe user {total_they_owe} | Net: {total_they_owe - total_i_owe:+}")
            
            return "\n".join(lines)
            
        except Exception as e:
            return f"Error loading loans: {str(e)}"
    
    def get_loan_people(self) -> list[str]:
        """Get list of people with active loans for entity detection"""
        try:
            loans = self.finance_tool._load_loans()
            active = [l for l in loans if l.get("status") == "active"]
            return list(set(l.get("person", "") for l in active if l.get("person")))
        except Exception:
            return []
