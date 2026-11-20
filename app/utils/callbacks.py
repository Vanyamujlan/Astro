"""Helpers for callback double-tap protection and safe message editing."""

import asyncio
import time
from collections.abc import Awaitable, Callable

from loguru import logger
from telegram import CallbackQuery, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.error import BadRequest, TelegramError


class CallbackGuard:
    """Prevents duplicate processing when a user taps inline buttons rapidly."""

    def __init__(self, cooldown_seconds: float = 0.35) -> None:
        self._cooldown = cooldown_seconds
        self._in_flight: set[int] = set()
        self._last_tap: dict[tuple[int, str], float] = {}

    def try_acquire(self, user_id: int, callback_data: str) -> bool:
        """Return True if callback should be processed, False if duplicate/throttled."""
        if user_id in self._in_flight:
            return False

        now = time.monotonic()
        if len(self._last_tap) > 1000:
            cutoff = now - max(self._cooldown * 10, 5.0)
            self._last_tap = {
                k: ts for k, ts in self._last_tap.items() if ts >= cutoff
            }

        key = (user_id, callback_data)
        last = self._last_tap.get(key)
        if last is not None and (now - last) < self._cooldown:
            return False

        self._last_tap[key] = now
        self._in_flight.add(user_id)
        return True

    def release(self, user_id: int) -> None:
        """Release in-flight lock for user_id."""
        self._in_flight.discard(user_id)


async def run_guarded_callback(
    guard: CallbackGuard,
    query: CallbackQuery,
    handler: Callable[[], Awaitable[None]],
) -> None:
    """Execute callback handler with duplicate-tap protection."""
    user = query.from_user
    data = query.data or ""
    if user is None:
        await query.answer()
        return

    if not guard.try_acquire(user.id, data):
        await query.answer()
        return

    try:
        await handler()
    finally:
        guard.release(user.id)


async def safe_edit_message(
    query: CallbackQuery,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    parse_mode: str | None = ParseMode.HTML,
) -> None:
    """Edit callback message safely, ignoring 'Message is not modified' errors."""
    try:
        await query.edit_message_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
        )
    except BadRequest as exc:
        if "Message is not modified" in str(exc):
            logger.debug("Ignored unchanged message edit for callback.")
            return
        raise
    except TelegramError:
        raise


def get_callback_guard(bot_data: dict) -> CallbackGuard:
    """Retrieve or lazily create a shared CallbackGuard inside application.bot_data."""
    guard = bot_data.get("callback_guard")
    if not isinstance(guard, CallbackGuard):
        guard = CallbackGuard()
        bot_data["callback_guard"] = guard
    return guard


async def yield_to_loop() -> None:
    """Tiny async helper for cooperative scheduling if needed."""
    await asyncio.sleep(0)
