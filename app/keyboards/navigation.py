"""Navigation, profile, and language selection inline keyboards."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.utils.texts import LANGUAGES, get_texts


def back_to_main_keyboard(language_code: str | None = None) -> InlineKeyboardMarkup:
    """Build a single-row navigation keyboard returning to the main menu."""
    t = get_texts(language_code)
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(t["btn_back"], callback_data="nav:main")]]
    )


def profile_keyboard(language_code: str | None = None) -> InlineKeyboardMarkup:
    """Build minimalist profile action keyboard."""
    t = get_texts(language_code)
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(t["btn_change_language"], callback_data="settings:language")],
            [InlineKeyboardButton(t["btn_back"], callback_data="nav:main")],
        ]
    )


def language_keyboard(
    current_language: str | None = None,
    language_code: str | None = None,
) -> InlineKeyboardMarkup:
    """Build language selection keyboard with active and planned languages."""
    t = get_texts(language_code)
    rows: list[list[InlineKeyboardButton]] = []

    for meta in LANGUAGES.values():
        if meta.enabled:
            prefix = "✓ " if meta.code == current_language else ""
            label = f"{prefix}{meta.label}"
        else:
            label = f"{meta.label} (скоро)"
        rows.append(
            [InlineKeyboardButton(label, callback_data=f"settings:lang:{meta.code}")]
        )

    rows.append([InlineKeyboardButton(t["btn_back"], callback_data="nav:back:profile")])
    return InlineKeyboardMarkup(rows)
