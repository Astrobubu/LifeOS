"""
Terminal UI - Rich dashboard for LifeOS
"""
import threading
from datetime import datetime
from collections import deque
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from config.settings import settings
from utils.cost_tracker import cost_tracker


class TerminalUI:
    def __init__(self):
        self.console = Console()
        self.start_time = datetime.now()
        self.errors: deque = deque(maxlen=50)
        self.activities: deque = deque(maxlen=30)
        self.messages: deque = deque(maxlen=20)  # Chat messages
        self._lock = threading.Lock()
        self.request_count = 0
        self.current_status = "Starting..."
        self.input_buffer = ""  # Current input being typed
        self.input_enabled = True  # Allow terminal input
    
    def log_error(self, error: str, source: str = "System"):
        """Log an error - full message, no truncation"""
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"[{source}] {error}")
        
        with self._lock:
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.errors.appendleft({
                "time": timestamp,
                "source": source,
                "message": str(error)
            })
    
    def log_activity(self, activity: str):
        """Log an activity"""
        with self._lock:
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.activities.appendleft(f"[dim]{timestamp}[/] {activity}")
            self.request_count += 1
    
    def log_message(self, role: str, content: str):
        """Log a chat message"""
        with self._lock:
            timestamp = datetime.now().strftime("%H:%M:%S")
            if role == "user":
                self.messages.append(f"[dim]{timestamp}[/] [bold cyan]You:[/] {content}")
            else:
                # Truncate long responses for display
                display = content[:200] + "..." if len(content) > 200 else content
                self.messages.append(f"[dim]{timestamp}[/] [bold green]AI:[/] {display}")
    
    def set_input(self, text: str):
        """Update the input buffer display"""
        self.input_buffer = text
    
    def set_status(self, status: str):
        """Set current status"""
        self.current_status = status
    
    def get_uptime(self) -> str:
        """Get formatted uptime"""
        delta = datetime.now() - self.start_time
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    def make_header(self) -> Panel:
        """Create header panel"""
        grid = Table.grid(expand=True)
        grid.add_column(justify="left", ratio=1)
        grid.add_column(justify="center", ratio=1)
        grid.add_column(justify="right", ratio=1)
        
        now = datetime.now().strftime("%H:%M:%S")
        grid.add_row(
            "[bold cyan]LifeOS[/]",
            f"[dim]{settings.OPENAI_MODEL}[/]",
            f"[dim]Up:[/] {self.get_uptime()}  [dim]|[/]  {now}"
        )
        
        return Panel(grid, box=box.ROUNDED, style="dim", padding=(0, 1))
    
    def make_stats(self) -> Panel:
        """Create stats panel"""
        today = cost_tracker.get_today_stats()
        total = cost_tracker.get_total_stats()
        
        table = Table(box=None, expand=True, show_header=True, padding=(0, 1))
        table.add_column("", style="dim")
        table.add_column("Today", justify="right", style="cyan")
        table.add_column("Total", justify="right", style="dim")
        
        table.add_row("Input", f"{today['input']:,}", f"{total['total_input_tokens']:,}")
        table.add_row("Output", f"{today['output']:,}", f"{total['total_output_tokens']:,}")
        table.add_row("Cost", f"${today['cost']:.4f}", f"${total['total_cost']:.4f}")
        table.add_row("Requests", str(self.request_count), "")
        
        return Panel(table, title="[bold]Stats[/]", border_style="dim", box=box.ROUNDED, padding=(0, 1))
    
    def make_activity(self) -> Panel:
        """Create activity panel - fills available space"""
        if not self.activities:
            content = Text("Waiting for activity...", style="dim")
        else:
            # Show as many as will fit
            lines = list(self.activities)[:15]
            content = "\n".join(lines)
        
        return Panel(content, title="[bold]Activity[/]", border_style="dim", box=box.ROUNDED, padding=(0, 1))
    
    def make_errors(self) -> Panel:
        """Create errors panel - full error text with wrapping"""
        if not self.errors:
            content = Text("No errors", style="dim")
        else:
            # Build error text with full messages that will wrap
            lines = []
            for err in list(self.errors)[:10]:
                lines.append(f"[dim]{err['time']}[/] [yellow][{err['source']}][/]")
                lines.append(f"  {err['message']}")
                lines.append("")
            content = "\n".join(lines)
        
        border = "red" if self.errors else "dim"
        return Panel(
            content, 
            title=f"[bold]Errors ({len(self.errors)})[/]", 
            border_style=border, 
            box=box.ROUNDED, 
            padding=(0, 1)
        )
    
    def make_status(self) -> Panel:
        """Create status bar with input"""
        status_color = "green" if self.current_status == "Running" else "yellow"
        
        # Show input prompt
        if self.input_enabled:
            input_display = self.input_buffer if self.input_buffer else ""
            input_line = f"[bold white]>[/] {input_display}[blink]_[/]"
        else:
            input_line = "[dim]Input disabled[/]"
        
        text = f"[{status_color}]{self.current_status}[/]  |  {input_line}  [dim]| exit, backup, clear[/]"
        return Panel(text, box=box.ROUNDED, style="dim", padding=(0, 0))
    
    def make_chat(self) -> Panel:
        """Create chat panel showing recent messages"""
        if not self.messages:
            content = Text("No messages yet. Type below to chat.", style="dim")
        else:
            lines = list(self.messages)[-10:]  # Last 10 messages
            content = "\n".join(lines)
        
        return Panel(content, title="[bold]Chat[/]", border_style="cyan", box=box.ROUNDED, padding=(0, 1))
    
    def make_layout(self) -> Layout:
        """Create the main layout with chat panel"""
        layout = Layout()
        
        layout.split(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
            Layout(name="status", size=3)
        )
        
        layout["main"].split_row(
            Layout(name="left", ratio=1),
            Layout(name="right", ratio=1)
        )
        
        layout["left"].split(
            Layout(name="stats", size=8),
            Layout(name="chat", ratio=1)  # Chat replaces some of activity
        )
        
        layout["right"].split(
            Layout(name="activity", ratio=1),
            Layout(name="errors", ratio=1)
        )
        
        return layout
    
    def refresh(self, layout: Layout):
        """Refresh all panels"""
        layout["header"].update(self.make_header())
        layout["stats"].update(self.make_stats())
        layout["chat"].update(self.make_chat())
        layout["activity"].update(self.make_activity())
        layout["errors"].update(self.make_errors())
        layout["status"].update(self.make_status())


# Global instance
terminal_ui = TerminalUI()
