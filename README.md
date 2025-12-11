# LifeOS

**LifeOS** is an intelligent, CLI-based personal assistant designed to manage tasks, notes, finances, and even print physical task cards on a thermal printer. It leverages a local LLM agent to understand natural language commands and execute complex workflows.

## 🚀 Features

*   **Intelligent Agent:** A smart CLI agent that understands natural language context and intent.
*   **Task Management:** Create, update, list, and complete tasks.
*   **Note Taking:** Create, read, update, and search notes with fuzzy matching.
*   **Finance Tracking:** Log transactions and check balances (basic implementation).
*   **Calendar Integration:** (Planned/Partial) Interface with Google Calendar.
*   **Web Browsing & Search:** Search the web and browse content directly from the CLI.
*   **🖨️ Thermal Printer Integration:**
    *   Print task cards directly to a **TSC DA200** (or compatible TSPL) thermal printer.
    *   **Style Support:** Choose between "Handwritten" and "Urgent" styles.
    *   **Smart Parsing:** Automatically determines importance and style from your command.
    *   **Calibrated Output:** Pixel-perfect alignment for 58mm labels.

## 🛠️ Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Astrobubu/LifeOS.git
    cd LifeOS
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *Note: You may need to install `pywin32` manually if on Windows.*

3.  **Environment Setup:**
    *   Create a `.env` file based on your API keys (OpenAI, Telegram, etc.).
    *   Ensure your TSC Printer driver is installed and named `"TSC DA200"` (or update `printer_control/print_task.py`).

## 🎮 Usage

Run the main application:
```bash
python main.py
```

### Example Commands

*   **Tasks:** "Add a task to buy groceries."
*   **Notes:** "Create a note about my meeting with John."
*   **Printing:**
    *   "Print a task: Call Mom."
    *   "Print an urgent task: Server Down!" (Sets importance to High/3).
    *   "Print a note to pick up dry cleaning."

## 📂 Project Structure

*   `agent/`: Core logic for the Smart Agent and prompts.
*   `tools/`: Tool definitions (Tasks, Notes, Printer, etc.) exposed to the agent.
*   `printer_control/`: **The Crown Jewel.**
    *   Scripts for controlling the thermal printer via raw TSPL commands.
    *   HTML templates for rendering task cards.
    *   Calibration tools (`ui_alignment.py`) for perfect print margins.
*   `storage/`: JSON and Markdown storage for user data.
*   `utils/`: Helper utilities for costs and UI.

## 🖨️ Printer Calibration (Deep Dive)

The `printer_control` module is highly tuned for **58mm continuous rolls**.

*   **`print_task.py`**: The main driver. Usage: `python printer_control/print_task.py "Text" <Importance 1-3> <Style>`
*   **`ui_alignment.py`**: A GUI tool to manually tweak X/Y offsets, speed, and density in real-time.
*   **`task_renderer.py`**: Renders HTML templates to 1-bit monochrome bitmaps for the printer.

## 🤝 Contributing

Feel free to fork, submit PRs, or suggest new "Styles" for the printer templates!

---
*Built with ❤️ (and a lot of thermal paper).*
