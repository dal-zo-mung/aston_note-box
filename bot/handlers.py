from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from telegram import (
    Animation,
    Audio,
    Document,
    Message,
    PhotoSize,
    Update,
    Video,
    Voice,
)
from telegram.ext import Application, ContextTypes, MessageHandler, filters

from bot.commands import HELP_TEXT
from bot.dependencies import get_services
from bot.ui import (
    COMMAND_SHORTCUT_MESSAGE,
    DATABASE_ERROR_MESSAGE,
    INVALID_COMMAND_MESSAGE,
    UNAUTHORIZED_MESSAGE,
    build_command_keyboard,
    format_store_response,
    reply_with_keyboard,
)
from services.note_service import NoteServiceError, ValidationError
from utils.keywords import normalize_keywords


LOGGER = logging.getLogger(__name__)
MAX_TELEGRAM_MESSAGE_LENGTH = 3900
MAX_MEDIA_CAPTION_LENGTH = 900
SEARCH_PREFIX = "search*"
STORE_PREFIX = "store*"
DELETE_PREFIX = "delete*"
UPDATE_PREFIX = "update*"
KEYWORD_MARKER = "keyword*"
STORE_USAGE = "Usage: store* <content> keyword* <keywords>"
SEARCH_USAGE = "Usage: search* <id or keywords>"
UPDATE_USAGE = "Usage: update* <id> | <new content> keyword* <keywords>"
DELETE_USAGE = "Usage: delete* <id>"


async def handle_text_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    message = update.effective_message
    user = update.effective_user

    if message is None or not message.text or user is None:
        return

    services = get_services(context)
    if not await _ensure_access(message, services, user.id):
        return

    text = message.text.strip()
    if not text:
        await reply_with_keyboard(message, INVALID_COMMAND_MESSAGE)
        return

    if text.lower() == "help":
        await reply_with_keyboard(message, HELP_TEXT)
        return

    if text == "*":
        await reply_with_keyboard(message, COMMAND_SHORTCUT_MESSAGE)
        return

    if _has_prefix(text, SEARCH_PREFIX):
        await _handle_search(message, services, user.id, text)
        return

    if _has_prefix(text, STORE_PREFIX):
        await _handle_store_text(message, services, user.id, text)
        return

    if _has_prefix(text, DELETE_PREFIX):
        await _handle_delete(message, services, user.id, text)
        return

    if _has_prefix(text, UPDATE_PREFIX):
        await _handle_update(message, services, user.id, text)
        return

    await reply_with_keyboard(message, INVALID_COMMAND_MESSAGE)


async def handle_photo_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    await _handle_media_message(update, context, "photo", "photo")


async def handle_audio_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    await _handle_media_message(update, context, "audio", "audio")


async def handle_document_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    await _handle_media_message(update, context, "document", "document")


async def handle_video_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    await _handle_media_message(update, context, "video", "video")


async def handle_voice_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    await _handle_media_message(update, context, "voice", "voice")


async def handle_animation_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    await _handle_media_message(update, context, "animation", "animation")


async def _handle_media_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    media_type: str,
    default_label: str,
) -> None:
    message = update.effective_message
    user = update.effective_user

    if message is None or user is None:
        return

    services = get_services(context)
    if not await _ensure_access(message, services, user.id):
        return

    caption = (message.caption or "").strip()
    if not _has_prefix(caption, STORE_PREFIX):
        await reply_with_keyboard(message, f"Use `store*` in the caption to save this {default_label}.")
        return

    content, keywords = _parse_store_payload(_extract_command_payload(caption, STORE_PREFIX))
    if content is None:
        await reply_with_keyboard(message, STORE_USAGE)
        return

    media_obj = getattr(message, media_type)
    if media_obj is None:
        return

    # Handle file_id extraction based on media type
    if media_type == "photo":
        # For photos, use the largest size
        if message.photo and len(message.photo) > 0:
            file_id = message.photo[-1].file_id
            file_name = None
            mime_type = None
        else:
            await reply_with_keyboard(message, "Failed to process photo. Please try again.")
            return
    else:
        file_id = media_obj.file_id
        file_name = getattr(media_obj, 'file_name', None)
        mime_type = getattr(media_obj, 'mime_type', None)

    fallback = [default_label]
    if file_name:
        fallback.append(file_name)
    if mime_type:
        fallback.append(mime_type)

    if media_type == "document" and mime_type and mime_type.startswith("image/"):
        # Treat image documents as photos
        media_type = "photo"
        default_label = "photo"
        LOGGER.info(f"Processing image document as photo: {mime_type}")

    await _store_media_note(
        message=message,
        services=services,
        user_id=user.id,
        content=content,
        note_type=media_type,
        file_id=file_id,
        keywords=keywords,
        file_name=file_name,
        mime_type=mime_type,
        fallback=fallback,
    )


async def handle_invalid_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    del context

    message = update.effective_message
    if message is None:
        return

    await reply_with_keyboard(message, INVALID_COMMAND_MESSAGE)


async def handle_application_error(
    update: object, context: ContextTypes.DEFAULT_TYPE
) -> None:
    LOGGER.exception("Unhandled bot error", exc_info=context.error)

    if isinstance(update, Update) and update.effective_message is not None:
        await reply_with_keyboard(update.effective_message, "Operation failed.")


def register_message_handlers(application: Application) -> None:
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message)
    )
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo_message))
    application.add_handler(MessageHandler(filters.AUDIO, handle_audio_message))
    application.add_handler(MessageHandler(filters.VIDEO, handle_video_message))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice_message))
    application.add_handler(MessageHandler(filters.ANIMATION, handle_animation_message))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document_message))
    application.add_handler(MessageHandler(filters.ALL, handle_invalid_message))
    application.add_error_handler(handle_application_error)


async def _ensure_access(message: Message, services: Any, user_id: int) -> bool:
    if not services.database.is_available:
        await reply_with_keyboard(message, DATABASE_ERROR_MESSAGE)
        return False
    if not services.note_service.is_user_allowed(user_id):
        await reply_with_keyboard(message, UNAUTHORIZED_MESSAGE)
        return False
    return True


async def _handle_search(
    message: Message,
    services: Any,
    user_id: int,
    text: str,
) -> None:
    payload = _extract_command_payload(text, SEARCH_PREFIX)
    if not payload:
        await reply_with_keyboard(message, SEARCH_USAGE)
        return

    if payload.isdigit():
        note = await services.note_service.get_note_by_id(user_id, int(payload))
        if note is None:
            await reply_with_keyboard(message, "ID not found")
            return

        await _send_note(message, note)
        return

    try:
        results = await services.note_service.search_notes(user_id, payload)
    except ValidationError as error:
        await reply_with_keyboard(message, str(error))
        return

    if not results:
        await reply_with_keyboard(message, "No matching data found.")
        return

    await reply_with_keyboard(message, f"Matches found: {len(results)}")
    for note in results:
        await _send_note(message, note)


async def _handle_store_text(
    message: Message,
    services: Any,
    user_id: int,
    text: str,
) -> None:
    payload = _extract_command_payload(text, STORE_PREFIX)
    content, keywords = _parse_store_payload(payload)
    if content is None:
        await reply_with_keyboard(message, STORE_USAGE)
        return

    try:
        result = await services.note_service.store_text_note(
            user_id=user_id,
            content=content,
            keywords=keywords,
        )
    except ValidationError as error:
        await reply_with_keyboard(message, str(error))
        return
    except NoteServiceError:
        await reply_with_keyboard(message, DATABASE_ERROR_MESSAGE)
        return

    await reply_with_keyboard(
        message,
        format_store_response(result.note_id, result.keywords, status="Stored"),
    )


async def _handle_delete(
    message: Message,
    services: Any,
    user_id: int,
    text: str,
) -> None:
    payload = _extract_command_payload(text, DELETE_PREFIX)
    if not payload or not payload.isdigit():
        await reply_with_keyboard(message, DELETE_USAGE)
        return

    deleted = await services.note_service.delete_note(user_id, int(payload))
    if not deleted:
        await reply_with_keyboard(message, "ID not found")
        return

    await reply_with_keyboard(message, f"Deleted note {payload}.")


async def _handle_update(
    message: Message,
    services: Any,
    user_id: int,
    text: str,
) -> None:
    payload = _extract_command_payload(text, UPDATE_PREFIX)
    if not payload or "|" not in payload:
        await reply_with_keyboard(message, UPDATE_USAGE)
        return

    note_id_text, remainder = payload.split("|", 1)
    note_id_text = note_id_text.strip()
    if not note_id_text or not note_id_text.isdigit():
        await reply_with_keyboard(message, UPDATE_USAGE)
        return

    content, keywords = _parse_store_payload(remainder.strip())
    if content is None:
        await reply_with_keyboard(message, UPDATE_USAGE)
        return

    try:
        result = await services.note_service.update_note(
            user_id=user_id,
            note_id=int(note_id_text),
            content=content,
            keywords=keywords,
        )
    except ValidationError as error:
        await reply_with_keyboard(message, str(error))
        return

    if result is None:
        await reply_with_keyboard(message, "ID not found")
        return

    await reply_with_keyboard(
        message,
        format_store_response(result.note_id, result.keywords, status="Updated"),
    )


async def _store_media_note(
    *,
    message: Message,
    services: Any,
    user_id: int,
    content: str,
    note_type: str,
    file_id: str,
    keywords: list[str],
    fallback: list[str],
    file_name: str | None = None,
    mime_type: str | None = None,
) -> None:
    try:
        result = await services.note_service.store_media_note(
            user_id=user_id,
            content=content,
            note_type=note_type,
            file_id=file_id,
            keywords=keywords,
            file_name=file_name,
            mime_type=mime_type,
            fallback=fallback,
        )
    except ValidationError as error:
        await reply_with_keyboard(message, str(error))
        return
    except NoteServiceError:
        await reply_with_keyboard(message, DATABASE_ERROR_MESSAGE)
        return

    await reply_with_keyboard(
        message,
        format_store_response(result.note_id, result.keywords, status="Stored"),
    )


async def _send_note(message: Message, note: Any) -> None:
    header = _build_note_header(note)

    media_reply_methods = {
        "photo": lambda: message.reply_photo(
            photo=note.file_id,
            caption=_truncate_text(header, MAX_MEDIA_CAPTION_LENGTH),
            reply_markup=build_command_keyboard(),
        ),
        "audio": lambda: message.reply_audio(
            audio=note.file_id,
            caption=_truncate_text(header, MAX_MEDIA_CAPTION_LENGTH),
            reply_markup=build_command_keyboard(),
        ),
        "video": lambda: message.reply_video(
            video=note.file_id,
            caption=_truncate_text(header, MAX_MEDIA_CAPTION_LENGTH),
            reply_markup=build_command_keyboard(),
        ),
        "voice": lambda: message.reply_voice(
            voice=note.file_id,
            caption=_truncate_text(header, MAX_MEDIA_CAPTION_LENGTH),
            reply_markup=build_command_keyboard(),
        ),
        "animation": lambda: message.reply_animation(
            animation=note.file_id,
            caption=_truncate_text(header, MAX_MEDIA_CAPTION_LENGTH),
            reply_markup=build_command_keyboard(),
        ),
        "document": lambda: message.reply_document(
            document=note.file_id,
            caption=_truncate_text(header, MAX_MEDIA_CAPTION_LENGTH),
            reply_markup=build_command_keyboard(),
        ),
    }

    if note.note_type in media_reply_methods and note.file_id:
        await media_reply_methods[note.note_type]()
        return

    body_segments = _split_text_for_telegram(
        note.content or "(empty)",
        MAX_TELEGRAM_MESSAGE_LENGTH - len(header) - 2,
    )
    if not body_segments:
        await reply_with_keyboard(message, f"{header}\n\n(empty)")
        return

    await reply_with_keyboard(message, f"{header}\n\n{body_segments[0]}")
    for segment in body_segments[1:]:
        await reply_with_keyboard(message, segment)


def _build_note_header(note: Any) -> str:
    lines = [
        f"ID: {note.note_id}",
        f"Type: {note.note_type}",
        f"Saved: {note.timestamp.astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')}",
    ]
    if note.file_name:
        lines.append(f"File: {note.file_name}")
    if note.keywords:
        lines.append(f"KW: {', '.join(note.keywords)}")
    if note.note_type != "text" and note.content:
        lines.append(f"Content: {note.content}")
    return "\n".join(lines)


def _parse_store_payload(payload: str) -> tuple[str | None, list[str]]:
    cleaned = payload.strip()
    if not cleaned:
        return None, []

    lower_cleaned = cleaned.lower()
    marker_index = lower_cleaned.find(KEYWORD_MARKER)
    if marker_index == -1:
        return cleaned, []

    content = cleaned[:marker_index].strip()
    keyword_text = cleaned[marker_index + len(KEYWORD_MARKER) :].strip()
    if not content:
        return None, []

    return content, normalize_keywords(keyword_text)


def _split_text_for_telegram(text: str, limit: int) -> list[str]:
    if not text:
        return []

    segments: list[str] = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = min(start + limit, text_length)
        if end < text_length:
            split_at = text.rfind("\n", start, end)
            if split_at == -1 or split_at <= start:
                split_at = text.rfind(" ", start, end)
            if split_at > start:
                end = split_at

        segment = text[start:end]
        if segment:
            segments.append(segment)

        start = end
        while start < text_length and text[start] in {"\n", " "}:
            start += 1

    return segments


def _truncate_text(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    if limit <= 3:
        return text[:limit]
    return text[: limit - 3].rstrip() + "..."


def _has_prefix(text: str, prefix: str) -> bool:
    return text.lower().startswith(prefix)


def _extract_command_payload(text: str, prefix: str) -> str:
    return text[len(prefix) :].strip()
