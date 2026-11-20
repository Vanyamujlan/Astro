"""Handler for the /start command."""

from loguru import logger
from telegram import Update
from telegram.ext import ContextTypes

from app.keyboards.main_menu import main_menu_keyboard
from app.services.user_service import UserService
from app.utils.exceptions import DatabaseOperationError
from app.utils.sanitizers import mask_telegram_id
from app.utils.texts import DEFAULT_LANGUAGE, get_texts


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start: register or sync user in Firestore and display the main menu."""
    effective_user = update.effective_user
    effective_message = update.effective_message
    if effective_user is None or effective_message is None:
        return

    user_service: UserService = context.bot_data["user_service"]
    interface_language = DEFAULT_LANGUAGE

    try:
        user, _is_new = await user_service.register_or_update_user(
            telegram_id=effective_user.id,
            username=effective_user.username,
            first_name=effective_user.first_name or "User",
            language_code=effective_user.language_code,
        )
        interface_language = user.interface_language
    except DatabaseOperationError:
        logger.error(
            "Database error during /start for user={}.",
            mask_telegram_id(effective_user.id),
        )
        t = get_texts(interface_language)
        await effective_message.reply_text(t["db_error"])
        return

    t = get_texts(interface_language)
    await effective_message.reply_text(
        text=t["main_menu"],
        reply_markup=main_menu_keyboard(interface_language),
    )
