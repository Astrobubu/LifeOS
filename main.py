#!/usr/bin/env python3
"""
LifeOS - Personal AI Assistant
"""

import sys
import os
import threading
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from rich.live import Live
from rich.console import Console

from bot.telegram_bot import run_bot_async
from utils.backup import create_backup
from utils.terminal_ui import terminal_ui

console = Console()


def input_listener(live):
    """Listen for commands"""
    import msvcrt
    buffer = ""
    while True:
        try:
            if msvcrt.kbhit():
                char = msvcrt.getwch()
                if char == '\r':  # Enter
                    cmd = buffer.strip().lower()
                    buffer = ""
                    if cmd in ['exit', 'quit', 'q', 'stop']:
                        live.stop()
                        os._exit(0)
                    elif cmd == 'backup':
                        try:
                            path = create_backup()
                            terminal_ui.log_activity(f"Backup: {path.name}")
                        except Exception as e:
                            terminal_ui.log_error(str(e), "Backup")
                    elif cmd == 'clear':
                        terminal_ui.errors.clear()
                        terminal_ui.activities.clear()
                elif char == '\x08':  # Backspace
                    buffer = buffer[:-1]
                else:
                    buffer += char
            time.sleep(0.05)
        except Exception as e:
            terminal_ui.log_error(str(e), "Input")


def run_with_ui():
    """Run bot with live UI"""
    import asyncio
    
    # Create backup on startup
    terminal_ui.set_status("Creating backup...")
    try:
        backup_path = create_backup()
        terminal_ui.log_activity(f"Startup backup: {backup_path.name}")
    except Exception as e:
        terminal_ui.log_error(str(e), "Backup")
    
    terminal_ui.set_status("Starting bot...")
    
    # Create layout
    layout = terminal_ui.make_layout()
    
    # Start bot in background thread
    def bot_thread():
        try:
            asyncio.run(run_bot_async())
        except Exception as e:
            terminal_ui.log_error(str(e), "Bot")
    
    bot = threading.Thread(target=bot_thread, daemon=True)
    bot.start()
    
    terminal_ui.set_status("Running")
    terminal_ui.log_activity("Bot started")
    
    # Run live UI with full screen
    try:
        with Live(layout, refresh_per_second=4, console=console, screen=True) as live:
            # Start input listener with live reference
            listener = threading.Thread(target=input_listener, args=(live,), daemon=True)
            listener.start()
            
            while True:
                terminal_ui.refresh(layout)
                time.sleep(0.25)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    run_with_ui()
