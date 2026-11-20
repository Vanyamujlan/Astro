"""Telegram Application builder, handler registration, and error handling."""

from loguru import logger
from telegram import Update
from telegram.error import (
    Conflict,
    Forbidden,
    InvalidToken,
    NetworkError,
    RetryAfter,
    TelegramError,
    TimedOut,
)
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from app.config import Settings
from app.handlers.help import help_callback, help_command
from app.handlers.menu import (
    main_menu_callback,
    section_callback,
    unknown_callback_handler,
    unknown_command_handler,
)
from app.handlers.profile import profile_callback
from app.handlers.settings import language_menu_callback, set_language_callback
from app.handlers.start import start_handler
from app.services.user_service import UserService
from app.utils.callbacks import CallbackGuard
from app.utils.exceptions import (
    ConfigurationError,
    DatabaseConnectionError,
    DatabaseOperationError,
)
from app.utils.sanitizers import mask_telegram_id, sanitize_secrets


async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle uncaught exceptions across handlers without stopping the bot."""
    err = context.error
    user_ref = "unknown"
    if isinstance(update, Update) and update.effective_user is not None:
        user_ref = mask_telegram_id(update.effective_user.id)

    if isinstance(err, InvalidToken):
        logger.critical("Telegram Bot API rejected BOT_TOKEN (InvalidToken).")
        return

    if isinstance(err, Conflict):
        logger.error(
            "Telegram polling Conflict: another bot instance or active webhook is running."
        )
        return

    if isinstance(err, RetryAfter):
        logger.warning(
            "Telegram rate limit hit (retry_after={}s) for user={}.",
            err.retry_after,
            user_ref,
        )
        return

    if isinstance(err, Forbidden):
        logger.info("Bot was blocked or lacks permissions for user={}.", user_ref)
        return

    if isinstance(err, (TimedOut, NetworkError)):
        logger.warning(
            "Transient Telegram network issue ({}) for user={}.",
            type(err).__name__,
            user_ref,
        )
        return

    if isinstance(err, TelegramError):
        logger.error(
            "Telegram API error for user={}: {} ({})",
            user_ref,
            type(err).__name__,
            sanitize_secrets(str(err)),
        )
    elif isinstance(err, (DatabaseConnectionError, DatabaseOperationError)):
        logger.error(
            "Firebase/Firestore error for user={}: {}",
            user_ref,
            type(err).__name__,
        )
    elif isinstance(err, ConfigurationError):
        logger.critical("Configuration error encountered: {}", sanitize_secrets(str(err)))
    else:
        logger.exception(
            "Unexpected error while processing update for user={}: {}",
            user_ref,
            type(err).__name__ if err is not None else "UnknownError",
        )

    if isinstance(update, Update):
        if update.callback_query is not None:
            try:
                await update.callback_query.answer(
                    "Временная ошибка. Попробуйте позже.",
                    show_alert=False,
                )
            except TelegramError as exc:
                logger.debug(
                    "Failed to answer callback during error recovery: {}",
                    type(exc).__name__,
                )
            return

        if update.effective_message is not None:
            try:
                await update.effective_message.reply_text(
                    "Произошла непредвиденная ошибка. Пожалуйста, повторите попытку позже."
                )
            except TelegramError as exc:
                logger.debug(
                    "Failed to notify user={} about error: {}",
                    user_ref,
                    type(exc).__name__,
                )


def create_application(settings: Settings, user_service: UserService) -> Application:
    """Build and configure the async Telegram Application instance."""
    application = (
        ApplicationBuilder()
        .token(settings.bot_token.get_secret_value())
        .build()
    )

    application.bot_data["user_service"] = user_service
    application.bot_data["callback_guard"] = CallbackGuard()

    # Commands (registered before unknown command fallback)
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command_handler))

    # Navigation & Sections
    application.add_handler(CallbackQueryHandler(main_menu_callback, pattern=r"^nav:main$"))
    application.add_handler(
        CallbackQueryHandler(
            section_callback,
            pattern=r"^menu:(natal|compatibility|forecasts|premium)$",
        )
    )
    application.add_handler(
        CallbackQueryHandler(profile_callback, pattern=r"^(menu:profile|nav:back:profile)$")
    )
    application.add_handler(
        CallbackQueryHandler(language_menu_callback, pattern=r"^settings:language$")
    )
    application.add_handler(
        CallbackQueryHandler(set_language_callback, pattern=r"^settings:lang:[a-z]{2}$")
    )
    application.add_handler(CallbackQueryHandler(help_callback, pattern=r"^menu:help$"))

    # Fallback for any unknown or outdated callback_data (must be registered last)
    application.add_handler(CallbackQueryHandler(unknown_callback_handler))

    application.add_error_handler(global_error_handler)

    logger.info("Astralio Telegram Application configured (environment={}).", settings.environment)
    return application
