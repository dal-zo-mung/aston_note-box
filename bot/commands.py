from __future__ import annotations

from telegram import BotCommand, Update
from telegram.ext import Application, CommandHandler, ContextTypes

from bot.dependencies import get_services
from bot.ui import (
    DATABASE_ERROR_MESSAGE,
    UNAUTHORIZED_MESSAGE,
    reply_id_grid,
    reply_with_keyboard,
)


START_TEXT_NEW_USER = (
    "👋 Welcome ...!\n "
    "This is your custom-private storage bot developed by @Philip3377.\n\n"
    "📌 What this bot does:\n"
    "- Saves text, photos, videos, audio, voice, animations, and general files\n"
    "- Keeps each item private to your own Telegram account\n"
    "- Lets you find saved items later by ID or keyword\n\n"
    "🎯 Who should use this bot:\n"
    "- Students\n"
    "- Developers\n"
    "- Anyone who wants a simple personal repository inside Telegram\n\n"
    "⚠️ Important:\n"
    "- This bot works with command keys only\n"
    "- Use commands to save, search, update, and delete your data\n"
    "- Add your own keywords when possible for easier search later\n"
    "- For files and media, send them with a caption that starts with `store*`\n\n"
    "🛠️ Main commands:\n"
    "- store* → save data\n"
    "- search* → find data\n"
    "- update* → modify data\n"
    "- delete* → remove data\n\n"
    "⌨️ Shortcuts:\n"
    "- Type `/` to open Telegram's command menu\n"
    "- Send `*` to reopen the 4 command buttons quickly\n\n"
    "ℹ️ Use /help to see full command examples."
)

START_TEXT_RETURNING = (
    "👋 Welcome back.\n\n"
    "- Type `/` for Telegram's command menu\n"
    "- Send `*` to reopen the 4 command buttons quickly\n"
    "- Use /help to see command examples\n"
    "- Use /about to learn more about this bot\n\n"
    "This is your custom-private storage bot developed by @Philip3377.\n\n"
)

HELP_TEXT = (
    "📘 Available commands:\n"
    "store* <content> keyword* <keywords>\n"
    "search* <id or keywords>\n"
    "update* <id> | <new content> keyword* <keywords>\n"
    "delete* <id>\n\n"
    "🧩 Supported media:\n"
    "- photo\n"
    "- video\n"
    "- audio\n"
    "- voice\n"
    "- animation\n"
    "- document (Word, Excel, PDF, ZIP, and other files)\n\n"
    "💡 Notes:\n"
    "- `keyword*` is optional\n"
    "- If you do not add keywords, the bot generates simple keywords for you\n"
    "- Type `/` to open Telegram's command menu\n"
    "- Send `*` to reopen the 4 command buttons quickly\n"
    "- For media or files, send them with a caption like:\n"
    " `store* project roadmap keyword* roadmap, planning`\n"
)

ABOUT_TEXT = (
    "🤖 **About This Bot**\n\n"
    "👋 Hey there! This is your personal Telegram storage buddy - a custom bot I built just for keeping your stuff safe and organized!\n\n"
    "🛠️ **What makes it special:**\n"
    "• Saves all your favorite stuff: texts, photos, videos, music, voice notes, animations, and files\n"
    "• Everything stays super private - only you can see your saved items\n"
    "• Smart search by keywords or ID numbers\n"
    "• Easy update and delete whenever you want\n"
    "• Powered by reliable MongoDB for lightning-fast storage\n\n"
    "👨‍💻 **About me - @Philip3377**\n"
    "Hi! I'm Philip, a passionate developer who loves creating cool tools that make life easier. \n"
    "I specialize in Python and Database, aiming for Ai backend-engineering. \n\n"
    "📧 **Touch me!**\n"
    "Got questions? Want to share feedback?\n"
    "Feel free to DM me @Philip3377 - I'm always open! 😊\n\n"
    "⭐ **Love using this bot?**\n"
    "Your feedback means the world to me! Drop me a message with suggestions or just say hi!\n\n"
    "🔒 **Your privacy matters:**\n"
    "Your data is locked away safely. Only you have the key to access your treasures.\n\n"
    "_Crafted with ❤️ and lots of coffee by @Philip3377_"
)

BOT_COMMANDS = [
    BotCommand("start", "Show bot introduction"),
    BotCommand("help", "Show command help"),
    BotCommand("about", "About the bot and developer"),
    BotCommand("state", "Show your saved note count"),
    BotCommand("stored_ids", "Show your saved note IDs"),
]


async def start_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    message = update.effective_message
    user = update.effective_user

    if message is None or user is None:
        return

    services = get_services(context)
    if not services.database.is_available:
        await reply_with_keyboard(message, DATABASE_ERROR_MESSAGE)
        return
    if not services.note_service.is_user_allowed(user.id):
        await reply_with_keyboard(message, UNAUTHORIZED_MESSAGE)
        return

    has_started = await services.note_service.has_started(user.id)
    await services.note_service.mark_started(user.id)
    await reply_with_keyboard(
        message,
        START_TEXT_RETURNING if has_started else START_TEXT_NEW_USER,
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user

    if message is None or user is None:
        return

    services = get_services(context)
    if not services.note_service.is_user_allowed(user.id):
        await reply_with_keyboard(message, UNAUTHORIZED_MESSAGE)
        return

    await reply_with_keyboard(message, HELP_TEXT)


async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user

    if message is None or user is None:
        return

    services = get_services(context)
    if not services.note_service.is_user_allowed(user.id):
        await reply_with_keyboard(message, UNAUTHORIZED_MESSAGE)
        return

    await reply_with_keyboard(message, ABOUT_TEXT)


async def state_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    message = update.effective_message
    user = update.effective_user

    if message is None or user is None:
        return

    services = get_services(context)
    if not services.database.is_available:
        await reply_with_keyboard(message, DATABASE_ERROR_MESSAGE)
        return
    if not services.note_service.is_user_allowed(user.id):
        await reply_with_keyboard(message, UNAUTHORIZED_MESSAGE)
        return

    count = await services.note_service.count_notes(user.id)
    await reply_with_keyboard(message, f"Stored notes: {count}")


async def stored_ids_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    message = update.effective_message
    user = update.effective_user

    if message is None or user is None:
        return

    services = get_services(context)
    if not services.database.is_available:
        await reply_with_keyboard(message, DATABASE_ERROR_MESSAGE)
        return
    if not services.note_service.is_user_allowed(user.id):
        await reply_with_keyboard(message, UNAUTHORIZED_MESSAGE)
        return

    note_ids = await services.note_service.list_note_ids(user.id)
    await reply_id_grid(message, "Stored IDs", note_ids)


def register_command_handlers(application: Application) -> None:
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("about", about_command))
    application.add_handler(CommandHandler("state", state_command))
    application.add_handler(CommandHandler("stored_ids", stored_ids_command))


async def configure_bot_commands(application: Application) -> None:
    await application.bot.set_my_commands(BOT_COMMANDS)
