import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

from config.settings import settings
from agent.smart_agent import SmartAgent, AgentResponse
from utils.cost_tracker import cost_tracker
from utils.backup import get_backup_stats

# Setup comprehensive logging to file AND console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('d:\\Apps\\LifeOS\\bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Global agent instance
agent = SmartAgent()

# Track message IDs for clearing
user_message_ids: dict[int, list[int]] = {}


def get_main_keyboard() -> InlineKeyboardMarkup:
    """Get the main menu keyboard"""
    keyboard = [
        [
            InlineKeyboardButton("📝 Notes", callback_data="list_notes"),
            InlineKeyboardButton("✅ Tasks", callback_data="list_tasks"),
        ],
        [
            InlineKeyboardButton("📅 Today", callback_data="today_schedule"),
            InlineKeyboardButton("💰 Loans", callback_data="loan_summary"),
        ],
        [
            InlineKeyboardButton("📧 Email", callback_data="check_email"),
            InlineKeyboardButton("👤 Profile", callback_data="show_profile"),
        ],
        [
            InlineKeyboardButton("ℹ️ Info", callback_data="show_info"),
            InlineKeyboardButton("🗑️ Clear", callback_data="clear"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_confirmation_keyboard() -> InlineKeyboardMarkup:
    """Get confirmation buttons"""
    keyboard = [
        [
            InlineKeyboardButton("✅ Yes, do it", callback_data="confirm_yes"),
            InlineKeyboardButton("❌ Cancel", callback_data="confirm_no"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def track_message(user_id: int, message_id: int):
    """Track a message ID for later deletion"""
    if user_id not in user_message_ids:
        user_message_ids[user_id] = []
    user_message_ids[user_id].append(message_id)
    # Keep only last 100 messages
    if len(user_message_ids[user_id]) > 100:
        user_message_ids[user_id] = user_message_ids[user_id][-100:]


def is_authorized(user_id: int) -> bool:
    """Check if user is authorized to use the bot"""
    if not settings.ALLOWED_USER_IDS:
        return True  # No restriction if not configured
    return user_id in settings.ALLOWED_USER_IDS


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("Not authorized.")
        return
    
    user_id = update.effective_user.id
    track_message(user_id, update.message.message_id)
    
    # Check if profile needs setup
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
        welcome = f"""Hey {profile.get('name', 'there')}! Ready to help.

Quick actions below or just tell me what you need."""
    
    msg = await update.message.reply_text(welcome, reply_markup=get_main_keyboard())
    track_message(user_id, msg.message_id)


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /clear command - clear conversation history and delete messages"""
    if not is_authorized(update.effective_user.id):
        return
    
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Clear agent history
    agent.clear_history()
    
    # Delete tracked messages
    deleted = 0
    if user_id in user_message_ids:
        for msg_id in user_message_ids[user_id]:
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
                deleted += 1
            except Exception:
                pass  # Message may already be deleted or too old
        user_message_ids[user_id] = []
    
    # Delete the /clear command message itself
    try:
        await update.message.delete()
    except Exception:
        pass
    
    # Send fresh start message
    msg = await context.bot.send_message(
        chat_id=chat_id,
        text="Chat cleared! Starting fresh.",
        reply_markup=get_main_keyboard()
    )
    track_message(user_id, msg.message_id)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stats command - show memory stats"""
    if not is_authorized(update.effective_user.id):
        return
    
    user_id = update.effective_user.id
    track_message(user_id, update.message.message_id)
    
    stats = agent.get_memory_stats()
    stats_text = get_stats_text(stats)
    
    msg = await update.message.reply_text(stats_text)
    track_message(user_id, msg.message_id)


def get_stats_text(stats: dict) -> str:
    """Format stats as text"""
    text = f"""📊 Memory Statistics

Total memories: {stats['total_memories']}
Average importance: {stats['avg_importance']:.1f}

By type:
"""
    for mem_type, count in stats.get('by_type', {}).items():
        text += f"  - {mem_type}: {count}\n"
    
    if not stats.get('by_type'):
        text += "  (no memories yet)\n"
    
    return text


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    if not is_authorized(update.effective_user.id):
        return
    
    user_id = update.effective_user.id
    track_message(user_id, update.message.message_id)
    
    msg = await update.message.reply_text(get_help_text(), reply_markup=get_main_keyboard())
    track_message(user_id, msg.message_id)


def get_help_text() -> str:
    """Get help text"""
    return """How to use me:

Send me text, voice, or images and I'll help!

I can:
- Create and manage notes
- Track your tasks  
- Search the web
- Read/send emails
- Remember important information

Tips:
- "remember that..." to store info
- "add task..." for quick tasks
- "create note..." for notes
- "search for..." for web search"""


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button presses"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not is_authorized(user_id):
        return
    
    chat_id = query.message.chat_id
    action = query.data
    
    # Handle confirmation buttons
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
            text="Cleared! Fresh start.",
            reply_markup=get_main_keyboard()
        )
        track_message(user_id, msg.message_id)
    
    elif action == "stats":
        stats = agent.get_memory_stats()
        await query.edit_message_text(get_stats_text(stats), reply_markup=get_main_keyboard())
    
    elif action == "help":
        await query.edit_message_text(get_help_text(), reply_markup=get_main_keyboard())
    
    elif action == "list_notes":
        await query.edit_message_text("Getting notes...", reply_markup=None)
        response = await agent.process("list all my notes", user_id)
        msg = await context.bot.send_message(chat_id=chat_id, text=response.text, reply_markup=get_main_keyboard())
        track_message(user_id, msg.message_id)
    
    elif action == "list_tasks":
        await query.edit_message_text("Getting tasks...", reply_markup=None)
        response = await agent.process("list all my tasks", user_id)
        msg = await context.bot.send_message(chat_id=chat_id, text=response.text, reply_markup=get_main_keyboard())
        track_message(user_id, msg.message_id)
    
    elif action == "check_email":
        await query.edit_message_text("Checking email...", reply_markup=None)
        response = await agent.process("check my recent emails", user_id)
        msg = await context.bot.send_message(chat_id=chat_id, text=response.text, reply_markup=get_main_keyboard())
        track_message(user_id, msg.message_id)
    
    elif action == "today_schedule":
        await query.edit_message_text("Getting today's schedule...", reply_markup=None)
        response = await agent.process("what's on my calendar today", user_id)
        msg = await context.bot.send_message(chat_id=chat_id, text=response.text, reply_markup=get_main_keyboard())
        track_message(user_id, msg.message_id)
    
    elif action == "loan_summary":
        await query.edit_message_text("Getting loan summary...", reply_markup=None)
        response = await agent.process("show me my loan summary", user_id)
        msg = await context.bot.send_message(chat_id=chat_id, text=response.text, reply_markup=get_main_keyboard())
        track_message(user_id, msg.message_id)
    
    elif action == "show_profile":
        profile = agent.get_profile_data()
        if profile:
            text = f"""👤 Your Profile

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
        # Cost tracking
        cost_summary = cost_tracker.get_summary()
        
        # Memory stats
        mem_stats = agent.get_memory_stats()
        mem_text = f"Memories: {mem_stats.get('total_memories', 0)}/{mem_stats.get('max_memories', 500)}"
        
        # Backup stats
        backup_stats = get_backup_stats()
        backup_text = f"Backups: {backup_stats.get('count', 0)}/{backup_stats.get('max', 5)}"
        if backup_stats.get('latest'):
            backup_text += f"\nLatest: {backup_stats['latest'][:10]}"
        
        text = f"""{cost_summary}

📁 **Storage**
• {mem_text}
• {backup_text}

🤖 **Model:** {settings.OPENAI_MODEL}"""
        
        await query.edit_message_text(text, reply_markup=get_main_keyboard(), parse_mode="Markdown")


async def keep_typing(chat_id, bot, stop_event):
    """Keep sending typing indicator until stopped"""
    while not stop_event.is_set():
        try:
            await bot.send_chat_action(chat_id=chat_id, action="typing")
        except Exception as e:
            logger.error(f"Typing indicator failed: {e}")
        await asyncio.sleep(4)  # Typing indicator lasts ~5 seconds


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages"""
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("Not authorized.")
        return
    
    user_message = update.message.text
    user_id = update.effective_user.id
    
    track_message(user_id, update.message.message_id)
    
    # Log user message
    logger.info(f"CHAT [User {user_id}]: {user_message}")
    
    # Log activity
    try:
        from utils.terminal_ui import terminal_ui
        terminal_ui.log_activity(f"Text: {user_message[:30]}...")
    except:
        pass
    
    # Handle profile setup
    if context.user_data.get("awaiting_setup") or agent.needs_setup:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        try:
            # Use AI to extract profile info from natural text
            profile_data = await extract_profile_from_text(user_message)
            if profile_data.get("name"):
                agent.setup_profile(**profile_data)
                context.user_data["awaiting_setup"] = False
                msg = await update.message.reply_text(
                    f"Got it, {profile_data['name']}! I'm all set up.\n\nNow I know who you are and can help better - especially with emails and outreach.\n\nWhat can I help you with?",
                    reply_markup=get_main_keyboard()
                )
                track_message(user_id, msg.message_id)
                return
        except Exception as e:
            logger.error(f"Profile setup error: {e}")
    
    # Start continuous typing indicator
    stop_typing = asyncio.Event()
    typing_task = asyncio.create_task(keep_typing(update.effective_chat.id, context.bot, stop_typing))
    
    try:
        response = await agent.process(user_message, user_id)
        
        # Check if confirmation needed
        if response.needs_confirmation:
            msg = await update.message.reply_text(
                response.text,
                reply_markup=get_confirmation_keyboard(),
                parse_mode=None
            )
            track_message(user_id, msg.message_id)
            return
        
        # Regular response
        text = response.text
        if len(text) > 4000:
            chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
            for chunk in chunks:
                msg = await update.message.reply_text(chunk)
                track_message(user_id, msg.message_id)
        else:
            msg = await update.message.reply_text(text)
            logger.info(f"CHAT [Bot to {user_id}]: {text}")
            track_message(user_id, msg.message_id)
            
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        error_msg = str(e)
        
        # Log to terminal UI
        try:
            from utils.terminal_ui import terminal_ui
            terminal_ui.log_error(error_msg[:100], "Text")
        except:
            pass
        
        # Clean up common error messages for user
        if "rate limit" in error_msg.lower():
            error_msg = "Rate limited. Please wait a moment and try again."
        elif "timeout" in error_msg.lower():
            error_msg = "Request timed out. Please try again."
        elif "api" in error_msg.lower() and "key" in error_msg.lower():
            error_msg = "API configuration error. Check settings."
        else:
            error_msg = error_msg[:150] if len(error_msg) > 150 else error_msg
        
        msg = await update.message.reply_text(f"Error: {error_msg}")
        track_message(user_id, msg.message_id)
    finally:
        # Stop typing indicator
        stop_typing.set()
        typing_task.cancel()


async def extract_profile_from_text(text: str) -> dict:
    """Use AI to extract profile info from natural text"""
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    
    response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[{
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
Only include fields that are clearly mentioned or can be inferred."""
        }],
        temperature=1,
        response_format={"type": "json_object"}
    )
    
    import json
    return json.loads(response.choices[0].message.content)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle voice messages"""
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        return
    
    track_message(user_id, update.message.message_id)
    
    # Log activity
    try:
        from utils.terminal_ui import terminal_ui
        terminal_ui.log_activity("Voice message received")
    except:
        pass
    
    # Start continuous typing indicator
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
                parse_mode=None
            )
        else:
            msg = await update.message.reply_text(response.text)
            logger.info(f"CHAT [Bot to {user_id}]: {response.text}")
        track_message(user_id, msg.message_id)
        
    except Exception as e:
        logger.error(f"Voice error: {e}", exc_info=True)
        try:
            from utils.terminal_ui import terminal_ui
            terminal_ui.log_error(str(e), "Voice")
        except:
            pass
        msg = await update.message.reply_text(f"Couldn't process voice message. Try again or type instead.")
        track_message(user_id, msg.message_id)
    finally:
        stop_typing.set()
        typing_task.cancel()


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo messages - smart processing with action detection"""
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        return
    
    track_message(user_id, update.message.message_id)
    
    # Log activity
    try:
        from utils.terminal_ui import terminal_ui
        caption = update.message.caption or "no caption"
        terminal_ui.log_activity(f"Photo: {caption[:25]}...")
    except:
        pass
    
    # Start continuous typing indicator
    stop_typing = asyncio.Event()
    typing_task = asyncio.create_task(keep_typing(update.effective_chat.id, context.bot, stop_typing))
    
    try:
        logger.info(f"[IMAGE] Processing image from user {user_id}")
        photo = update.message.photo[-1]
        photo_file = await context.bot.get_file(photo.file_id)
        photo_bytes = await photo_file.download_as_bytearray()
        caption = update.message.caption or ""
        logger.info(f"CHAT [User {user_id} Photo]: {caption}")
        logger.info(f"[IMAGE] Downloaded {len(photo_bytes)} bytes, caption: '{caption}'")
        
        # Process image with user context for smart actions
        logger.info(f"[IMAGE] Calling agent.process_image...")
        response = await agent.process_image(bytes(photo_bytes), caption, user_id)
        logger.info(f"[IMAGE] Got response: needs_confirmation={response.needs_confirmation}, text_len={len(response.text) if response.text else 0}")
        
        # Handle confirmation if needed
        if response.needs_confirmation:
            msg = await update.message.reply_text(
                response.text,
                reply_markup=get_confirmation_keyboard(),
                parse_mode=None
            )
        else:
            logger.info(f"CHAT [Bot to {user_id}]: {response.text}")
            msg = await update.message.reply_text(response.text)
        track_message(user_id, msg.message_id)
        logger.info(f"[IMAGE] Image processing completed successfully")
        
    except Exception as e:
        logger.error(f"[IMAGE] Photo error: {e}", exc_info=True)
        logger.error(f"[IMAGE] Full traceback:", exc_info=True)
        try:
            from utils.terminal_ui import terminal_ui
            terminal_ui.log_error(str(e), "Photo")
        except:
            pass
        # Show actual error to help debug
        error_msg = str(e)[:500] if str(e) else "Unknown error"
        logger.error(f"[IMAGE] Sending error to user: {error_msg}")
        msg = await update.message.reply_text(f"❌ Image processing error:\n\n{error_msg}")
        track_message(user_id, msg.message_id)
    finally:
        stop_typing.set()
        typing_task.cancel()


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"Update {update} caused error {context.error}")
    # Log to terminal UI
    try:
        from utils.terminal_ui import terminal_ui
        terminal_ui.log_error(str(context.error)[:100], "Telegram")
    except:
        pass


def run_bot():
    """Start the Telegram bot"""
    # Validate settings
    missing = settings.validate()
    if missing:
        print(f"Missing required settings: {', '.join(missing)}")
        print("Please create a .env file with the required values.")
        print("See .env.example for reference.")
        return
    
    # Create application
    app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    # Error handler
    app.add_error_handler(error_handler)
    
    # Start polling
    print(f"🚀 {settings.BOT_NAME} is starting...")
    print("Press Ctrl+C to stop")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


async def automation_scheduler(app):
    """Background task to check and run due automations every minute.
    
    This enables catch-up for missed scheduled tasks (e.g., if PC was off).
    """
    from tools import get_tool
    automations_tool = get_tool("automations")
    
    # Wait a bit on startup to let everything initialize
    await asyncio.sleep(5)
    
    while True:
        try:
            results = await automations_tool.check_and_run_due()
            if results:
                for result in results:
                    if result.success:
                        data = result.data
                        try:
                            from utils.terminal_ui import terminal_ui
                            if isinstance(data, dict) and data.get("type") == "prompt":
                                # Handle prompt-type automation - process through agent
                                auto_name = data.get('automation_name', 'prompt')
                                terminal_ui.log_activity(f"Auto: {auto_name}")
                                
                                if settings.ALLOWED_USER_IDS:
                                    try:
                                        user_id = settings.ALLOWED_USER_IDS[0]
                                        response = await agent.process(data["prompt"], user_id)
                                        terminal_ui.log_activity(f"Auto done: {auto_name}")
                                        
                                        # Send response to user via Telegram
                                        if response.text and app:
                                            await app.bot.send_message(chat_id=user_id, text=response.text)
                                            logger.info(f"Sent automation response to {user_id}")
                                            
                                    except Exception as agent_err:
                                        terminal_ui.log_error(f"Auto failed: {str(agent_err)[:80]}", "Agent")
                                        logger.error(f"Automation agent error for {auto_name}: {agent_err}", exc_info=True)
                            else:
                                terminal_ui.log_activity(f"Auto: {str(data)[:30]}")
                        except Exception as e:
                            logger.error(f"Automation log error: {e}", exc_info=True)
                    else:
                        # Log failed automation
                        logger.error(f"Automation failed: {result.error}")
                        try:
                            from utils.terminal_ui import terminal_ui
                            terminal_ui.log_error(f"Auto: {str(result.error)[:50]}", "Auto")
                        except:
                            pass
        except Exception as e:
            logger.error(f"Automation scheduler error: {e}", exc_info=True)
            try:
                from utils.terminal_ui import terminal_ui
                terminal_ui.log_error(f"Scheduler: {str(e)[:50]}", "Auto")
            except:
                pass
        
        await asyncio.sleep(60)  # Check every minute


async def run_bot_async():
    """Start the Telegram bot (async version for terminal UI)"""
    # Validate settings
    missing = settings.validate()
    if missing:
        raise Exception(f"Missing settings: {', '.join(missing)}")
    
    # Create application
    app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    # Error handler
    app.add_error_handler(error_handler)
    
    # Start polling (async)
    await app.initialize()
    await app.start()
    await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    
    # Start automation scheduler in background
    asyncio.create_task(automation_scheduler(app))
    logger.info("Automation scheduler started")
    
    # Keep running
    while True:
        await asyncio.sleep(1)
