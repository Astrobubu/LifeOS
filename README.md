# LifeOS

**LifeOS** is an intelligent Telegram-based personal assistant powered by an agentic AI architecture. It manages tasks (physical prints), notes, finances, calendar, email, and automations through natural conversation.

## 🚀 Features

### Core Capabilities
- **Intelligent Agentic Architecture**: Master Agent orchestrates specialized sub-agents for different domains
- **Fast-Path Routing**: Simple requests skip planning for instant responses
- **Voice & Image Processing**: Send voice notes or photos for transcription and analysis
- **Physical Task Printing**: Print task cards on a TSC DA200 thermal printer

### Domains Covered
- 📝 **Notes & Memory**: Remember information, create notes, search memories
- 💰 **Finance**: Track loans and debts (who owes whom)
- 📅 **Calendar**: Events, reminders with Telegram notifications
- 📧 **Email**: Read and send Gmail
- 🔄 **Automations**: Scheduled/recurring actions (daily prints, weekly reminders)
- 🌐 **Web Search**: Search and browse the web
- 🖨️ **Thermal Printer**: Print task cards with handwritten/urgent styles

## 🛠️ Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Astrobubu/LifeOS.git
   cd LifeOS
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment:**
   Create a `.env` file with:
   ```
   TELEGRAM_BOT_TOKEN=your_bot_token
   ALLOWED_USER_IDS=your_telegram_user_id
   OPENAI_API_KEY=your_openai_key
   OPENAI_MODEL=gpt-4o-mini
   ```

4. **Run the bot:**
   ```bash
   python main.py
   ```

## 📱 Telegram Commands

| Command | Description |
|---------|-------------|
| `/start` | Initialize the bot |
| `/help` | Show help text |
| `/clear` | Clear conversation history |
| `/stats` | Show memory statistics |
| `/automations` | List scheduled automations |
| `/cost` | Show API usage costs |

## 💬 Example Interactions

- `"Print buy milk"` → Prints task card immediately
- `"Remind me at 3pm to call mom"` → Creates calendar reminder
- `"I owe dad 100"` → Records loan
- `"Every morning print my schedule"` → Creates daily automation
- `"Reprint laundry"` → Runs existing automation
- `"Remember that Sarah's birthday is March 5th"` → Stores memory

## 📂 Project Structure

```
LifeOS/
├── agent/              # Agentic AI architecture
│   ├── master_agent.py   # Orchestrator with planning
│   ├── smart_agent.py    # Entry point with fast-path
│   └── sub_agents/       # Domain-specific agents
├── bot/                # Telegram bot handlers
├── tools/              # Tool implementations
├── printer_control/    # Thermal printer drivers
├── memory/             # Vector memory system
├── storage/            # JSON data storage
└── config/             # Settings and configuration
```

## 🖨️ Printer Setup

For TSC DA200 (or compatible TSPL) printers:
1. Install printer driver
2. Name the printer "TSC DA200" in Windows
3. Use `printer_control/ui_alignment.py` to calibrate

---
*Built with ❤️ and a lot of thermal paper.*
