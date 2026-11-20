"""User profile display handler backed by UserService and Firestore."""

import html

from loguru import logger
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from app.database.models import UserModel
from app.keyboards.navigation import back_to_main_keyboard, profile_keyboard
from app.services.user_service import UserService
from app.utils.callbacks import get_callback_guard, run_guarded_callback, safe_edit_message
from app.utils.exceptions import DatabaseOperationError
from app.utils.sanitizers import mask_telegram_id
from app.utils.texts import DEFAULT_LANGUAGE, get_language_label, get_texts


def format_profile_text(
    user_id: int,
    profile: UserModel | None,
    language_code: str | None = None,
) -> str:
    """Format minimalist user profile message without inventing missing fields."""
    t = get_texts(language_code)
    not_set = t["profile_not_set"]

    if profile is None:
        return (
            f"<b>{t['profile_title']}</b>\n\n"
            f"Имя: {not_set}\n"
            f"Telegram ID: <code>{user_id}</code>\n"
            f"Username: {not_set}\n"
            f"Язык: {not_set}\n"
            f"Дата регистрации: {not_set}\n"
            f"Текущий тариф: {not_set}"
        )

    name = html.escape(profile.first_name.strip()) if profile.first_name.strip() else not_set
    username = f"@{html.escape(profile.username)}" if profile.username else not_set
    language_label = (
        get_language_label(profile.interface_language)
        if profile.interface_language
        else not_set
    )
    registered_at = (
        profile.created_at.strftime("%d.%m.%Y") if profile.created_at else not_set
    )

    sub = profile.subscription or {}
    plan_raw = sub.get("plan")
    if plan_raw == "free":
        plan_label = t["profile_plan_free"]
    elif isinstance(plan_raw, str) and plan_raw.strip():
        plan_label = html.escape(plan_raw.strip())
    else:
        plan_label = not_set

    return (
        f"<b>{t['profile_title']}</b>\n\n"
        f"Имя: {name}\n"
        f"Telegram ID: <code>{profile.telegram_id}</code>\n"
        f"Username: {username}\n"
        f"Язык: {language_label}\n"
        f"Дата регистрации: {registered_at}\n"
        f"Текущий тариф: {plan_label}"
    )


async def profile_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Load user profile from Firestore and display it cleanly."""
    query = update.callback_query
    if query is None or query.from_user is None:
        return

    guard = get_callback_guard(context.bot_data)
    user_service: UserService = context.bot_data["user_service"]
    telegram_user = query.from_user

    async def _handle() -> None:
        await query.answer()
        try:
            profile = await user_service.get_user_profile(telegram_user.id)
        except DatabaseOperationError:
            logger.error(
                "Database error loading profile for user={}.",
                mask_telegram_id(telegram_user.id),
            )
            t = get_texts(DEFAULT_LANGUAGE)
            await safe_edit_message(
                query=query,
                text=t["db_error"],
                reply_markup=back_to_main_keyboard(DEFAULT_LANGUAGE),
                parse_mode=None,
            )
            return

        lang = profile.interface_language if profile else DEFAULT_LANGUAGE
        text = format_profile_text(telegram_user.id, profile, language_code=lang)
        await safe_edit_message(
            query=query,
            text=text,
            reply_markup=profile_keyboard(lang),
            parse_mode=ParseMode.HTML,
        )

    await run_guarded_callback(guard, query, _handle)
