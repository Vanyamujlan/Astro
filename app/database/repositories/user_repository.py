"""Async repository for the Firestore `users` collection."""

import asyncio
from datetime import UTC, datetime
from typing import Any

from firebase_admin.exceptions import FirebaseError
from google.api_core.exceptions import AlreadyExists, GoogleAPIError, NotFound
from loguru import logger

from app.database.models import UserModel, default_subscription_payload
from app.utils.exceptions import (
    DatabaseOperationError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from app.utils.sanitizers import mask_telegram_id

USERS_COLLECTION = "users"
_UPDATABLE_FIELDS = frozenset(
    {
        "username",
        "first_name",
        "language_code",
        "interface_language",
        "last_activity",
        "onboarding_completed",
        "subscription",
        "birth_data",
    }
)


class UserRepository:
    """Provides non-blocking async CRUD operations for `users` in Cloud Firestore.

    Firebase Admin SDK Firestore methods are synchronous; all blocking calls are
    dispatched to a worker thread via `asyncio.to_thread` to keep the bot event loop responsive.
    """

    def __init__(self, db: Any) -> None:
        self._db = db

    def _doc_ref(self, telegram_id: int) -> Any:
        return self._db.collection(USERS_COLLECTION).document(str(telegram_id))

    async def user_exists(self, telegram_id: int) -> bool:
        """Check whether a user document exists for the given Telegram ID."""
        try:
            snapshot = await asyncio.to_thread(self._get_snapshot_sync, telegram_id)
            return bool(snapshot.exists)
        except (FirebaseError, GoogleAPIError) as exc:
            logger.error(
                "Firestore user_exists failed for user={}: {}",
                mask_telegram_id(telegram_id),
                type(exc).__name__,
            )
            raise DatabaseOperationError("Ошибка проверки пользователя в базе данных.") from exc

    async def get_user_by_telegram_id(self, telegram_id: int) -> UserModel | None:
        """Fetch a user by Telegram ID, returning None if not found."""
        try:
            snapshot = await asyncio.to_thread(self._get_snapshot_sync, telegram_id)
            if not snapshot.exists:
                return None
            data = snapshot.to_dict() or {}
            return UserModel.model_validate(data)
        except (FirebaseError, GoogleAPIError) as exc:
            logger.error(
                "Firestore get_user failed for user={}: {}",
                mask_telegram_id(telegram_id),
                type(exc).__name__,
            )
            raise DatabaseOperationError("Ошибка чтения профиля пользователя из базы.") from exc

    async def create_user(
        self,
        telegram_id: int,
        username: str | None,
        first_name: str,
        language_code: str | None = None,
        interface_language: str = "ru",
        onboarding_completed: bool = False,
    ) -> UserModel:
        """Atomically create a new user document; fails if profile already exists."""
        now = datetime.now(UTC)
        user = UserModel(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            language_code=language_code,
            interface_language=interface_language,
            created_at=now,
            updated_at=now,
            last_activity=now,
            onboarding_completed=onboarding_completed,
            subscription=default_subscription_payload(),
            birth_data=None,
        )
        payload = user.to_firestore_dict()

        try:
            await asyncio.to_thread(self._create_doc_sync, telegram_id, payload)
            logger.info(
                "Created Firestore user profile for user={}.",
                mask_telegram_id(telegram_id),
            )
            return user
        except AlreadyExists as exc:
            logger.warning(
                "Duplicate user creation prevented for user={}.",
                mask_telegram_id(telegram_id),
            )
            raise UserAlreadyExistsError(
                f"Пользователь {mask_telegram_id(telegram_id)} уже существует."
            ) from exc
        except (FirebaseError, GoogleAPIError) as exc:
            logger.error(
                "Firestore create_user failed for user={}: {}",
                mask_telegram_id(telegram_id),
                type(exc).__name__,
            )
            raise DatabaseOperationError("Ошибка создания профиля пользователя в базе.") from exc

    async def update_user(self, telegram_id: int, /, **fields: Any) -> UserModel:
        """Safely update allowed fields on an existing user document."""
        invalid_fields = set(fields.keys()) - _UPDATABLE_FIELDS
        if invalid_fields:
            raise ValueError(f"Unsupported fields for user update: {sorted(invalid_fields)}")

        if not fields:
            existing = await self.get_user_by_telegram_id(telegram_id)
            if existing is None:
                raise UserNotFoundError(
                    f"Пользователь {mask_telegram_id(telegram_id)} не найден."
                )
            return existing

        update_payload = dict(fields)
        update_payload["updated_at"] = datetime.now(UTC)

        try:
            updated_data = await asyncio.to_thread(
                self._update_and_fetch_sync,
                telegram_id,
                update_payload,
            )
            logger.info("Updated Firestore profile for user={}.", mask_telegram_id(telegram_id))
            return UserModel.model_validate(updated_data)
        except NotFound as exc:
            raise UserNotFoundError(
                f"Пользователь {mask_telegram_id(telegram_id)} не найден."
            ) from exc
        except (FirebaseError, GoogleAPIError) as exc:
            logger.error(
                "Firestore update_user failed for user={}: {}",
                mask_telegram_id(telegram_id),
                type(exc).__name__,
            )
            raise DatabaseOperationError("Ошибка обновления профиля пользователя в базе.") from exc

    def _get_snapshot_sync(self, telegram_id: int) -> Any:
        return self._doc_ref(telegram_id).get()

    def _create_doc_sync(self, telegram_id: int, payload: dict[str, Any]) -> None:
        # DocumentReference.create() is atomic on Firestore server and rejects existing docs.
        self._doc_ref(telegram_id).create(payload)

    def _update_and_fetch_sync(
        self,
        telegram_id: int,
        update_payload: dict[str, Any],
    ) -> dict[str, Any]:
        doc_ref = self._doc_ref(telegram_id)
        doc_ref.update(update_payload)
        snapshot = doc_ref.get()
        if not snapshot.exists:
            raise NotFound(f"Document {telegram_id} not found after update.")
        return snapshot.to_dict() or {}
