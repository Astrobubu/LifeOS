#!/usr/bin/env python
"""Quick diagnostic to show recent errors from the terminal UI"""
import sys
sys.path.insert(0, 'd:\\Apps\\LifeOS')

from utils.terminal_ui import terminal_ui

print("Recent errors from Terminal UI:")
print("=" * 60)

if not terminal_ui.errors:
    print("No errors logged.")
else:
    for i, err in enumerate(list(terminal_ui.errors)[:5], 1):
        print(f"\nError #{i}:")
        print(f"  Time: {err['time']}")
        print(f"  Source: {err['source']}")
        print(f"  Message: {err['message']}")
        print("-" * 60)
