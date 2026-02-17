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
            ),
            self._make_schema(
                name="get_person_loans",
                description="Get all loan entries for a specific person with full details (amounts, notes, dates, IDs). Use this when the user asks about loans with a specific person.",
                parameters={
                    "person": {"type": "string", "description": "Person name (case-insensitive match)"}
                },
                required=["person"]
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
            elif function_name == "get_person_loans":
                return await self._get_person_loans(**arguments)
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

        # Per-person breakdown
        i_owe_by_person: dict[str, float] = {}
        they_owe_by_person: dict[str, float] = {}

        for loan in active:
            person = loan.get("person", "Unknown")
            amount = loan.get("amount", 0)
            if loan["direction"] == "i_owe":
                i_owe_by_person[person] = i_owe_by_person.get(person, 0) + amount
            else:
                they_owe_by_person[person] = they_owe_by_person.get(person, 0) + amount

        i_owe_total = sum(i_owe_by_person.values())
        they_owe_total = sum(they_owe_by_person.values())

        lines = [f"Loan Summary:"]
        if i_owe_by_person:
            lines.append(f"\nYou owe others: ${i_owe_total:.2f}")
            for person, amount in sorted(i_owe_by_person.items()):
                lines.append(f"  - {person}: ${amount:.2f}")
        if they_owe_by_person:
            lines.append(f"\nOthers owe you: ${they_owe_total:.2f}")
            for person, amount in sorted(they_owe_by_person.items()):
                lines.append(f"  - {person}: ${amount:.2f}")

        lines.append(f"\nNet: ${they_owe_total - i_owe_total:+.2f}")
        return ToolResult(success=True, data="\n".join(lines))

    async def _get_person_loans(self, person: str) -> ToolResult:
        loans = self._load_loans()
        person_loans = [l for l in loans if l.get("person", "").lower() == person.lower()]

        if not person_loans:
            return ToolResult(success=True, data=f"No loans found for {person}")

        active = [l for l in person_loans if l["status"] == "active"]
        settled = [l for l in person_loans if l["status"] == "settled"]

        lines = [f"Loans with {person}:"]

        if active:
            i_owe = sum(l["amount"] for l in active if l["direction"] == "i_owe")
            they_owe = sum(l["amount"] for l in active if l["direction"] == "they_owe")
            lines.append(f"\nActive total: You owe ${i_owe:.2f} | They owe ${they_owe:.2f}")
            lines.append(f"\nActive entries ({len(active)}):")
            for loan in active:
                dir_text = "You owe" if loan["direction"] == "i_owe" else "They owe"
                date = loan.get("created_at", "")[:10]
                note = f" - {loan['note']}" if loan.get("note") else ""
                lines.append(f"  [{loan['id']}] ${loan['amount']:.2f} ({dir_text}) {date}{note}")

        if settled:
            lines.append(f"\nSettled entries ({len(settled)}):")
            for loan in settled:
                date = loan.get("created_at", "")[:10]
                lines.append(f"  [{loan['id']}] ${loan['amount']:.2f} - settled {loan.get('settled_at', '')[:10]}")

        return ToolResult(success=True, data="\n".join(lines))
