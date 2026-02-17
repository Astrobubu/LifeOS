"""Sub-agents package - Autonomous agents for each domain (v2)"""
from .base_sub_agent import BaseSubAgent, SubAgentResult
from .finance_agent import FinanceSubAgent
from .calendar_agent import CalendarSubAgent
from .email_agent import EmailSubAgent
from .print_agent import PrintSubAgent
from .automations_agent import AutomationsSubAgent
from .memory_agent import MemorySubAgent
from .general_agent import GeneralSubAgent

__all__ = [
    "BaseSubAgent",
    "SubAgentResult",
    "FinanceSubAgent",
    "CalendarSubAgent",
    "EmailSubAgent",
    "PrintSubAgent",
    "AutomationsSubAgent",
    "MemorySubAgent",
    "GeneralSubAgent",
]
