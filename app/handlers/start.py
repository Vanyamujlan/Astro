"""Handler for the /start command."""

from firebase_admin.exceptions import FirebaseError
from google.api_core.exceptions import GoogleAPIError
from google.auth.exceptions import GoogleAuthError
from loguru import logger
from telegram import Update
from telegram.ext import ContextTypes

from app.keyboards.main_menu import main_menu_keyboard
from app.utils.exceptions import DatabaseConnectionError, DatabaseOperationError
from app.utils.sanitizers import mask_telegram_id
from app.utils.texts import DEFAULT_LANGUAGE, get_texts


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start: register or sync user in Firestore and display the main menu."""
    effective_user = update.effective_user
    effective_message = update.effective_message
    if effective_user is None or effective_message is None:
        return

    interface_language = DEFAULT_LANGUAGE
    bot_data = getattr(context, "bot_data", None)
    user_service = bot_data.get("user_service") if isinstance(bot_data, dict) else None
    if user_service is None or not callable(
        getattr(user_service, "register_or_update_user", None)
    ):
        logger.error(
            "UserService is missing or invalid in context.bot_data during /start for user={}.",
            mask_telegram_id(effective_user.id),
        )
        t = get_texts(interface_language)
        await effective_message.reply_text(t["service_unavailable"])
        return

    try:
        user, _is_new = await user_service.register_or_update_user(
            telegram_id=effective_user.id,
            username=effective_user.username,
            first_name=effective_user.first_name or "User",
            language_code=effective_user.language_code,
        )
        if getattr(user, "interface_language", None):
            interface_language = user.interface_language
    except (
        DatabaseConnectionError,
        DatabaseOperationError,
        FirebaseError,
        GoogleAPIError,
        GoogleAuthError,
    ) as exc:
        cause_name = type(exc.__cause__).__name__ if exc.__cause__ is not None else "None"
        logger.error(
            "Firebase/Firestore error during /start for user={}: {} (cause={}).",
            mask_telegram_id(effective_user.id),
            type(exc).__name__,
            cause_name,
        )
        t = get_texts(interface_language)
        await effective_message.reply_text(t["db_error"])
        return

    t = get_texts(interface_language)
    await effective_message.reply_text(
        text=t["main_menu"],
        reply_markup=main_menu_keyboard(interface_language),
    )
