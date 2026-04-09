from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from telegram.ext import ContextTypes

from config.settings import Settings
from db.database import Database
from services.note_service import NoteService


@dataclass(slots=True)
class ServiceContainer:
    settings: Settings
    database: Database
    note_service: NoteService


def get_services(context: ContextTypes.DEFAULT_TYPE) -> ServiceContainer:
    return cast(ServiceContainer, context.application.bot_data["services"])
