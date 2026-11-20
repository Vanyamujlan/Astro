"""Telegram application setup and lifecycle helpers."""

from app.bot.setup import create_application, global_error_handler

__all__ = ["create_application", "global_error_handler"]
