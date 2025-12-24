"""
Handlers package - Specialized handlers for different domains
"""
from .base_handler import BaseHandler
from .finance_handler import FinanceHandler
from .tasks_handler import TasksHandler
from .notes_handler import NotesHandler
from .calendar_handler import CalendarHandler
from .email_handler import EmailHandler
from .print_handler import PrintHandler
from .general_handler import GeneralHandler

__all__ = [
    "BaseHandler",
    "FinanceHandler", 
    "TasksHandler",
    "NotesHandler",
    "CalendarHandler",
    "EmailHandler",
    "PrintHandler",
    "GeneralHandler",
]
