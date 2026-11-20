"""Help section handlers for Astralio."""

from telegram import Update
from telegram.ext import ContextTypes

from app.keyboards.navigation import back_to_main_keyboard
from app.utils.callbacks import get_callback_guard, run_guarded_callback, safe_edit_message
from app.utils.texts import DEFAULT_LANGUAGE, get_texts


async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display Astralio help section via inline navigation."""
    query = update.callback_query
    if query is None:
        return

    guard = get_callback_guard(context.bot_data)

    async def _handle() -> None:
        await query.answer()
        t = get_texts(DEFAULT_LANGUAGE)
        await safe_edit_message(
            query=query,
            text=t["help_section"],
            reply_markup=back_to_main_keyboard(DEFAULT_LANGUAGE),
            parse_mode=None,
        )

    await run_guarded_callback(guard, query, _handle)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display Astralio help section on /help command."""
    message = update.effective_message
    if message is None:
        return

    t = get_texts(DEFAULT_LANGUAGE)
    await message.reply_text(
        text=t["help_section"],
        reply_markup=back_to_main_keyboard(DEFAULT_LANGUAGE),
    )
