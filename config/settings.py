from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def _parse_positive_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    value = int(raw)
    if value <= 0:
        raise ValueError(f"{name} must be a positive integer.")
    return value


def _parse_non_negative_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    value = int(raw)
    if value < 0:
        raise ValueError(f"{name} must be zero or greater.")
    return value


def _parse_positive_float(name: str, default: float) -> float:
    raw = os.getenv(name, str(default)).strip()
    value = float(raw)
    if value <= 0:
        raise ValueError(f"{name} must be a positive number.")
    return value


def _parse_allowed_user_ids(raw_value: str) -> frozenset[int]:
    ids: set[int] = set()
    for raw_token in raw_value.split(","):
        token = raw_token.strip()
        if not token:
            continue
        if not token.isdigit():
            raise ValueError(
                "ALLOWED_TELEGRAM_USER_IDS must be a comma-separated list of Telegram numeric user IDs."
            )
        ids.add(int(token))
    return frozenset(ids)


@dataclass(slots=True, frozen=True)
class Settings:
    bot_token: str
    mongo_uri: str
    mongo_database_name: str
    mongo_collection_name: str
    mongo_counter_collection_name: str
    mongo_user_collection_name: str
    allowed_telegram_user_ids: frozenset[int]
    telegram_connect_timeout_seconds: float
    telegram_read_timeout_seconds: float
    telegram_write_timeout_seconds: float
    telegram_pool_timeout_seconds: float
    telegram_poll_timeout_seconds: int
    telegram_bootstrap_retries: int
    healthcheck_port: int
    search_limit: int
    max_note_content_length: int
    max_search_query_length: int
    max_keywords: int
    logs_dir: Path
    log_path: Path
    log_level: str

    def ensure_directories(self) -> None:
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def is_allowed_user(self, user_id: int) -> bool:
        return (
            not self.allowed_telegram_user_ids
            or user_id in self.allowed_telegram_user_ids
        )

    def validate_runtime(self) -> None:
        missing: list[str] = []

        if not self.bot_token or self.bot_token == "your_telegram_bot_token":
            missing.append("BOT_TOKEN")
        if not self.mongo_uri or self.mongo_uri == "your_mongodb_connection_string":
            missing.append("MONGO_URI")

        if missing:
            joined = ", ".join(missing)
            raise ValueError(
                f"Missing runtime configuration for: {joined}. Update your environment variables or .env file."
            )


def load_settings() -> Settings:
    logs_dir = PROJECT_ROOT / "storage" / "logs"
    log_path = logs_dir / "bot.log"
    healthcheck_default = _parse_positive_int("HEALTHCHECK_PORT", 7860)

    settings = Settings(
        bot_token=os.getenv("BOT_TOKEN", "").strip(),
        mongo_uri=os.getenv("MONGO_URI", "").strip(),
        mongo_database_name=os.getenv("MONGO_DATABASE", "telegram_bot").strip(),
        mongo_collection_name=os.getenv("MONGO_COLLECTION", "notes").strip(),
        mongo_counter_collection_name=os.getenv(
            "MONGO_COUNTER_COLLECTION", "note_counters"
        ).strip(),
        mongo_user_collection_name=os.getenv(
            "MONGO_USER_COLLECTION", "user_profiles"
        ).strip(),
        allowed_telegram_user_ids=_parse_allowed_user_ids(
            os.getenv("ALLOWED_TELEGRAM_USER_IDS", "")
        ),
        telegram_connect_timeout_seconds=_parse_positive_float(
            "TELEGRAM_CONNECT_TIMEOUT_SECONDS", 30.0
        ),
        telegram_read_timeout_seconds=_parse_positive_float(
            "TELEGRAM_READ_TIMEOUT_SECONDS", 30.0
        ),
        telegram_write_timeout_seconds=_parse_positive_float(
            "TELEGRAM_WRITE_TIMEOUT_SECONDS", 30.0
        ),
        telegram_pool_timeout_seconds=_parse_positive_float(
            "TELEGRAM_POOL_TIMEOUT_SECONDS", 30.0
        ),
        telegram_poll_timeout_seconds=_parse_positive_int(
            "TELEGRAM_POLL_TIMEOUT_SECONDS", 30
        ),
        telegram_bootstrap_retries=_parse_non_negative_int(
            "TELEGRAM_BOOTSTRAP_RETRIES", 3
        ),
        healthcheck_port=_parse_positive_int("PORT", healthcheck_default),
        search_limit=_parse_positive_int("SEARCH_LIMIT", 5),
        max_note_content_length=_parse_positive_int(
            "MAX_NOTE_CONTENT_LENGTH", 4000
        ),
        max_search_query_length=_parse_positive_int(
            "MAX_SEARCH_QUERY_LENGTH", 120
        ),
        max_keywords=_parse_positive_int("MAX_KEYWORDS", 5),
        logs_dir=logs_dir,
        log_path=log_path,
        log_level=os.getenv("LOG_LEVEL", "INFO").strip().upper(),
    )
    settings.ensure_directories()
    return settings
