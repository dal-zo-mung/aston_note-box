from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone

from pymongo import ASCENDING, DESCENDING, TEXT, MongoClient, ReturnDocument
from pymongo.collection import Collection
from pymongo.errors import OperationFailure, PyMongoError

from utils.keywords import extract_keywords, normalize_keywords


LOGGER = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class StoredNote:
    note_id: int
    user_id: int
    content: str
    timestamp: datetime
    note_type: str
    keywords: list[str]
    file_id: str | None = None
    file_name: str | None = None
    mime_type: str | None = None


def connect_to_mongo(connection_string: str) -> MongoClient | None:
    try:
        client = MongoClient(
            connection_string,
            appname="telegram-storage-bot",
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            socketTimeoutMS=30000,
            retryWrites=True,
            tz_aware=True,
        )
        client.admin.command("ping")
        return client
    except PyMongoError:
        LOGGER.exception("Failed to connect to MongoDB.")
        return None


class Database:
    def __init__(
        self,
        *,
        mongo_uri: str,
        database_name: str,
        collection_name: str,
        counter_collection_name: str,
        user_collection_name: str,
    ) -> None:
        self._client = connect_to_mongo(mongo_uri)
        self._database_name = database_name
        self._collection_name = collection_name
        self._counter_collection_name = counter_collection_name
        self._user_collection_name = user_collection_name
        self._notes: Collection | None = None
        self._counters: Collection | None = None
        self._users: Collection | None = None
        self._initialize_collections()

    @property
    def is_available(self) -> bool:
        return (
            self._notes is not None
            and self._counters is not None
            and self._users is not None
        )

    def close(self) -> None:
        if self._client is not None:
            self._client.close()

    def _initialize_collections(self) -> None:
        if self._client is None:
            return

        database = self._client[self._database_name]
        self._notes = database[self._collection_name]
        self._counters = database[self._counter_collection_name]
        self._users = database[self._user_collection_name]

        try:
            # Helper function to create index if it doesn't exist
            def create_index_safe(collection, keys, **kwargs):
                try:
                    collection.create_index(keys, **kwargs)
                    LOGGER.info(f"Created index: {kwargs.get('name', 'unnamed')}")
                except OperationFailure as e:
                    if "already exists" in str(e):
                        LOGGER.info(f"Index already exists: {kwargs.get('name', 'unnamed')}")
                    else:
                        raise

            create_index_safe(
                self._notes,
                [("user_id", ASCENDING), ("note_id", ASCENDING)],
                unique=True,
                name="user_note_unique",
            )
            create_index_safe(
                self._notes,
                [("user_id", ASCENDING), ("timestamp", DESCENDING)],
                name="user_timestamp_desc",
            )
            create_index_safe(
                self._notes,
                [("user_id", ASCENDING), ("keywords", ASCENDING)],
                name="user_keywords",
            )
            create_index_safe(
                self._notes,
                [("content", TEXT), ("keywords", TEXT), ("file_name", TEXT)],
                default_language="none",
                weights={"keywords": 12, "file_name": 6, "content": 3},
                name="note_text_search",
            )
            create_index_safe(
                self._users,
                [("user_id", ASCENDING)],
                unique=True,
                name="user_profile_unique",
            )
        except PyMongoError:
            LOGGER.exception("Failed to initialize MongoDB indexes.")
            self._notes = None
            self._counters = None
            self._users = None

    def has_started(self, user_id: int) -> bool:
        if not self.is_available:
            return False

        try:
            document = self._users.find_one({"user_id": user_id}, projection={"_id": True})
            return document is not None
        except PyMongoError:
            LOGGER.exception("Failed to read user profile for %s.", user_id)
            return False

    def mark_started(self, user_id: int) -> bool:
        if not self.is_available:
            return False

        try:
            now = _utc_now()
            self._users.update_one(
                {"user_id": user_id},
                {
                    "$setOnInsert": {
                        "user_id": user_id,
                        "created_at": now,
                    },
                    "$set": {"last_started_at": now},
                },
                upsert=True,
            )
            return True
        except PyMongoError:
            LOGGER.exception("Failed to update user profile for %s.", user_id)
            return False

    def create_text_note(
        self,
        *,
        user_id: int,
        content: str,
        keywords: list[str] | None = None,
    ) -> int | None:
        return self._create_note(
            user_id=user_id,
            content=content,
            note_type="text",
            file_id=None,
            keywords=keywords,
            file_name=None,
            mime_type=None,
        )

    def create_media_note(
        self,
        *,
        user_id: int,
        content: str,
        note_type: str,
        file_id: str,
        keywords: list[str] | None = None,
        file_name: str | None = None,
        mime_type: str | None = None,
    ) -> int | None:
        return self._create_note(
            user_id=user_id,
            content=content,
            note_type=note_type,
            file_id=file_id,
            keywords=keywords,
            file_name=file_name,
            mime_type=mime_type,
        )

    def _create_note(
        self,
        *,
        user_id: int,
        content: str,
        note_type: str,
        file_id: str | None,
        keywords: list[str] | None,
        file_name: str | None,
        mime_type: str | None,
    ) -> int | None:
        if not self.is_available:
            return None

        try:
            note_id = self._next_note_id(user_id)
            fallback_keywords = [note_type]
            if file_name:
                fallback_keywords.append(file_name)
            if mime_type:
                fallback_keywords.append(mime_type)
            keyword_list = keywords or extract_keywords(content, fallback=fallback_keywords)
            self._notes.insert_one(
                {
                    "user_id": user_id,
                    "note_id": note_id,
                    "content": content,
                    "timestamp": _utc_now(),
                    "type": note_type,
                    "file_id": file_id,
                    "keywords": keyword_list,
                    "file_name": file_name,
                    "mime_type": mime_type,
                }
            )
            return note_id
        except PyMongoError:
            LOGGER.exception("Failed to insert note for user %s.", user_id)
            return None

    def _next_note_id(self, user_id: int) -> int:
        if not self.is_available:
            raise RuntimeError("MongoDB is not available.")

        counter = self._counters.find_one_and_update(
            {"_id": f"user:{user_id}"},
            {"$inc": {"seq": 1}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        return int(counter["seq"])

    def get_note_by_id(self, user_id: int, note_id: int) -> StoredNote | None:
        if not self.is_available:
            return None

        try:
            document = self._notes.find_one(
                {"user_id": user_id, "note_id": note_id},
                projection={"_id": False},
            )
        except PyMongoError:
            LOGGER.exception("Failed to fetch note %s for user %s.", note_id, user_id)
            return None

        return _build_note(document)

    def search_notes(
        self,
        user_id: int,
        query: str,
        *,
        limit: int = 5,
    ) -> list[StoredNote]:
        if not self.is_available or limit <= 0:
            return []

        cleaned_query = query.strip()
        if not cleaned_query:
            return []

        text_results = self._text_search_notes(user_id, cleaned_query, limit)
        if text_results:
            return text_results

        return self._fallback_search_notes(user_id, cleaned_query, limit)

    def _text_search_notes(
        self,
        user_id: int,
        cleaned_query: str,
        limit: int,
    ) -> list[StoredNote]:
        if not self.is_available:
            return []

        try:
            cursor = self._notes.find(
                {"user_id": user_id, "$text": {"$search": cleaned_query}},
                projection={"_id": False, "score": {"$meta": "textScore"}},
            ).sort([("score", {"$meta": "textScore"}), ("note_id", ASCENDING)]).limit(limit)
            return [note for note in (_build_note(document) for document in cursor) if note is not None]
        except OperationFailure:
            LOGGER.exception("MongoDB text search failed for user %s.", user_id)
            return []
        except PyMongoError:
            LOGGER.exception("Failed to search notes for user %s.", user_id)
            return []

    def _fallback_search_notes(
        self,
        user_id: int,
        cleaned_query: str,
        limit: int,
    ) -> list[StoredNote]:
        normalized_query = normalize_keywords(cleaned_query)
        regex = re.compile(re.escape(cleaned_query), re.IGNORECASE)
        filters: list[dict[str, object]] = [{"content": regex}, {"file_name": regex}]
        if normalized_query:
            filters.append({"keywords": {"$in": normalized_query}})

        try:
            cursor = self._notes.find(
                {"user_id": user_id, "$or": filters},
                projection={"_id": False},
            )
            notes = [_build_note(document) for document in cursor]
        except PyMongoError:
            LOGGER.exception("Fallback search failed for user %s.", user_id)
            return []

        filtered = [note for note in notes if note is not None]
        filtered.sort(
            key=lambda note: _search_score(note, cleaned_query, normalized_query),
            reverse=True,
        )
        return filtered[:limit]

    def update_note(
        self,
        *,
        user_id: int,
        note_id: int,
        content: str,
        keywords: list[str] | None = None,
    ) -> bool:
        if not self.is_available:
            return False

        existing = self.get_note_by_id(user_id, note_id)
        fallback_keywords = [existing.note_type] if existing is not None else ["text"]
        if existing and existing.file_name:
            fallback_keywords.append(existing.file_name)
        if existing and existing.mime_type:
            fallback_keywords.append(existing.mime_type)
        keyword_list = keywords or extract_keywords(content, fallback=fallback_keywords)

        try:
            result = self._notes.update_one(
                {"user_id": user_id, "note_id": note_id},
                {
                    "$set": {
                        "content": content,
                        "keywords": keyword_list,
                        "updated_at": _utc_now(),
                    }
                },
            )
            return result.matched_count > 0
        except PyMongoError:
            LOGGER.exception("Failed to update note %s for user %s.", note_id, user_id)
            return False

    def delete_note(self, user_id: int, note_id: int) -> bool:
        if not self.is_available:
            return False

        try:
            result = self._notes.delete_one({"user_id": user_id, "note_id": note_id})
            return result.deleted_count > 0
        except PyMongoError:
            LOGGER.exception("Failed to delete note %s for user %s.", note_id, user_id)
            return False

    def list_note_ids(self, user_id: int) -> list[int]:
        if not self.is_available:
            return []

        try:
            cursor = self._notes.find(
                {"user_id": user_id},
                projection={"_id": False, "note_id": True},
                sort=[("note_id", ASCENDING)],
            )
            return [int(document["note_id"]) for document in cursor]
        except PyMongoError:
            LOGGER.exception("Failed to list note IDs for user %s.", user_id)
            return []

    def count_user_notes(self, user_id: int) -> int:
        if not self.is_available:
            return 0

        try:
            return int(self._notes.count_documents({"user_id": user_id}))
        except PyMongoError:
            LOGGER.exception("Failed to count notes for user %s.", user_id)
            return 0


def _build_note(document: dict[str, object] | None) -> StoredNote | None:
    if document is None:
        return None

    timestamp = document.get("timestamp")
    if not isinstance(timestamp, datetime):
        timestamp = _utc_now()

    file_id = document.get("file_id")
    file_name = document.get("file_name")
    mime_type = document.get("mime_type")
    note_type = str(document.get("type", "text"))
    raw_keywords = document.get("keywords", [])
    keywords = [str(value) for value in raw_keywords] if isinstance(raw_keywords, list) else []

    return StoredNote(
        note_id=int(document["note_id"]),
        user_id=int(document["user_id"]),
        content=str(document.get("content", "")),
        timestamp=timestamp,
        note_type=note_type,
        keywords=keywords,
        file_id=str(file_id) if file_id is not None else None,
        file_name=str(file_name) if file_name is not None else None,
        mime_type=str(mime_type) if mime_type is not None else None,
    )


def _search_score(
    note: StoredNote,
    query: str,
    normalized_query: list[str],
) -> tuple[int, int, int]:
    query_lower = query.lower()
    keyword_hits = len(set(normalized_query) & set(note.keywords))
    file_name_text = note.file_name.lower() if note.file_name else ""
    exact_phrase = int(
        query_lower in note.content.lower()
        or query_lower in " ".join(note.keywords)
        or query_lower in file_name_text
    )
    return (exact_phrase, keyword_hits, note.note_id)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)

