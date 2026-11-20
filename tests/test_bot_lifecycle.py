"""Tests for bot lifecycle, graceful shutdown, unknown commands, and error handling."""

import asyncio
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.bot.setup import create_application, global_error_handler
from app.config import Settings
from app.handlers.menu import unknown_command_handler
from app.main import run_bot
from app.utils.exceptions import ConfigurationError, DatabaseOperationError
from telegram.error import Conflict, InvalidToken, NetworkError


class FakeEvent:
    """Helper event that triggers shutdown right after polling starts."""

    def __init__(self) -> None:
        self._event = asyncio.Event()

    def set(self) -> None:
        self._event.set()

    async def wait(self) -> None:
        # Yield briefly then exit so run_bot executes full startup + shutdown
        await asyncio.sleep(0)
        self._event.set()
        await self._event.wait()


async def test_run_bot_startup_and_graceful_shutdown_order() -> None:
    """run_bot initializes, starts polling with error_callback, and shuts down cleanly."""
    settings = Settings(
        bot_token="123456:FakeLifecycleToken",  # type: ignore[arg-type]
        firebase_project_id="astralio-test",
        firebase_client_email="firebase-adminsdk-test@astralio-test.iam.gserviceaccount.com",
        firebase_private_key=(
            "-----BEGIN PRIVATE KEY-----\\n"  # type: ignore[arg-type]
            "YXN0cmFsaW8tdGVzdC1wbGFjZWhvbGRlcg==\\n"
            "-----END PRIVATE KEY-----"
        ),
    )
    events: list[str] = []

    fake_updater = MagicMock()
    fake_updater.running = False

    async def fake_start_polling(**kwargs: Any) -> None:
        assert kwargs.get("error_callback") is not None
        fake_updater.running = True
        events.append("updater.start_polling")

    async def fake_updater_stop() -> None:
        fake_updater.running = False
        events.append("updater.stop")

    fake_updater.start_polling = AsyncMock(side_effect=fake_start_polling)
    fake_updater.stop = AsyncMock(side_effect=fake_updater_stop)

    fake_app = MagicMock()
    fake_app.running = False
    fake_app.updater = fake_updater

    async def fake_initialize() -> None:
        events.append("app.initialize")

    async def fake_start() -> None:
        fake_app.running = True
        events.append("app.start")

    async def fake_stop() -> None:
        fake_app.running = False
        events.append("app.stop")

    async def fake_shutdown() -> None:
        if fake_app.running:
            raise RuntimeError("This Application is still running!")
        events.append("app.shutdown")

    fake_app.initialize = AsyncMock(side_effect=fake_initialize)
    fake_app.start = AsyncMock(side_effect=fake_start)
    fake_app.stop = AsyncMock(side_effect=fake_stop)
    fake_app.shutdown = AsyncMock(side_effect=fake_shutdown)

    def fake_close_firebase() -> None:
        events.append("close_firebase")

    with (
        patch("app.main.init_firebase", return_value=MagicMock()),
        patch("app.main.close_firebase", side_effect=fake_close_firebase),
        patch("app.main.create_application", return_value=fake_app),
        patch("app.main.asyncio.Event", return_value=FakeEvent()),
    ):
        await run_bot(settings)

    assert events == [
        "app.initialize",
        "app.start",
        "updater.start_polling",
        "updater.stop",
        "app.stop",
        "app.shutdown",
        "close_firebase",
    ]


async def test_run_bot_invalid_token_cleans_up_resources() -> None:
    """InvalidToken during startup raises ConfigurationError and still shuts down cleanly."""
    settings = Settings(
        bot_token="123456:InvalidFakeToken",  # type: ignore[arg-type]
        firebase_project_id="astralio-test",
        firebase_client_email="firebase-adminsdk-test@astralio-test.iam.gserviceaccount.com",
        firebase_private_key=(
            "-----BEGIN PRIVATE KEY-----\\n"  # type: ignore[arg-type]
            "YXN0cmFsaW8tdGVzdC1wbGFjZWhvbGRlcg==\\n"
            "-----END PRIVATE KEY-----"
        ),
    )
    fake_app = MagicMock()
    fake_app.running = False
    fake_app.updater = MagicMock(running=False)
    fake_app.initialize = AsyncMock(side_effect=InvalidToken())
    fake_app.shutdown = AsyncMock()

    with (
        patch("app.main.init_firebase", return_value=MagicMock()),
        patch("app.main.close_firebase") as mock_close_firebase,
        patch("app.main.create_application", return_value=fake_app),
    ):
        with pytest.raises(ConfigurationError):
            await run_bot(settings)

    mock_close_firebase.assert_called_once()
    fake_app.shutdown.assert_not_awaited()


async def test_unknown_command_handler_replies_politely() -> None:
    """Unknown slash commands receive a minimalist hint to use /start."""
    replies: list[str] = []

    async def fake_reply(text: str, **kwargs: Any) -> None:
        replies.append(text)

    update = SimpleNamespace(effective_message=SimpleNamespace(reply_text=fake_reply))
    context = SimpleNamespace()

    await unknown_command_handler(update, context)  # type: ignore[arg-type]
    assert len(replies) == 1
    assert "/start" in replies[0]


async def test_global_error_handler_handles_telegram_db_and_callbacks() -> None:
    """global_error_handler handles Conflict, NetworkError, DB errors, and callback spinners."""
    # Polling Conflict (update=None)
    await global_error_handler(None, SimpleNamespace(error=Conflict("terminated")))  # type: ignore[arg-type]

    # NetworkError (update=None)
    await global_error_handler(None, SimpleNamespace(error=NetworkError("timeout")))  # type: ignore[arg-type]

    # Callback query error answers spinner instead of leaving it hanging
    answers: list[str] = []

    async def fake_answer(text: str | None = None, show_alert: bool = False) -> None:
        answers.append(text or "")

    from telegram import Update

    cb_update = MagicMock(spec=Update)
    cb_update.effective_user = SimpleNamespace(id=12345)
    cb_update.callback_query = SimpleNamespace(answer=fake_answer)
    cb_update.effective_message = None

    await global_error_handler(
        cb_update,
        SimpleNamespace(error=DatabaseOperationError("db down")),  # type: ignore[arg-type]
    )
    assert len(answers) == 1
    assert "ошибка" in answers[0].lower()

    # Message update error sends fallback message
    msg_replies: list[str] = []

    async def fake_reply(text: str) -> None:
        msg_replies.append(text)

    msg_update = MagicMock(spec=Update)
    msg_update.effective_user = SimpleNamespace(id=12345)
    msg_update.callback_query = None
    msg_update.effective_message = SimpleNamespace(reply_text=fake_reply)

    await global_error_handler(
        msg_update,
        SimpleNamespace(error=RuntimeError("boom")),  # type: ignore[arg-type]
    )
    assert len(msg_replies) == 1


def test_create_application_registers_unknown_command_handler() -> None:
    """Application registers /start, /help, and unknown command MessageHandler."""
    settings = Settings(
        bot_token="123456:FakeBotTokenForLifecycle",  # type: ignore[arg-type]
        firebase_project_id="astralio-test",
        firebase_client_email="firebase-adminsdk-test@astralio-test.iam.gserviceaccount.com",
        firebase_private_key=(
            "-----BEGIN PRIVATE KEY-----\\n"  # type: ignore[arg-type]
            "YXN0cmFsaW8tdGVzdC1wbGFjZWhvbGRlcg==\\n"
            "-----END PRIVATE KEY-----"
        ),
    )
    app = create_application(settings=settings, user_service=MagicMock())
    # Group 0: 2 CommandHandlers + 1 MessageHandler(COMMAND) + 7 CallbackQueryHandlers = 10
    assert len(app.handlers[0]) == 10
