"""Inline keyboard builders for Astralio."""

from app.keyboards.main_menu import main_menu_keyboard
from app.keyboards.navigation import (
    back_to_main_keyboard,
    language_keyboard,
    profile_keyboard,
)

__all__ = [
    "back_to_main_keyboard",
    "language_keyboard",
    "main_menu_keyboard",
    "profile_keyboard",
]
