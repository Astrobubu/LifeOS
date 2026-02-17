# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LifeOS is a Telegram-based personal AI assistant using an Orchestrator-Workers agentic pattern. A Master Agent plans and delegates to specialized Sub-Agents (tasks, calendar, email, finance, memory, automations, print, web), each with their own LLM and tools. It includes physical thermal printer integration (TSC DA200) for printing task cards and text.

## Running the Project

```bash
pip install -r requirements.txt
python main.py
```

Entry point `main.py` starts a Rich terminal UI and launches the Telegram bot in a background thread. The bot can also be tested via terminal chat directly.

No test suite or linting configuration exists.

## Architecture

### Agent Flow
```
User Message → SmartAgent (smart_agent.py)
  ├─ Fast-path: simple patterns skip planning, route directly to sub-agent
  └─ Complex: MasterAgent (master_agent.py) creates ExecutionPlan → delegates to sub-agents → synthesizes
```

- **SmartAgent** (`agent/smart_agent.py`): Entry point. Handles context (1hr timeout + summarization), fast-path routing, image/voice processing, proactive memory extraction.
- **MasterAgent** (`agent/master_agent.py`): LLM-powered orchestrator. Creates multi-step plans, delegates to sub-agents, combines results.
- **Router** (`agent/router.py`): Keyword-based intent classification for fast-path.
- **Sub-Agents** (`agent/sub_agents/`): Each has own system prompt, LLM, and domain tools. Runs agentic loop (LLM + tool calls until done). Base class in `base_sub_agent.py`.

### Tool System
Tools in `tools/` implement `BaseTool`. Sub-agents call them via OpenAI function calling. Each tool returns `ToolResult(success, data)` and manages its own JSON storage.

### Memory System
`memory/vector_memory.py`: Semantic search with OpenAI `text-embedding-3-small`. Stores embeddings as `embeddings.npy` + metadata in `vector_memories.json`. Auto-deduplication at >0.9 similarity, max 500 memories with decay.

### Printer System
`printer_control/`: TSC DA200 via win32print (Windows only). Two modes:
- **Task cards** (`print_task.py`): Short tasks, supports handwritten/urgent/normal styles
- **Long text** (`print_text.py`): Paragraphs, notes, lists

Pipeline: HTML template → Chrome headless screenshot → PNG → TSPL commands to printer.

### Automations
Three types: `action` (direct tool call, no LLM), `prompt` (AI-powered), `routine` (pre-built). Schedules: hourly, daily, weekly, on_start, once. Background scheduler in `telegram_bot.py` checks every 60s.

## Storage

All data is JSON files in `storage/`:
- `automations/automations.json` - scheduled actions
- `finance/loans.json` - loan tracking
- `memories/vector_memories.json` + `embeddings.npy` - semantic memories
- `notes/` - markdown note files
- `tasks/tasks.json` - task list
- `profile/user_profile.json` - user identity
- `working_memory/state.json` - cross-step state
- `usage_costs.json` - API cost tracking

Daily backups to `backups/` (max 5, auto-rotation).

## Environment Variables (.env)

Required: `TELEGRAM_BOT_TOKEN`, `ALLOWED_USER_IDS`, `OPENAI_API_KEY`, `OPENAI_MODEL` (gpt-5-mini), `OPENAI_VISION_MODEL` (gpt-5), `BOT_NAME`
Google APIs: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` (OAuth tokens stored as `token.json`, `calendar_token.json`)

## Models Used
- Main LLM: `gpt-5-mini` (set via OPENAI_MODEL)
- Vision: `gpt-5` (set via OPENAI_VISION_MODEL)
- Transcription: `whisper-1`
- Embeddings: `text-embedding-3-small`

## Telegram Bot Commands
`/start`, `/help`, `/clear` (clears conversation + deletes messages), `/stats` (memory stats), `/automations` (list scheduled), `/cost` (API usage)

## Key Patterns
- Fast-path patterns in `smart_agent.py` bypass full planning for simple requests (e.g., "print X", "remind me at X")
- Sub-agents are autonomous: they loop with LLM + tools until task is complete
- Working memory (`working_memory.py`) passes state between plan steps
- Cost tracking via `utils/cost_tracker.py` wraps all OpenAI calls
- Platform: Windows required for printer (win32print). Python 3.10+ (match/case used).
