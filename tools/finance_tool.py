"""
Simple Finance Tracker
Loans: who owes who, how much
Keeps it simple - just numbers
"""
import json
import uuid
from datetime import datetime
from pathlib import Path
from config.settings import settings
from .base_tool import BaseTool, ToolResult


class FinanceTool(BaseTool):
    name = "finance"
    description = "Track loans and money owed"
    
    def __init__(self):
        self.loans_file = settings.STORAGE_DIR / "finance" / "loans.json"
        self._ensure_file()
    
    def _ensure_file(self):
        self.loans_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.loans_file.exists():
            self._save_loans([])
    
    def _load_loans(self) -> list[dict]:
        with open(self.loans_file, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def _save_loans(self, loans: list[dict]):
        with open(self.loans_file, "w", encoding="utf-8") as f:
            json.dump(loans, f, indent=2, ensure_ascii=False)
    
    def get_function_schemas(self) -> list[dict]:
        return [
            self._make_schema(
                name="add_loan",
                description="""Record a loan. CRITICAL: Pay close attention to WHO owes WHOM!
                - 'I borrowed from X' / 'X lent me' / 'I owe X' → direction='i_owe' (USER owes the person)
                - 'X borrowed from me' / 'I lent X' / 'X owes me' → direction='they_owe' (person owes USER)
                If updating an existing loan with someone, check their current loans first to add to the right direction.""",
                parameters={
                    "person": {"type": "string", "description": "Name of the person"},
                    "amount": {"type": "number", "description": "Amount of money"},
                    "direction": {"type": "string", "enum": ["i_owe", "they_owe"], "description": "i_owe = USER owes this person | they_owe = this person owes the USER"},
                    "note": {"type": "string", "description": "Optional note about the loan"}
                },
                required=["person", "amount", "direction"]
            ),
            self._make_schema(
                name="list_loans",
                description="List all active loans",
                parameters={
                    "direction": {"type": "string", "enum": ["i_owe", "they_owe", "all"], "description": "Filter by direction"}
                },
                required=[]
            ),
            self._make_schema(
                name="settle_loan",
                description="Mark a loan as settled/paid",
                parameters={
                    "loan_id": {"type": "string", "description": "ID of the loan to settle"},
                },
                required=["loan_id"]
            ),
            self._make_schema(
                name="update_loan",
                description="Update loan amount (partial payment)",
                parameters={
                    "loan_id": {"type": "string", "description": "ID of the loan"},
                    "new_amount": {"type": "number", "description": "New remaining amount"}
                },
                required=["loan_id", "new_amount"]
            ),
            self._make_schema(
                name="get_loan_summary",
                description="Get summary of all loans - totals owed and owing",
                parameters={},
                required=[]
            )
        ]
    
    async def execute(self, function_name: str, arguments: dict) -> ToolResult:
        try:
            if function_name == "add_loan":
                return await self._add_loan(**arguments)
            elif function_name == "list_loans":
                return await self._list_loans(**arguments)
            elif function_name == "settle_loan":
                return await self._settle_loan(**arguments)
            elif function_name == "update_loan":
                return await self._update_loan(**arguments)
            elif function_name == "get_loan_summary":
                return await self._get_summary()
            else:
                return ToolResult(success=False, error=f"Unknown function: {function_name}")
        except Exception as e:
            return ToolResult(success=False, error=str(e))
    
    async def _add_loan(self, person: str, amount: float, direction: str, note: str = "") -> ToolResult:
        loans = self._load_loans()
        
        loan = {
            "id": str(uuid.uuid4())[:8],
            "person": person,
            "amount": amount,
            "direction": direction,
            "note": note,
            "status": "active",
            "created_at": datetime.now().isoformat()
        }
        
        loans.append(loan)
        self._save_loans(loans)
        
        direction_text = "You owe" if direction == "i_owe" else f"{person} owes you"
        return ToolResult(success=True, data=f"Recorded: {direction_text} ${amount:.2f}")
    
    async def _list_loans(self, direction: str = "all") -> ToolResult:
        loans = self._load_loans()
        active = [l for l in loans if l["status"] == "active"]
        
        if direction != "all":
            active = [l for l in active if l["direction"] == direction]
        
        if not active:
            return ToolResult(success=True, data="No active loans")
        
        lines = []
        for loan in active:
            dir_text = "You owe" if loan["direction"] == "i_owe" else "Owes you"
            note_text = f" ({loan['note']})" if loan.get("note") else ""
            lines.append(f"[{loan['id']}] {loan['person']}: {dir_text} ${loan['amount']:.2f}{note_text}")
        
        return ToolResult(success=True, data="\n".join(lines))
    
    async def _settle_loan(self, loan_id: str) -> ToolResult:
        loans = self._load_loans()
        
        for loan in loans:
            if loan["id"] == loan_id or loan["id"].startswith(loan_id):
                loan["status"] = "settled"
                loan["settled_at"] = datetime.now().isoformat()
                self._save_loans(loans)
                return ToolResult(success=True, data=f"Settled loan with {loan['person']} for ${loan['amount']:.2f}")
        
        return ToolResult(success=False, error=f"Loan {loan_id} not found")
    
    async def _update_loan(self, loan_id: str, new_amount: float) -> ToolResult:
        loans = self._load_loans()
        
        for loan in loans:
            if loan["id"] == loan_id or loan["id"].startswith(loan_id):
                old_amount = loan["amount"]
                loan["amount"] = new_amount
                self._save_loans(loans)
                return ToolResult(success=True, data=f"Updated loan: ${old_amount:.2f} → ${new_amount:.2f}")
        
        return ToolResult(success=False, error=f"Loan {loan_id} not found")
    
    async def _get_summary(self) -> ToolResult:
        loans = self._load_loans()
        active = [l for l in loans if l["status"] == "active"]
        
        i_owe_total = sum(l["amount"] for l in active if l["direction"] == "i_owe")
        they_owe_total = sum(l["amount"] for l in active if l["direction"] == "they_owe")
        
        summary = f"""Loan Summary:
You owe others: ${i_owe_total:.2f}
Others owe you: ${they_owe_total:.2f}
Net: ${they_owe_total - i_owe_total:+.2f}"""
        
        return ToolResult(success=True, data=summary)
