"""Sub-agents package - Autonomous agents for each domain"""
from .base_sub_agent import BaseSubAgent
from .finance_agent import FinanceSubAgent
from .tasks_agent import TasksSubAgent
from .calendar_agent import CalendarSubAgent
from .email_agent import EmailSubAgent
from .notes_agent import NotesSubAgent
from .web_agent import WebResearchSubAgent
from .print_agent import PrintSubAgent
from .automations_agent import AutomationsSubAgent
from .memory_agent import MemorySubAgent

__all__ = [
    "BaseSubAgent",
    "FinanceSubAgent",
    "TasksSubAgent",
    "CalendarSubAgent",
    "EmailSubAgent",
    "NotesSubAgent",
    "WebResearchSubAgent",
    "PrintSubAgent",
    "AutomationsSubAgent",
    "MemorySubAgent",
]
