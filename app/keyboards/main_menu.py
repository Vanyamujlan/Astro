"""Main menu InlineKeyboardMarkup builder for Astralio."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.utils.texts import get_texts


def main_menu_keyboard(language_code: str | None = None) -> InlineKeyboardMarkup:
    """Build minimalist main menu inline keyboard (one button per row)."""
    t = get_texts(language_code)
    rows = [
        [InlineKeyboardButton(t["btn_natal"], callback_data="menu:natal")],
        [InlineKeyboardButton(t["btn_compatibility"], callback_data="menu:compatibility")],
        [InlineKeyboardButton(t["btn_forecasts"], callback_data="menu:forecasts")],
        [InlineKeyboardButton(t["btn_profile"], callback_data="menu:profile")],
        [InlineKeyboardButton(t["btn_premium"], callback_data="menu:premium")],
        [InlineKeyboardButton(t["btn_help"], callback_data="menu:help")],
    ]
    return InlineKeyboardMarkup(rows)
