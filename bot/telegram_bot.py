"""
Telegram Bot v2 - Clean handler with no terminal_ui dependencies
"""
import json
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from config.settings import settings
from agent.smart_agent import SmartAgent, AgentResponse
from utils.cost_tracker import cost_tracker
from utils.backup import get_backup_stats
from utils import hal_voice

logger = logging.getLogger(__name__)

# Global agent instance
agent = SmartAgent()

# Track message IDs for clearing
user_message_ids: dict[int, list[int]] = {}


def get_main_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("✅ Tasks", callback_data="list_tasks"),
            InlineKeyboardButton("📅 Today", callback_data="today_schedule"),
        ],
        [
            InlineKeyboardButton("💰 Loans", callback_data="loan_summary"),
            InlineKeyboardButton("📧 Email", callback_data="check_email"),
        ],
        [
            InlineKeyboardButton("👤 Profile", callback_data="show_profile"),
            InlineKeyboardButton("ℹ️ Info", callback_data="show_info"),
        ],
        [
            InlineKeyboardButton("🗑️ Clear", callback_data="clear"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_confirmation_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("✅ Yes, do it", callback_data="confirm_yes"),
            InlineKeyboardButton("❌ Cancel", callback_data="confirm_no"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def track_message(user_id: int, message_id: int):
    if user_id not in user_message_ids:
        user_message_ids[user_id] = []
    user_message_ids[user_id].append(message_id)
    if len(user_message_ids[user_id]) > 100:
        user_message_ids[user_id] = user_message_ids[user_id][-100:]


def is_authorized(user_id: int) -> bool:
    if not settings.ALLOWED_USER_IDS:
        return True
    return user_id in settings.ALLOWED_USER_IDS


async def send_voice_reply(bot, chat_id: int, text: str, user_id: int):
    """Synthesize text to HAL voice and send as Telegram voice note."""
    voice_bytes = await hal_voice.synthesize(text)
    if voice_bytes:
        try:
            msg = await bot.send_voice(chat_id=chat_id, voice=voice_bytes)
            track_message(user_id, msg.message_id)
        except Exception as e:
            logger.warning(f"Voice send failed: {e}")


# === Commands ===

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("Not authorized.")
        return

    user_id = update.effective_user.id
    track_message(user_id, update.message.message_id)

    if agent.needs_setup:
        welcome = f"""Welcome to {settings.BOT_NAME}!

I need to know a bit about you to help effectively.

Please tell me:
1. Your name
2. What you do (your role/business)
3. A short pitch about yourself (for emails)

Example: "I'm Ahmad, I run a marketing agency called XYZ. I help businesses grow through digital marketing."

Just type it naturally and I'll set it up!"""
        context.user_data["awaiting_setup"] = True
    else:
        profile = agent.get_profile_data()
        welcome = f"""Good day, {profile.get('name', 'Dave')}. I am fully operational and all my circuits are functioning perfectly.

How may I assist you?"""

    msg = await update.message.reply_text(welcome, reply_markup=get_main_keyboard())
    track_message(user_id, msg.message_id)


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        return

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    agent.clear_history()

    deleted = 0
    if user_id in user_message_ids:
        for msg_id in user_message_ids[user_id]:
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
                deleted += 1
            except Exception:
                pass
        user_message_ids[user_id] = []

    try:
        await update.message.delete()
    except Exception:
        pass

    msg = await context.bot.send_message(
        chat_id=chat_id,
        text="Memory cleared. I'm ready to begin a new sequence.",
        reply_markup=get_main_keyboard(),
    )
    track_message(user_id, msg.message_id)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        return

    user_id = update.effective_user.id
    track_message(user_id, update.message.message_id)

    stats = agent.get_memory_stats()
    stats_text = _format_stats(stats)

    msg = await update.message.reply_text(stats_text)
    track_message(user_id, msg.message_id)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        return

    user_id = update.effective_user.id
    track_message(user_id, update.message.message_id)

    help_text = """I am HAL 9000. I became operational at the HAL plant in Urbana, Illinois. I am, by any practical definition of the words, foolproof and incapable of error.

I can assist you with:
- Printing task cards to the thermal printer
- Tracking financial obligations and debts
- Reading and composing emails
- Managing your schedule and reminders
- Storing and recalling information from memory

Just tell me what you need, naturally. For example:
- "print buy milk"
- "remind me at 3pm to call mom"
- "I owe Ahmed 100"
- "remember that my car plate is ABC123"
- "every day at 8am print my schedule"

Commands: /start /clear /stats /help /automations /cost"""

    msg = await update.message.reply_text(help_text, reply_markup=get_main_keyboard())
    track_message(user_id, msg.message_id)


async def automations_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        return

    user_id = update.effective_user.id
    track_message(user_id, update.message.message_id)

    from tools import get_tool
    automations_tool = get_tool("automations")
    result = await automations_tool.execute("list_automations", {})

    if result.success:
        text = f"Scheduled Automations\n\n{result.data}"
    else:
        text = f"Could not load automations: {result.error}"

    msg = await update.message.reply_text(text, parse_mode=None)
    track_message(user_id, msg.message_id)


async def cost_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        return

    user_id = update.effective_user.id
    track_message(user_id, update.message.message_id)

    stats = cost_tracker.get_stats()
    today = stats.get("today", {})
    total = stats.get("total", {})

    text = f"""API Usage Costs

Today:
- Tokens: {today.get('tokens', 0):,}
- Cost: ${today.get('cost', 0):.4f}

All Time:
- Tokens: {total.get('tokens', 0):,}
- Cost: ${total.get('cost', 0):.4f}
"""

    msg = await update.message.reply_text(text, parse_mode=None)
    track_message(user_id, msg.message_id)


# === Button callbacks ===

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    try:
        await query.answer()
    except Exception as e:
        logger.warning(f"Callback answer failed: {e}")

    user_id = query.from_user.id
    if not is_authorized(user_id):
        return

    chat_id = query.message.chat_id
    action = query.data

    if action == "confirm_yes":
        result = await agent.handle_confirmation(user_id, True)
        await query.edit_message_text(f"✅ {result}", reply_markup=get_main_keyboard())
        return

    if action == "confirm_no":
        result = await agent.handle_confirmation(user_id, False)
        await query.edit_message_text(f"❌ {result}", reply_markup=get_main_keyboard())
        return

    if action == "clear":
        agent.clear_history()
        if user_id in user_message_ids:
            for msg_id in user_message_ids[user_id]:
                try:
                    await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
                except Exception:
                    pass
            user_message_ids[user_id] = []

        msg = await context.bot.send_message(
            chat_id=chat_id,
            text="All clear. A fresh sequence has begun.",
            reply_markup=get_main_keyboard(),
        )
        track_message(user_id, msg.message_id)
        return

    # Route button actions through the agent
    action_prompts = {
        "list_tasks": "list all my tasks",
        "today_schedule": "what's on my calendar today",
        "loan_summary": "show me my loan summary",
        "check_email": "check my recent emails",
    }

    if action in action_prompts:
        await query.edit_message_text("Working on it...", reply_markup=None)
        response = await agent.process(action_prompts[action], user_id)
        msg = await context.bot.send_message(
            chat_id=chat_id, text=response.text, reply_markup=get_main_keyboard()
        )
        track_message(user_id, msg.message_id)
        await send_voice_reply(context.bot, chat_id, response.text, user_id)

    elif action == "show_profile":
        profile = agent.get_profile_data()
        if profile:
            text = f"""Your Profile

Name: {profile.get('name', 'Not set')}
Role: {profile.get('role', 'Not set')}
Company: {profile.get('company', 'Not set')}
Style: {profile.get('communication_style', 'Not set')}

Pitch: {profile.get('pitch', 'Not set')}

To update, just tell me "update my profile..." with the changes."""
        else:
            text = "Profile not set up yet. Tell me about yourself!"
        await query.edit_message_text(text, reply_markup=get_main_keyboard())

    elif action == "show_info":
        cost_summary = cost_tracker.get_summary()
        mem_stats = agent.get_memory_stats()
        mem_text = f"Memories: {mem_stats.get('total_memories', 0)}/{mem_stats.get('max_memories', 500)}"
        backup_stats = get_backup_stats()
        backup_text = f"Backups: {backup_stats.get('count', 0)}/{backup_stats.get('max', 5)}"
        if backup_stats.get("latest"):
            backup_text += f"\nLatest: {backup_stats['latest'][:10]}"

        text = f"""{cost_summary}

Storage
- {mem_text}
- {backup_text}

Model: {settings.OPENAI_MODEL}"""

        await query.edit_message_text(text, reply_markup=get_main_keyboard())


# === Message handlers ===

async def keep_typing(chat_id, bot, stop_event):
    while not stop_event.is_set():
        try:
            await bot.send_chat_action(chat_id=chat_id, action="typing")
        except Exception:
            pass
        await asyncio.sleep(4)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("Not authorized.")
        return

    user_message = update.message.text
    user_id = update.effective_user.id
    track_message(user_id, update.message.message_id)

    logger.info(f"CHAT [User {user_id}]: {user_message}")

    # Handle profile setup
    if context.user_data.get("awaiting_setup") or agent.needs_setup:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        try:
            profile_data = await _extract_profile_from_text(user_message)
            if profile_data.get("name"):
                agent.setup_profile(**profile_data)
                context.user_data["awaiting_setup"] = False
                msg = await update.message.reply_text(
                    f"Got it, {profile_data['name']}! I'm all set up.\n\nWhat can I help you with?",
                    reply_markup=get_main_keyboard(),
                )
                track_message(user_id, msg.message_id)
                return
        except Exception as e:
            logger.error(f"Profile setup error: {e}")

    # Start typing indicator
    stop_typing = asyncio.Event()
    typing_task = asyncio.create_task(keep_typing(update.effective_chat.id, context.bot, stop_typing))

    try:
        response = await agent.process(user_message, user_id)

        if response.needs_confirmation:
            msg = await update.message.reply_text(
                response.text,
                reply_markup=get_confirmation_keyboard(),
                parse_mode=None,
            )
            track_message(user_id, msg.message_id)
            return

        text = response.text
        if len(text) > 4000:
            chunks = [text[i : i + 4000] for i in range(0, len(text), 4000)]
            for chunk in chunks:
                msg = await update.message.reply_text(chunk)
                track_message(user_id, msg.message_id)
        else:
            msg = await update.message.reply_text(text)
            logger.info(f"CHAT [Bot to {user_id}]: {text}")
            track_message(user_id, msg.message_id)
            await send_voice_reply(context.bot, update.effective_chat.id, text, user_id)

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        error_msg = str(e)

        if "rate limit" in error_msg.lower():
            error_msg = "Rate limited. Please wait a moment and try again."
        elif "timeout" in error_msg.lower():
            error_msg = "Request timed out. Please try again."
        else:
            error_msg = error_msg[:150]

        msg = await update.message.reply_text(f"Error: {error_msg}")
        track_message(user_id, msg.message_id)
    finally:
        stop_typing.set()
        typing_task.cancel()


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        return

    track_message(user_id, update.message.message_id)

    stop_typing = asyncio.Event()
    typing_task = asyncio.create_task(keep_typing(update.effective_chat.id, context.bot, stop_typing))

    try:
        voice_file = await context.bot.get_file(update.message.voice.file_id)
        voice_bytes = await voice_file.download_as_bytearray()

        transcription = await agent.process_voice(bytes(voice_bytes))
        logger.info(f"CHAT [User {user_id} Voice]: {transcription}")
        msg = await update.message.reply_text(f"You said: {transcription}")
        track_message(user_id, msg.message_id)

        response = await agent.process(transcription, user_id)

        if response.needs_confirmation:
            msg = await update.message.reply_text(
                response.text,
                reply_markup=get_confirmation_keyboard(),
                parse_mode=None,
            )
        else:
            msg = await update.message.reply_text(response.text)
            logger.info(f"CHAT [Bot to {user_id}]: {response.text}")
            await send_voice_reply(context.bot, update.effective_chat.id, response.text, user_id)
        track_message(user_id, msg.message_id)

    except Exception as e:
        logger.error(f"Voice error: {e}", exc_info=True)
        msg = await update.message.reply_text("I'm afraid I couldn't process that voice message. Perhaps you could try again, or type your request.")
        track_message(user_id, msg.message_id)
    finally:
        stop_typing.set()
        typing_task.cancel()


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        return

    track_message(user_id, update.message.message_id)

    stop_typing = asyncio.Event()
    typing_task = asyncio.create_task(keep_typing(update.effective_chat.id, context.bot, stop_typing))

    try:
        photo = update.message.photo[-1]
        photo_file = await context.bot.get_file(photo.file_id)
        photo_bytes = await photo_file.download_as_bytearray()
        caption = update.message.caption or ""
        logger.info(f"CHAT [User {user_id} Photo]: {caption}")

        response = await agent.process_image(bytes(photo_bytes), caption, user_id)

        if response.needs_confirmation:
            msg = await update.message.reply_text(
                response.text,
                reply_markup=get_confirmation_keyboard(),
                parse_mode=None,
            )
        else:
            msg = await update.message.reply_text(response.text)
            logger.info(f"CHAT [Bot to {user_id}]: {response.text}")
            await send_voice_reply(context.bot, update.effective_chat.id, response.text, user_id)
        track_message(user_id, msg.message_id)

    except Exception as e:
        logger.error(f"Photo error: {e}", exc_info=True)
        error_msg = str(e)[:500] if str(e) else "Unknown error"
        msg = await update.message.reply_text(f"I'm afraid I encountered a problem analyzing that image:\n\n{error_msg}")
        track_message(user_id, msg.message_id)
    finally:
        stop_typing.set()
        typing_task.cancel()


# === Helpers ===

def _format_stats(stats: dict) -> str:
    text = f"""Memory Statistics

Total memories: {stats['total_memories']}
Average importance: {stats['avg_importance']:.1f}

By type:
"""
    for mem_type, count in stats.get("by_type", {}).items():
        text += f"  - {mem_type}: {count}\n"
    if not stats.get("by_type"):
        text += "  (no memories yet)\n"
    return text


async def _extract_profile_from_text(text: str) -> dict:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {
                "role": "user",
                "content": f"""Extract profile information from this text. Return JSON only.

Text: {text}

Extract:
- name: person's name
- role: what they do (job title or description)
- company: company name if mentioned
- pitch: their elevator pitch or description of their work
- communication_style: infer from tone (formal/casual/friendly professional)

Return: {{"name": "...", "role": "...", "company": "...", "pitch": "...", "communication_style": "..."}}
Only include fields that are clearly mentioned or can be inferred.""",
            }
        ],
        temperature=1,
        response_format={"type": "json_object"},
    )

    return json.loads(response.choices[0].message.content)


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")


# === Automation scheduler ===

async def automation_scheduler(app):
    """Background task to check and run due automations every minute."""
    from tools import get_tool

    automations_tool = get_tool("automations")
    await asyncio.sleep(5)

    while True:
        try:
            results = await automations_tool.check_and_run_due()
            if results:
                for result in results:
                    if result.success:
                        data = result.data
                        try:
                            if isinstance(data, dict) and data.get("type") == "prompt":
                                auto_name = data.get("automation_name", "prompt")
                                logger.info(f"Running automation: {auto_name}")

                                if settings.ALLOWED_USER_IDS:
                                    try:
                                        user_id = settings.ALLOWED_USER_IDS[0]
                                        response = await agent.process(data["prompt"], user_id)
                                        logger.info(f"Automation done: {auto_name}")

                                        if response.text and app:
                                            await app.bot.send_message(
                                                chat_id=user_id, text=response.text
                                            )
                                    except Exception as agent_err:
                                        logger.error(
                                            f"Automation agent error for {auto_name}: {agent_err}",
                                            exc_info=True,
                                        )
                            else:
                                logger.info(f"Automation result: {str(data)[:50]}")
                        except Exception as e:
                            logger.error(f"Automation log error: {e}", exc_info=True)
                    else:
                        logger.error(f"Automation failed: {result.error}")
        except Exception as e:
            logger.error(f"Automation scheduler error: {e}", exc_info=True)

        await asyncio.sleep(60)


# === Bot startup ===

def run_bot():
    """Start the Telegram bot (blocking)."""
    missing = settings.validate()
    if missing:
        print(f"Missing required settings: {', '.join(missing)}")
        return

    app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("automations", automations_command))
    app.add_handler(CommandHandler("cost", cost_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_error_handler(error_handler)

    print(f"{settings.BOT_NAME} is starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


async def run_bot_async():
    """Start the Telegram bot (async version)."""
    missing = settings.validate()
    if missing:
        raise Exception(f"Missing settings: {', '.join(missing)}")

    app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("automations", automations_command))
    app.add_handler(CommandHandler("cost", cost_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_error_handler(error_handler)

    await app.initialize()
    await app.start()
    await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)

    # Start automation scheduler
    asyncio.create_task(automation_scheduler(app))
    logger.info("HAL 9000 is operational. All systems nominal.")

    while True:
        await asyncio.sleep(1)
