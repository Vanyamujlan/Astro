"""Async application entrypoint for the Astralio Telegram bot."""

import asyncio
import signal
import sys

from loguru import logger
from telegram import Update
from telegram.error import InvalidToken, TelegramError

from app.bot.setup import create_application
from app.config import Settings, load_settings
from app.database.firebase import close_firebase, init_firebase
from app.database.repositories.user_repository import UserRepository
from app.logging_config import setup_logging
from app.services.user_service import UserService
from app.utils.exceptions import ConfigurationError, DatabaseConnectionError
from app.utils.sanitizers import sanitize_secrets


async def run_bot(settings: Settings) -> None:
    """Initialize Firebase, wire dependencies, and run Telegram polling until stopped."""
    db_client = init_firebase(settings)
    user_repository = UserRepository(db_client)
    user_service = UserService(user_repository)
    application = create_application(settings=settings, user_service=user_service)

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except NotImplementedError:
            # Windows event loops do not support add_signal_handler
            pass

    def _polling_error_callback(exc: TelegramError) -> None:
        application.create_task(application.process_error(error=exc, update=None))

    initialized = False
    try:
        await application.initialize()
        initialized = True
        await application.start()
        if application.updater is None:
            raise RuntimeError("Telegram Application updater is not initialized.")
        await application.updater.start_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=False,
            error_callback=_polling_error_callback,
        )
        logger.info("Astralio bot polling started.")
        await stop_event.wait()
    except InvalidToken as exc:
        logger.critical("Telegram rejected BOT_TOKEN during startup (InvalidToken).")
        raise ConfigurationError("Недействительный BOT_TOKEN.") from exc
    except TelegramError as exc:
        logger.critical(
            "Telegram Bot API failure during startup: {} ({})",
            type(exc).__name__,
            sanitize_secrets(str(exc)),
        )
        raise
    finally:
        # Stop updater and application BEFORE shutdown() to avoid
        # RuntimeError('This Application is still running!').
        if application.updater is not None and application.updater.running:
            await application.updater.stop()
        if application.running:
            await application.stop()
        if initialized:
            await application.shutdown()
        close_firebase()
        logger.info("Astralio bot shutdown complete.")


def main() -> int:
    """Synchronous CLI entrypoint loading configuration and starting the async bot."""
    try:
        settings = load_settings()
    except ConfigurationError as exc:
        print(f"[CONFIG ERROR] {exc}", file=sys.stderr)
        return 1

    setup_logging(log_level=settings.log_level, environment=settings.environment)

    try:
        asyncio.run(run_bot(settings))
    except KeyboardInterrupt:
        logger.info("Bot stopped by keyboard interrupt.")
    except ConfigurationError as exc:
        logger.critical("Startup aborted due to invalid configuration: {}", exc)
        return 1
    except DatabaseConnectionError as exc:
        logger.critical("Startup aborted due to Firebase connection error: {}", exc)
        return 1
    except Exception as exc:  # noqa: BLE001
        logger.critical("Fatal unhandled exception during bot execution: {}", type(exc).__name__)
        return 1
    return 0
