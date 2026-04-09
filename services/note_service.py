from __future__ import annotations

import asyncio
from dataclasses import dataclass

from config.settings import Settings
from db.database import Database, StoredNote
from utils.keywords import extract_keywords, normalize_keywords


class NoteServiceError(RuntimeError):
    pass


class ValidationError(NoteServiceError):
    pass


@dataclass(slots=True, frozen=True)
class SaveResult:
    note_id: int
    keywords: list[str]


class NoteService:
    def __init__(self, *, settings: Settings, database: Database) -> None:
        self._settings = settings
        self._database = database

    @property
    def database(self) -> Database:
        return self._database

    def is_user_allowed(self, user_id: int) -> bool:
        return self._settings.is_allowed_user(user_id)

    async def has_started(self, user_id: int) -> bool:
        return await asyncio.to_thread(self._database.has_started, user_id)

    async def mark_started(self, user_id: int) -> bool:
        return await asyncio.to_thread(self._database.mark_started, user_id)

    async def count_notes(self, user_id: int) -> int:
        return await asyncio.to_thread(self._database.count_user_notes, user_id)

    async def list_note_ids(self, user_id: int) -> list[int]:
        return await asyncio.to_thread(self._database.list_note_ids, user_id)

    async def get_note_by_id(self, user_id: int, note_id: int) -> StoredNote | None:
        return await asyncio.to_thread(self._database.get_note_by_id, user_id, note_id)

    async def search_notes(self, user_id: int, query: str) -> list[StoredNote]:
        cleaned_query = self._validate_search_query(query)
        return await asyncio.to_thread(
            self._database.search_notes,
            user_id,
            cleaned_query,
            limit=self._settings.search_limit,
        )

    async def store_text_note(
        self,
        *,
        user_id: int,
        content: str,
        keywords: list[str] | None = None,
    ) -> SaveResult:
        clean_content = self._validate_note_content(content)
        final_keywords = self._build_keywords(
            content=clean_content,
            provided_keywords=keywords,
            fallback=["text"],
        )
        note_id = await asyncio.to_thread(
            self._database.create_text_note,
            user_id=user_id,
            content=clean_content,
            keywords=final_keywords,
        )
        if note_id is None:
            raise NoteServiceError("Failed to store text note.")
        return SaveResult(note_id=note_id, keywords=final_keywords)

    async def store_media_note(
        self,
        *,
        user_id: int,
        content: str,
        note_type: str,
        file_id: str,
        keywords: list[str] | None = None,
        file_name: str | None = None,
        mime_type: str | None = None,
        fallback: list[str] | None = None,
    ) -> SaveResult:
        clean_content = self._validate_note_content(content)
        fallback_keywords = list(fallback or [note_type])
        if file_name:
            fallback_keywords.append(file_name)
        if mime_type:
            fallback_keywords.append(mime_type)

        final_keywords = self._build_keywords(
            content=clean_content,
            provided_keywords=keywords,
            fallback=fallback_keywords,
        )
        note_id = await asyncio.to_thread(
            self._database.create_media_note,
            user_id=user_id,
            content=clean_content,
            note_type=note_type,
            file_id=file_id,
            keywords=final_keywords,
            file_name=file_name,
            mime_type=mime_type,
        )
        if note_id is None:
            raise NoteServiceError(f"Failed to store {note_type} note.")
        return SaveResult(note_id=note_id, keywords=final_keywords)

    async def update_note(
        self,
        *,
        user_id: int,
        note_id: int,
        content: str,
        keywords: list[str] | None = None,
    ) -> SaveResult | None:
        clean_content = self._validate_note_content(content)
        existing = await self.get_note_by_id(user_id, note_id)
        if existing is None:
            return None

        fallback = [existing.note_type]
        if existing.file_name:
            fallback.append(existing.file_name)
        if existing.mime_type:
            fallback.append(existing.mime_type)
        final_keywords = self._build_keywords(
            content=clean_content,
            provided_keywords=keywords,
            fallback=fallback,
        )
        updated = await asyncio.to_thread(
            self._database.update_note,
            user_id=user_id,
            note_id=note_id,
            content=clean_content,
            keywords=final_keywords,
        )
        if not updated:
            return None
        return SaveResult(note_id=note_id, keywords=final_keywords)

    async def delete_note(self, user_id: int, note_id: int) -> bool:
        return await asyncio.to_thread(self._database.delete_note, user_id, note_id)

    def _validate_note_content(self, content: str) -> str:
        cleaned = content.strip()
        if not cleaned:
            raise ValidationError("Content cannot be empty.")
        if len(cleaned) > self._settings.max_note_content_length:
            raise ValidationError(
                f"Content is too long. Maximum length is {self._settings.max_note_content_length} characters."
            )
        return cleaned

    def _validate_search_query(self, query: str) -> str:
        cleaned = query.strip()
        if not cleaned:
            raise ValidationError("Search query cannot be empty.")
        if len(cleaned) > self._settings.max_search_query_length:
            raise ValidationError(
                f"Search query is too long. Maximum length is {self._settings.max_search_query_length} characters."
            )
        return cleaned

    def _build_keywords(
        self,
        *,
        content: str,
        provided_keywords: list[str] | None,
        fallback: list[str],
    ) -> list[str]:
        if provided_keywords:
            normalized = normalize_keywords(" ".join(provided_keywords))
            if normalized:
                return normalized[: self._settings.max_keywords]

        auto_keywords = extract_keywords(content, fallback=fallback)
        return auto_keywords[: self._settings.max_keywords]
