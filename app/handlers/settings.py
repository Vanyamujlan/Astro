"""Interface language settings handlers."""

from loguru import logger
from telegram import Update
from telegram.ext import ContextTypes

from app.keyboards.navigation import back_to_main_keyboard, language_keyboard
from app.services.user_service import UserService
from app.utils.callbacks import get_callback_guard, run_guarded_callback, safe_edit_message
from app.utils.exceptions import DatabaseOperationError, UserNotFoundError
from app.utils.sanitizers import mask_telegram_id
from app.utils.texts import DEFAULT_LANGUAGE, LANGUAGES, get_texts


async def language_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display language selection screen."""
    query = update.callback_query
    if query is None or query.from_user is None:
        return

    guard = get_callback_guard(context.bot_data)
    user_service: UserService = context.bot_data["user_service"]
    user_id = query.from_user.id

    async def _handle() -> None:
        await query.answer()
        current_lang = DEFAULT_LANGUAGE
        try:
            profile = await user_service.get_user_profile(user_id)
            if profile is not None and profile.interface_language:
                current_lang = profile.interface_language
        except DatabaseOperationError:
            logger.error(
                "Database error loading language setting for user={}.",
                mask_telegram_id(user_id),
            )
            t = get_texts(DEFAULT_LANGUAGE)
            await safe_edit_message(
                query=query,
                text=t["db_error"],
                reply_markup=back_to_main_keyboard(DEFAULT_LANGUAGE),
                parse_mode=None,
            )
            return

        t = get_texts(current_lang)
        await safe_edit_message(
            query=query,
            text=t["language_title"],
            reply_markup=language_keyboard(
                current_language=current_lang,
                language_code=current_lang,
            ),
            parse_mode=None,
        )

    await run_guarded_callback(guard, query, _handle)


async def set_language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle language button selection (`settings:lang:<code>`)."""
    query = update.callback_query
    if query is None or query.from_user is None:
        return

    guard = get_callback_guard(context.bot_data)
    user_service: UserService = context.bot_data["user_service"]
    user_id = query.from_user.id
    data = query.data or ""
    target_lang = data.rsplit(":", maxsplit=1)[-1]

    async def _handle() -> None:
        t = get_texts(DEFAULT_LANGUAGE)
        meta = LANGUAGES.get(target_lang)
        if meta is None:
            await query.answer(t["unknown_callback"])
            return

        if not meta.enabled:
            await query.answer(t["language_planned"])
            return

        try:
            updated = await user_service.change_interface_language(user_id, target_lang)
        except UserNotFoundError:
            updated, _ = await user_service.register_or_update_user(
                telegram_id=user_id,
                username=query.from_user.username,
                first_name=query.from_user.first_name or "User",
                language_code=query.from_user.language_code,
            )
            if updated.interface_language != target_lang:
                updated = await user_service.change_interface_language(user_id, target_lang)
        except DatabaseOperationError:
            logger.error(
                "Database error updating language for user={}.",
                mask_telegram_id(user_id),
            )
            await query.answer(t["db_error"], show_alert=True)
            return

        t_new = get_texts(updated.interface_language)
        await query.answer(t_new["language_updated"])
        await safe_edit_message(
            query=query,
            text=t_new["language_title"],
            reply_markup=language_keyboard(
                current_language=updated.interface_language,
                language_code=updated.interface_language,
            ),
            parse_mode=None,
        )

    await run_guarded_callback(guard, query, _handle)
