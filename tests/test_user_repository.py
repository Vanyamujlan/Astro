"""Tests for FirebaseManager, UserRepository, UserService, and /start handler."""

from copy import deepcopy
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from app.config import Settings
from app.database.firebase import FirebaseManager
from app.database.repositories.user_repository import USERS_COLLECTION, UserRepository
from app.handlers.start import start_handler
from app.services.user_service import UserService
from app.utils.exceptions import (
    DatabaseConnectionError,
    DatabaseOperationError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from google.api_core.exceptions import AlreadyExists, NotFound, ServiceUnavailable
from google.auth.exceptions import DefaultCredentialsError


class FakeSnapshot:
    """Minimal in-memory stand-in for Firestore DocumentSnapshot."""

    def __init__(self, doc_id: str, data: dict[str, Any] | None) -> None:
        self.id = doc_id
        self._data = deepcopy(data) if data is not None else None

    @property
    def exists(self) -> bool:
        return self._data is not None

    def to_dict(self) -> dict[str, Any] | None:
        return deepcopy(self._data) if self._data is not None else None


class FakeDocumentReference:
    """Minimal in-memory stand-in for Firestore DocumentReference."""

    def __init__(self, store: dict[str, dict[str, Any]], doc_id: str) -> None:
        self._store = store
        self._doc_id = doc_id

    def get(self) -> FakeSnapshot:
        return FakeSnapshot(self._doc_id, self._store.get(self._doc_id))

    def create(self, data: dict[str, Any]) -> None:
        if self._doc_id in self._store:
            raise AlreadyExists(f"Document {self._doc_id} already exists.")
        self._store[self._doc_id] = deepcopy(data)

    def update(self, data: dict[str, Any]) -> None:
        if self._doc_id not in self._store:
            raise NotFound(f"Document {self._doc_id} not found.")
        self._store[self._doc_id].update(deepcopy(data))


class FakeCollectionReference:
    """Minimal in-memory stand-in for Firestore CollectionReference."""

    def __init__(self, store: dict[str, dict[str, Any]]) -> None:
        self._store = store

    def document(self, doc_id: str) -> FakeDocumentReference:
        return FakeDocumentReference(self._store, doc_id)


class FakeFirestoreClient:
    """In-memory fake Firestore client for isolated async unit tests."""

    def __init__(self) -> None:
        self.collections: dict[str, dict[str, dict[str, Any]]] = {}

    def collection(self, name: str) -> FakeCollectionReference:
        store = self.collections.setdefault(name, {})
        return FakeCollectionReference(store)


@pytest.fixture
def fake_db() -> FakeFirestoreClient:
    return FakeFirestoreClient()


@pytest.fixture
def user_repo(fake_db: FakeFirestoreClient) -> UserRepository:
    return UserRepository(fake_db)


@pytest.fixture
def user_service(user_repo: UserRepository) -> UserService:
    return UserService(user_repo)


async def test_create_and_get_user(
    fake_db: FakeFirestoreClient,
    user_repo: UserRepository,
) -> None:
    """User is stored under users/{telegram_id} and retrieved cleanly."""
    created = await user_repo.create_user(
        telegram_id=100500,
        username="astro_user",
        first_name="Elena",
        language_code="ru",
    )

    assert created.telegram_id == 100500
    assert created.username == "astro_user"
    assert created.first_name == "Elena"
    assert created.subscription["plan"] == "free"
    assert created.birth_data is None
    assert "100500" in fake_db.collections[USERS_COLLECTION]

    assert await user_repo.user_exists(100500) is True
    assert await user_repo.user_exists(999999) is False

    fetched = await user_repo.get_user_by_telegram_id(100500)
    assert fetched is not None
    assert fetched.telegram_id == 100500
    assert fetched.username == "astro_user"


async def test_create_user_prevents_duplicates_and_overwrite(
    fake_db: FakeFirestoreClient,
    user_repo: UserRepository,
) -> None:
    """Duplicate create_user raises UserAlreadyExistsError and keeps original data."""
    await user_repo.create_user(
        telegram_id=777,
        username="original",
        first_name="Ivan",
        language_code="ru",
    )
    await user_repo.update_user(777, birth_data={"city": "Moscow"})

    with pytest.raises(UserAlreadyExistsError):
        await user_repo.create_user(
            telegram_id=777,
            username="attacker_overwrite",
            first_name="Fake",
            language_code="en",
        )

    preserved = await user_repo.get_user_by_telegram_id(777)
    assert preserved is not None
    assert preserved.username == "original"
    assert preserved.birth_data == {"city": "Moscow"}


async def test_update_user_and_validation(user_repo: UserRepository) -> None:
    """update_user updates allowed fields, refreshes updated_at, and validates keys."""
    created = await user_repo.create_user(
        telegram_id=555,
        username="old_name",
        first_name="Anna",
        language_code="ru",
    )

    updated = await user_repo.update_user(555, username="new_name", first_name="Anna M.")
    assert updated.username == "new_name"
    assert updated.first_name == "Anna M."
    assert updated.created_at == created.created_at
    assert updated.updated_at >= created.updated_at

    with pytest.raises(ValueError):
        await user_repo.update_user(555, telegram_id=123)

    with pytest.raises(UserNotFoundError):
        await user_repo.update_user(404040, username="ghost")


async def test_firestore_error_handling() -> None:
    """GoogleAPIError failures are wrapped in DatabaseOperationError."""
    broken_doc = MagicMock()
    broken_doc.get.side_effect = ServiceUnavailable("Firestore unavailable")
    broken_doc.create.side_effect = ServiceUnavailable("Firestore unavailable")
    broken_doc.update.side_effect = ServiceUnavailable("Firestore unavailable")

    broken_db = MagicMock()
    broken_db.collection.return_value.document.return_value = broken_doc

    repo = UserRepository(broken_db)

    with pytest.raises(DatabaseOperationError):
        await repo.user_exists(1)

    with pytest.raises(DatabaseOperationError):
        await repo.get_user_by_telegram_id(1)

    with pytest.raises(DatabaseOperationError):
        await repo.create_user(1, "u", "Name")

    with pytest.raises(DatabaseOperationError):
        await repo.update_user(1, username="u2")


async def test_firestore_auth_and_corrupted_doc_handling() -> None:
    """DefaultCredentialsError and malformed Firestore docs raise DatabaseOperationError."""
    auth_broken_doc = MagicMock()
    auth_broken_doc.get.side_effect = DefaultCredentialsError("No ADC credentials")
    auth_broken_db = MagicMock()
    auth_broken_db.collection.return_value.document.return_value = auth_broken_doc

    repo_auth = UserRepository(auth_broken_db)
    with pytest.raises(DatabaseOperationError):
        await repo_auth.get_user_by_telegram_id(10)

    bad_snapshot = FakeSnapshot("10", {"broken": "missing required fields"})
    corrupt_doc = MagicMock()
    corrupt_doc.get.return_value = bad_snapshot
    corrupt_db = MagicMock()
    corrupt_db.collection.return_value.document.return_value = corrupt_doc

    repo_corrupt = UserRepository(corrupt_db)
    with pytest.raises(DatabaseOperationError):
        await repo_corrupt.get_user_by_telegram_id(10)


async def test_user_service_register_sync_and_race_condition(
    user_repo: UserRepository,
    user_service: UserService,
) -> None:
    """UserService creates new users, syncs changed profiles, and handles races."""
    user, is_new = await user_service.register_or_update_user(
        telegram_id=4242,
        username="star_gazer",
        first_name="Maria",
        language_code="ru",
    )
    assert is_new is True
    assert user.first_name == "Maria"

    # Unchanged profile returns existing without error
    same_user, is_new_2 = await user_service.register_or_update_user(
        telegram_id=4242,
        username="star_gazer",
        first_name="Maria",
        language_code="ru",
    )
    assert is_new_2 is False
    assert same_user.updated_at == user.updated_at

    # Changed username triggers profile sync
    synced, is_new_3 = await user_service.register_or_update_user(
        telegram_id=4242,
        username="moon_walker",
        first_name="Maria",
        language_code="en",
    )
    assert is_new_3 is False
    assert synced.username == "moon_walker"
    assert synced.language_code == "en"

    # Simulate concurrent creation race condition
    with patch.object(
        user_repo,
        "get_user_by_telegram_id",
        side_effect=[None, synced],
    ), patch.object(
        user_repo,
        "create_user",
        side_effect=UserAlreadyExistsError("Already exists"),
    ):
        raced_user, raced_is_new = await user_service.register_or_update_user(
            telegram_id=4242,
            username="moon_walker",
            first_name="Maria",
            language_code="en",
        )
        assert raced_is_new is False
        assert raced_user.telegram_id == 4242


async def test_start_handler_flow(user_service: UserService) -> None:
    """/start creates user on first call, syncs on repeat, and displays main menu."""
    sent_messages: list[dict[str, Any]] = []

    async def fake_reply_text(text: str, **kwargs: Any) -> None:
        sent_messages.append({"text": text, **kwargs})

    update = SimpleNamespace(
        effective_user=SimpleNamespace(
            id=888001,
            username="leo_fan",
            first_name="<Alex>",
            language_code="ru",
        ),
        effective_message=SimpleNamespace(reply_text=fake_reply_text),
    )
    context = SimpleNamespace(bot_data={"user_service": user_service})

    await start_handler(update, context)  # type: ignore[arg-type]
    assert len(sent_messages) == 1
    assert "Astralio" in sent_messages[0]["text"]
    assert "Выберите раздел." in sent_messages[0]["text"]
    assert sent_messages[0]["reply_markup"] is not None

    profile = await user_service.get_user_profile(888001)
    assert profile is not None
    assert profile.onboarding_completed is True
    assert profile.interface_language == "ru"
    assert profile.last_activity is not None

    await start_handler(update, context)  # type: ignore[arg-type]
    assert len(sent_messages) == 2
    assert "Astralio" in sent_messages[1]["text"]


def test_firebase_manager_missing_credentials_file() -> None:
    """Missing credentials JSON raises DatabaseConnectionError clearly."""
    settings = Settings(
        bot_token="123456:TestToken",  # type: ignore[arg-type]
        firebase_project_id="astro-test",
        firebase_credentials_path="/nonexistent/path/serviceAccountKey.json",
    )
    manager = FirebaseManager()
    with pytest.raises(DatabaseConnectionError):
        manager.initialize(settings)


def test_firebase_manager_duplicate_init_guard_and_database_id() -> None:
    """FirebaseManager initializes once and passes custom database_id when set."""
    settings = Settings(
        bot_token="123456:TestToken",  # type: ignore[arg-type]
        firebase_project_id="astro-test",
        firebase_credentials_path=None,
        firebase_database_id="astro-native-db",
    )
    manager = FirebaseManager()
    fake_app = MagicMock()
    fake_client = MagicMock()

    with (
        patch("app.database.firebase.firebase_admin.get_app", side_effect=ValueError("no app")),
        patch("app.database.firebase.credentials.ApplicationDefault", return_value=MagicMock()),
        patch(
            "app.database.firebase.firebase_admin.initialize_app",
            return_value=fake_app,
        ) as mock_init_app,
        patch(
            "app.database.firebase.firestore.client",
            return_value=fake_client,
        ) as mock_fs_client,
    ):
        client_1 = manager.initialize(settings)
        client_2 = manager.initialize(settings)

        assert client_1 is fake_client
        assert client_2 is fake_client
        mock_init_app.assert_called_once()
        mock_fs_client.assert_called_once_with(app=fake_app, database_id="astro-native-db")


def test_firebase_manager_project_mismatch_and_close() -> None:
    """FirebaseManager rejects mismatched existing App project_id and cleans up on close."""
    settings = Settings(
        bot_token="123456:TestToken",  # type: ignore[arg-type]
        firebase_project_id="expected-project",
    )
    manager = FirebaseManager()
    wrong_app = MagicMock(project_id="other-project")

    with patch("app.database.firebase.firebase_admin.get_app", return_value=wrong_app):
        with pytest.raises(DatabaseConnectionError):
            manager.initialize(settings)

    # Verify close() releases client and deletes app
    good_app = MagicMock(project_id="expected-project")
    fake_client = MagicMock()
    with (
        patch("app.database.firebase.firebase_admin.get_app", return_value=good_app),
        patch("app.database.firebase.firestore.client", return_value=fake_client),
        patch("app.database.firebase.firebase_admin.delete_app") as mock_delete_app,
    ):
        manager.initialize(settings)
        assert manager.is_initialized is True
        manager.close()
        assert manager.is_initialized is False
        fake_client.close.assert_called_once()
        mock_delete_app.assert_called_once_with(good_app)
