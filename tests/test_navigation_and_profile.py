"""Tests for Astralio main menu, inline navigation, profile, language settings, and guards."""

from types import SimpleNamespace
from typing import Any

import pytest
from app.bot.setup import create_application
from app.config import Settings
from app.database.repositories.user_repository import UserRepository
from app.handlers.help import help_callback, help_command
from app.handlers.menu import main_menu_callback, section_callback, unknown_callback_handler
from app.handlers.profile import format_profile_text, profile_callback
from app.handlers.settings import language_menu_callback, set_language_callback
from app.handlers.start import start_handler
from app.services.user_service import UserService
from app.utils.callbacks import CallbackGuard

from tests.test_user_repository import FakeFirestoreClient


class FakeCallbackQuery:
    """Lightweight mock for telegram.CallbackQuery."""

    def __init__(self, user_id: int, data: str, username: str | None = "user_one") -> None:
        self.from_user = SimpleNamespace(
            id=user_id,
            username=username,
            first_name="Elena",
            language_code="ru",
        )
        self.data = data
        self.answers: list[dict[str, Any]] = []
        self.edits: list[dict[str, Any]] = []

    async def answer(self, text: str | None = None, show_alert: bool = False) -> None:
        self.answers.append({"text": text, "show_alert": show_alert})

    async def edit_message_text(self, text: str, **kwargs: Any) -> None:
        self.edits.append({"text": text, **kwargs})


@pytest.fixture
def fake_db() -> FakeFirestoreClient:
    return FakeFirestoreClient()


@pytest.fixture
def user_service(fake_db: FakeFirestoreClient) -> UserService:
    return UserService(UserRepository(fake_db))


@pytest.fixture
def bot_context(user_service: UserService) -> SimpleNamespace:
    return SimpleNamespace(
        bot_data={
            "user_service": user_service,
            "callback_guard": CallbackGuard(cooldown_seconds=0.35),
        }
    )


async def test_start_renders_minimalist_main_menu(
    bot_context: SimpleNamespace,
) -> None:
    """/start displays exact Astralio main menu with 6 single-row buttons."""
    replies: list[dict[str, Any]] = []

    async def fake_reply_text(text: str, **kwargs: Any) -> None:
        replies.append({"text": text, **kwargs})

    update = SimpleNamespace(
        effective_user=SimpleNamespace(
            id=10101,
            username="astral_user",
            first_name="Elena",
            language_code="ru",
        ),
        effective_message=SimpleNamespace(reply_text=fake_reply_text),
    )

    await start_handler(update, bot_context)  # type: ignore[arg-type]

    assert len(replies) == 1
    assert replies[0]["text"] == (
        "Astralio\n\n"
        "Астрология. Персональные разборы. Прогнозы.\n\n"
        "Выберите раздел."
    )
    markup = replies[0]["reply_markup"]
    button_labels = [row[0].text for row in markup.inline_keyboard]
    assert all(len(row) == 1 for row in markup.inline_keyboard)
    assert button_labels == [
        "Натальная карта",
        "Совместимость",
        "Прогнозы",
        "Профиль",
        "Premium",
        "Помощь",
    ]


@pytest.mark.parametrize(
    ("callback_data", "expected_fragment"),
    [
        ("menu:natal", "Раздел находится в разработке."),
        ("menu:compatibility", "Раздел находится в разработке."),
        ("menu:forecasts", "Раздел находится в разработке."),
        ("menu:premium", "Оплата и подключение тарифа появятся на следующих этапах."),
    ],
)
async def test_section_navigation_and_back_to_main(
    bot_context: SimpleNamespace,
    callback_data: str,
    expected_fragment: str,
) -> None:
    """Sections open with Back button and return cleanly to main menu."""
    query = FakeCallbackQuery(user_id=20202, data=callback_data)
    update = SimpleNamespace(callback_query=query)

    await section_callback(update, bot_context)  # type: ignore[arg-type]
    assert len(query.answers) == 1
    assert len(query.edits) == 1
    assert expected_fragment in query.edits[0]["text"]
    back_markup = query.edits[0]["reply_markup"]
    assert back_markup.inline_keyboard[0][0].text == "Назад"
    assert back_markup.inline_keyboard[0][0].callback_data == "nav:main"

    # Navigate back to main menu (new cooldown/different callback_data)
    back_query = FakeCallbackQuery(user_id=20202, data="nav:main")
    await main_menu_callback(SimpleNamespace(callback_query=back_query), bot_context)  # type: ignore[arg-type]
    assert len(back_query.edits) == 1
    assert back_query.edits[0]["text"].startswith("Astralio\n\n")


async def test_help_callback_and_command(bot_context: SimpleNamespace) -> None:
    """Help section works both via inline button and /help command."""
    query = FakeCallbackQuery(user_id=30303, data="menu:help")
    await help_callback(SimpleNamespace(callback_query=query), bot_context)  # type: ignore[arg-type]
    assert "Astralio — сервис персональной астрологии" in query.edits[0]["text"]
    assert query.edits[0]["reply_markup"].inline_keyboard[0][0].callback_data == "nav:main"

    replies: list[str] = []

    async def fake_reply(text: str, **kwargs: Any) -> None:
        replies.append(text)

    cmd_update = SimpleNamespace(effective_message=SimpleNamespace(reply_text=fake_reply))
    await help_command(cmd_update, bot_context)  # type: ignore[arg-type]
    assert len(replies) == 1
    assert "Astralio" in replies[0]


async def test_profile_loads_from_firestore_and_handles_missing_fields(
    user_service: UserService,
    bot_context: SimpleNamespace,
) -> None:
    """Profile displays Firestore fields accurately and uses 'Не указан' for absent fields."""
    await user_service.register_or_update_user(
        telegram_id=40404,
        username=None,
        first_name=" <Ivan> ",
        language_code=None,
    )

    query = FakeCallbackQuery(user_id=40404, data="menu:profile", username=None)
    await profile_callback(SimpleNamespace(callback_query=query), bot_context)  # type: ignore[arg-type]

    assert len(query.edits) == 1
    text = query.edits[0]["text"]
    assert "Имя: &lt;Ivan&gt;" in text
    assert "Telegram ID: <code>40404</code>" in text
    assert "Username: Не указан" in text
    assert "Язык: Русский" in text
    assert "Дата регистрации:" in text
    assert "Текущий тариф: Базовый" in text

    # Also verify formatting when Firestore has no document at all
    missing_text = format_profile_text(999111, None)
    assert "Имя: Не указан" in missing_text
    assert "Username: Не указан" in missing_text
    assert "Текущий тариф: Не указан" in missing_text


async def test_language_settings_and_no_duplicates(
    fake_db: FakeFirestoreClient,
    user_service: UserService,
    bot_context: SimpleNamespace,
) -> None:
    """Language menu updates active language and keeps planned languages honest."""
    await user_service.register_or_update_user(
        telegram_id=50505,
        username="lang_user",
        first_name="Olga",
        language_code="ru",
    )

    open_lang = FakeCallbackQuery(user_id=50505, data="settings:language")
    await language_menu_callback(SimpleNamespace(callback_query=open_lang), bot_context)  # type: ignore[arg-type]
    lang_buttons = [row[0].text for row in open_lang.edits[0]["reply_markup"].inline_keyboard]
    assert "✓ Русский" in lang_buttons
    assert "English (скоро)" in lang_buttons
    assert "Deutsch (скоро)" in lang_buttons
    assert open_lang.edits[0]["reply_markup"].inline_keyboard[-1][0].callback_data == (
        "nav:back:profile"
    )

    # Selecting planned English does not overwrite DB or crash
    tap_en = FakeCallbackQuery(user_id=50505, data="settings:lang:en")
    await set_language_callback(SimpleNamespace(callback_query=tap_en), bot_context)  # type: ignore[arg-type]
    assert "следующих обновлениях" in (tap_en.answers[0]["text"] or "")
    assert len(tap_en.edits) == 0

    # Selecting active Russian updates via UserService without duplicating user
    tap_ru = FakeCallbackQuery(user_id=50505, data="settings:lang:ru")
    await set_language_callback(SimpleNamespace(callback_query=tap_ru), bot_context)  # type: ignore[arg-type]
    assert tap_ru.answers[0]["text"] == "Язык интерфейса: Русский"
    assert len(fake_db.collections["users"]) == 1


async def test_unknown_callback_and_double_tap_protection(
    bot_context: SimpleNamespace,
) -> None:
    """Unknown callbacks answer politely; rapid duplicate taps are throttled."""
    unknown_query = FakeCallbackQuery(user_id=60606, data="legacy:unknown_btn")
    await unknown_callback_handler(SimpleNamespace(callback_query=unknown_query), bot_context)  # type: ignore[arg-type]
    assert len(unknown_query.answers) == 1
    assert "Неизвестная команда меню" in (unknown_query.answers[0]["text"] or "")

    # Rapid double tap on identical callback_data triggers edit only once
    q1 = FakeCallbackQuery(user_id=60607, data="menu:natal")
    q2 = FakeCallbackQuery(user_id=60607, data="menu:natal")
    await section_callback(SimpleNamespace(callback_query=q1), bot_context)  # type: ignore[arg-type]
    await section_callback(SimpleNamespace(callback_query=q2), bot_context)  # type: ignore[arg-type]

    assert len(q1.edits) == 1
    assert len(q2.edits) == 0
    assert len(q2.answers) == 1


def test_create_application_registers_all_stage_1_2_handlers(
    user_service: UserService,
) -> None:
    """Application builds cleanly with commands, callbacks, and fallback handler."""
    settings = Settings(
        bot_token="123456:FakeBotTokenForAppSetup",  # type: ignore[arg-type]
        firebase_project_id="astralio-test",
        firebase_client_email="firebase-adminsdk-test@astralio-test.iam.gserviceaccount.com",
        firebase_private_key=(
            "-----BEGIN PRIVATE KEY-----\\n"  # type: ignore[arg-type]
            "YXN0cmFsaW8tdGVzdC1wbGFjZWhvbGRlcg==\\n"
            "-----END PRIVATE KEY-----"
        ),
    )
    app = create_application(settings=settings, user_service=user_service)

    assert app.bot_data["user_service"] is user_service
    assert isinstance(app.bot_data["callback_guard"], CallbackGuard)
    # Default group 0: 2 commands + 1 unknown command + 7 callbacks (including fallback)
    assert len(app.handlers[0]) == 10


async def test_start_end_to_end_application_dispatch_and_no_duplicates(
    fake_db: FakeFirestoreClient,
    user_service: UserService,
) -> None:
    """Real PTB Application routes /start to main menu, registers user, and avoids duplicates."""
    from datetime import UTC, datetime
    from unittest.mock import patch

    from telegram import Chat, InlineKeyboardMarkup, Message, MessageEntity, Update, User

    settings = Settings(
        bot_token="123456:FakeBotTokenForDispatch",  # type: ignore[arg-type]
        firebase_project_id="astralis-b2fcb",
        firebase_client_email="firebase-adminsdk-test@astralis-b2fcb.iam.gserviceaccount.com",
        firebase_private_key=(
            "-----BEGIN PRIVATE KEY-----\\n"  # type: ignore[arg-type]
            "YXN0cmFsaW8tdGVzdC1wbGFjZWhvbGRlcg==\\n"
            "-----END PRIVATE KEY-----"
        ),
    )
    app = create_application(settings=settings, user_service=user_service)
    sent_payloads: list[dict[str, Any]] = []

    async def fake_post(self: Any, endpoint: str, data: dict[str, Any] | None = None, **_: Any):
        if endpoint == "getMe":
            return {
                "id": 123456,
                "is_bot": True,
                "first_name": "Astralio",
                "username": "astralio_test_bot",
            }
        if endpoint == "sendMessage" and data is not None:
            sent_payloads.append(data)
            return {
                "message_id": len(sent_payloads),
                "date": int(datetime.now(UTC).timestamp()),
                "chat": {"id": data["chat_id"], "type": "private"},
                "text": data["text"],
            }
        return True

    bot_cls = type(app.bot)
    with patch.object(bot_cls, "_post", new=fake_post):
        await app.initialize()
        for idx in (1, 2):
            msg = Message(
                message_id=idx,
                date=datetime.now(UTC),
                chat=Chat(id=777001, type="private"),
                from_user=User(
                    id=777001,
                    first_name="Elena",
                    is_bot=False,
                    username="astral_user",
                    language_code="ru",
                ),
                text="/start",
                entities=[MessageEntity(type="bot_command", offset=0, length=6)],
            )
            msg.set_bot(app.bot)
            await app.process_update(Update(update_id=idx, message=msg))
        await app.shutdown()

    assert len(sent_payloads) == 2
    expected_text = (
        "Astralio\n\n"
        "Астрология. Персональные разборы. Прогнозы.\n\n"
        "Выберите раздел."
    )
    for payload in sent_payloads:
        assert payload["text"] == expected_text
        markup = payload["reply_markup"]
        assert isinstance(markup, InlineKeyboardMarkup)
        labels = [row[0].text for row in markup.inline_keyboard]
        assert labels == [
            "Натальная карта",
            "Совместимость",
            "Прогнозы",
            "Профиль",
            "Premium",
            "Помощь",
        ]

    # Repeated /start must not create duplicate users in Firestore
    assert list(fake_db.collections["users"].keys()) == ["777001"]
    assert len(fake_db.collections["users"]) == 1


async def test_start_handles_firebase_error_gracefully_and_logs_safely() -> None:
    """Firebase unavailability during /start sends friendly message without crashing."""
    from unittest.mock import MagicMock

    from google.api_core.exceptions import ServiceUnavailable
    from loguru import logger

    broken_doc = MagicMock()
    broken_doc.get.side_effect = ServiceUnavailable("Firestore temporarily unavailable")
    broken_db = MagicMock()
    broken_db.collection.return_value.document.return_value = broken_doc

    failing_service = UserService(UserRepository(broken_db))
    context = SimpleNamespace(bot_data={"user_service": failing_service})

    replies: list[str] = []

    async def fake_reply_text(text: str, **kwargs: Any) -> None:
        replies.append(text)

    update = SimpleNamespace(
        effective_user=SimpleNamespace(
            id=90909,
            username="fail_user",
            first_name="Ivan",
            language_code="ru",
        ),
        effective_message=SimpleNamespace(reply_text=fake_reply_text),
    )

    log_messages: list[str] = []
    sink_id = logger.add(lambda msg: log_messages.append(str(msg)), level="ERROR")
    try:
        await start_handler(update, context)  # type: ignore[arg-type]
    finally:
        logger.remove(sink_id)

    assert len(replies) == 1
    assert "Временная ошибка сервиса" in replies[0]
    assert any(
        "DatabaseOperationError" in entry and "ServiceUnavailable" in entry
        for entry in log_messages
    )


async def test_start_and_callbacks_handle_missing_user_service_without_key_error() -> None:
    """Missing UserService in context.bot_data never raises KeyError."""
    empty_context = SimpleNamespace(bot_data={})
    replies: list[str] = []

    async def fake_reply_text(text: str, **kwargs: Any) -> None:
        replies.append(text)

    update = SimpleNamespace(
        effective_user=SimpleNamespace(
            id=80808,
            username="no_service_user",
            first_name="Maria",
            language_code="ru",
        ),
        effective_message=SimpleNamespace(reply_text=fake_reply_text),
    )

    await start_handler(update, empty_context)  # type: ignore[arg-type]
    assert len(replies) == 1
    assert "недоступен" in replies[0].lower()

    # Verify callbacks also answer cleanly without KeyError
    profile_query = FakeCallbackQuery(user_id=80808, data="menu:profile")
    await profile_callback(SimpleNamespace(callback_query=profile_query), empty_context)  # type: ignore[arg-type]
    assert len(profile_query.answers) == 1
    assert len(profile_query.edits) == 1
    assert "недоступен" in profile_query.edits[0]["text"].lower()

    lang_query = FakeCallbackQuery(user_id=80808, data="settings:lang:ru")
    await set_language_callback(SimpleNamespace(callback_query=lang_query), empty_context)  # type: ignore[arg-type]
    assert len(lang_query.answers) == 1
    assert "недоступен" in (lang_query.answers[0]["text"] or "").lower()
