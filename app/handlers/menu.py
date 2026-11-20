"""Main menu navigation, placeholder sections, and fallback command/callback handlers."""

from telegram import Update
from telegram.ext import ContextTypes

from app.keyboards.main_menu import main_menu_keyboard
from app.keyboards.navigation import back_to_main_keyboard
from app.utils.callbacks import get_callback_guard, run_guarded_callback, safe_edit_message
from app.utils.texts import DEFAULT_LANGUAGE, get_texts

_SECTION_TEXT_KEYS: dict[str, str] = {
    "menu:natal": "natal_section",
    "menu:compatibility": "compatibility_section",
    "menu:forecasts": "forecasts_section",
    "menu:premium": "premium_section",
}


async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Return user to the Astralio main menu by editing the current message."""
    query = update.callback_query
    if query is None:
        return

    guard = get_callback_guard(context.bot_data)

    async def _handle() -> None:
        await query.answer()
        t = get_texts(DEFAULT_LANGUAGE)
        await safe_edit_message(
            query=query,
            text=t["main_menu"],
            reply_markup=main_menu_keyboard(DEFAULT_LANGUAGE),
            parse_mode=None,
        )

    await run_guarded_callback(guard, query, _handle)


async def section_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display minimalist info section for Natal, Compatibility, Forecasts, or Premium."""
    query = update.callback_query
    if query is None:
        return

    guard = get_callback_guard(context.bot_data)
    data = query.data or ""
    text_key = _SECTION_TEXT_KEYS.get(data)
    if text_key is None:
        await unknown_callback_handler(update, context)
        return

    async def _handle() -> None:
        await query.answer()
        t = get_texts(DEFAULT_LANGUAGE)
        await safe_edit_message(
            query=query,
            text=t[text_key],
            reply_markup=back_to_main_keyboard(DEFAULT_LANGUAGE),
            parse_mode=None,
        )

    await run_guarded_callback(guard, query, _handle)


async def unknown_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Gracefully handle unknown or obsolete inline button callbacks."""
    query = update.callback_query
    if query is None:
        return

    t = get_texts(DEFAULT_LANGUAGE)
    await query.answer(t["unknown_callback"])


async def unknown_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Gracefully respond to unknown slash commands without crashing."""
    message = update.effective_message
    if message is None:
        return

    t = get_texts(DEFAULT_LANGUAGE)
    await message.reply_text(t["unknown_command"])
