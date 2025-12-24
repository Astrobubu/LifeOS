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


def input_listener(live, agent_queue):
    """Listen for commands and chat messages"""
    import msvcrt
    buffer = ""
    
    while True:
        try:
            if msvcrt.kbhit():
                char = msvcrt.getwch()
                if char == '\r':  # Enter
                    cmd = buffer.strip()
                    buffer = ""
                    terminal_ui.set_input("")
                    
                    if not cmd:
                        continue
                    
                    cmd_lower = cmd.lower()
                    
                    # Handle system commands
                    if cmd_lower in ['exit', 'quit', 'q', 'stop']:
                        live.stop()
                        os._exit(0)
                    elif cmd_lower == 'backup':
                        try:
                            path = create_backup()
                            terminal_ui.log_activity(f"Backup: {path.name}")
                        except Exception as e:
                            terminal_ui.log_error(str(e), "Backup")
                    elif cmd_lower == 'clear':
                        terminal_ui.errors.clear()
                        terminal_ui.activities.clear()
                        terminal_ui.messages.clear()
                    else:
                        # It's a chat message - queue it for processing
                        terminal_ui.log_message("user", cmd)
                        agent_queue.put(cmd)
                        
                elif char == '\x08':  # Backspace
                    buffer = buffer[:-1]
                    terminal_ui.set_input(buffer)
                elif char == '\x1b':  # Escape - clear buffer
                    buffer = ""
                    terminal_ui.set_input("")
                else:
                    buffer += char
                    terminal_ui.set_input(buffer)
            time.sleep(0.05)
        except Exception as e:
            terminal_ui.log_error(str(e), "Input")


def run_with_ui():
    """Run bot with live UI and terminal chat"""
    import asyncio
    import queue
    from agent.smart_agent import SmartAgent
    
    # Message queue for terminal input
    agent_queue = queue.Queue()
    agent = SmartAgent()
    
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
    
    # Agent processing thread for terminal messages
    def agent_processor():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        while True:
            try:
                # Get message from queue (blocking)
                message = agent_queue.get()
                if message:
                    terminal_ui.set_status("Processing...")
                    try:
                        # Process through agent
                        response = loop.run_until_complete(
                            agent.process(message, user_id=0)
                        )
                        # Log the response
                        terminal_ui.log_message("assistant", response.text)
                    except Exception as e:
                        terminal_ui.log_error(str(e), "Agent")
                        terminal_ui.log_message("assistant", f"Error: {str(e)[:100]}")
                    finally:
                        terminal_ui.set_status("Running")
            except Exception as e:
                terminal_ui.log_error(str(e), "AgentProcessor")
    
    agent_thread = threading.Thread(target=agent_processor, daemon=True)
    agent_thread.start()
    
    terminal_ui.set_status("Running")
    terminal_ui.log_activity("Bot started - type messages below")
    
    # Run live UI with full screen
    try:
        with Live(layout, refresh_per_second=4, console=console, screen=True) as live:
            # Start input listener with live reference and queue
            listener = threading.Thread(target=input_listener, args=(live, agent_queue), daemon=True)
            listener.start()
            
            while True:
                terminal_ui.refresh(layout)
                time.sleep(0.25)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    run_with_ui()
