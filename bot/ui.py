from __future__ import annotations

import html
from typing import Any

from telegram import KeyboardButton, ReplyKeyboardMarkup
from telegram.constants import ParseMode


GRID_COLUMNS = 7
DATABASE_ERROR_MESSAGE = "Database unavailable. Please try again later."
INVALID_COMMAND_MESSAGE = "Invalid command. Use /help to see available commands."
UNAUTHORIZED_MESSAGE = "This bot is private. You are not allowed to use it."
COMMAND_SHORTCUT_MESSAGE = "Choose a command:\nstore*\nsearch*\nupdate*\ndelete*"
_COMMAND_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton("store*"), KeyboardButton("search*")],
        [KeyboardButton("update*"), KeyboardButton("delete*")],
    ],
    resize_keyboard=True,
    is_persistent=True,
    one_time_keyboard=False,
    input_field_placeholder="Tap a command or type one...",
)


def build_command_keyboard() -> ReplyKeyboardMarkup:
    return _COMMAND_KEYBOARD


async def reply_with_keyboard(message: Any, text: str, **kwargs: Any) -> None:
    await message.reply_text(
        text,
        reply_markup=_COMMAND_KEYBOARD,
        **kwargs,
    )


async def reply_id_grid(message: Any, title: str, ids: list[int]) -> None:
    if not ids:
        await reply_with_keyboard(message, f"{title}:\n(none)")
        return

    grid = format_id_grid(ids)
    await reply_with_keyboard(
        message,
        f"{title}:\n<pre>{html.escape(grid)}</pre>",
        parse_mode=ParseMode.HTML,
    )


def format_id_grid(ids: list[int]) -> str:
    width = max(4, max(len(str(value)) for value in ids))
    rows: list[str] = []
    for index in range(0, len(ids), GRID_COLUMNS):
        row = ids[index : index + GRID_COLUMNS]
        rows.append(" ".join(f"{value:>{width}}" for value in row))
    return "\n".join(rows)


def format_store_response(note_id: int, keywords: list[str], *, status: str) -> str:
    keyword_text = ", ".join(keywords) if keywords else "-"
    return f"Status: {status}\nID: {note_id}\nKW: {keyword_text}"
