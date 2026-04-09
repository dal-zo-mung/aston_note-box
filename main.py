from __future__ import annotations

import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

from telegram.ext import Application

from bot.commands import configure_bot_commands, register_command_handlers
from bot.dependencies import ServiceContainer
from bot.handlers import register_message_handlers
from config.settings import load_settings
from db.database import Database
from services.note_service import NoteService
from utils.logger import configure_logging


LOGGER = logging.getLogger(__name__)
ALLOWED_UPDATES = ["message"]


class _HealthcheckHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        body = b"Telegram bot is running."
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        LOGGER.debug("Healthcheck server: " + format, *args)


def _run_healthcheck_server(port: int) -> None:
    try:
        server = ThreadingHTTPServer(("0.0.0.0", port), _HealthcheckHandler)
    except OSError:
        LOGGER.exception("Failed to start healthcheck server on port %s.", port)
        return

    LOGGER.info("Healthcheck server listening on port %s.", port)
    server.serve_forever()


def start_healthcheck_server(port: int) -> None:
    thread = Thread(target=_run_healthcheck_server, args=(port,), daemon=True)
    thread.start()


def build_services() -> ServiceContainer:
    settings = load_settings()
    settings.validate_runtime()

    configure_logging(log_level=settings.log_level, log_path=settings.log_path)

    database = Database(
        mongo_uri=settings.mongo_uri,
        database_name=settings.mongo_database_name,
        collection_name=settings.mongo_collection_name,
        counter_collection_name=settings.mongo_counter_collection_name,
        user_collection_name=settings.mongo_user_collection_name,
    )
    note_service = NoteService(settings=settings, database=database)

    return ServiceContainer(
        settings=settings,
        database=database,
        note_service=note_service,
    )


async def on_startup(application: Application) -> None:
    await configure_bot_commands(application)
    LOGGER.info("Telegram bot started.")


async def on_shutdown(application: Application) -> None:
    services = application.bot_data.get("services")
    if services is not None:
        services.database.close()
    LOGGER.info("Telegram bot stopped.")


def main() -> None:
    services = build_services()
    settings = services.settings

    start_healthcheck_server(settings.healthcheck_port)

    application = (
        Application.builder()
        .token(settings.bot_token)
        .connect_timeout(settings.telegram_connect_timeout_seconds)
        .read_timeout(settings.telegram_read_timeout_seconds)
        .write_timeout(settings.telegram_write_timeout_seconds)
        .pool_timeout(settings.telegram_pool_timeout_seconds)
        .get_updates_connect_timeout(settings.telegram_connect_timeout_seconds)
        .get_updates_read_timeout(settings.telegram_read_timeout_seconds)
        .get_updates_write_timeout(settings.telegram_write_timeout_seconds)
        .get_updates_pool_timeout(settings.telegram_pool_timeout_seconds)
        .post_init(on_startup)
        .post_shutdown(on_shutdown)
        .build()
    )
    application.bot_data["services"] = services

    register_command_handlers(application)
    register_message_handlers(application)

    LOGGER.info("Starting polling loop.")
    application.run_polling(
        allowed_updates=ALLOWED_UPDATES,
        timeout=settings.telegram_poll_timeout_seconds,
        bootstrap_retries=settings.telegram_bootstrap_retries,
    )


if __name__ == "__main__":
    main()
