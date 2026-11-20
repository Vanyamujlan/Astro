"""Business logic for user registration, profile retrieval, and settings."""

from datetime import UTC, datetime
from typing import Any

from loguru import logger

from app.database.models import UserModel
from app.database.repositories.user_repository import UserRepository
from app.utils.exceptions import UserAlreadyExistsError
from app.utils.sanitizers import mask_telegram_id
from app.utils.texts import DEFAULT_LANGUAGE, LANGUAGES


class UserService:
    """Coordinates user profile lifecycle between Telegram handlers and UserRepository."""

    def __init__(self, user_repository: UserRepository) -> None:
        self._repository = user_repository

    async def register_or_update_user(
        self,
        telegram_id: int,
        username: str | None,
        first_name: str,
        language_code: str | None = None,
    ) -> tuple[UserModel, bool]:
        """Register a new user or sync changed Telegram profile fields.

        Returns:
            Tuple of `(user_model, is_new_user)`.
        """
        normalized_first_name = (first_name or "User").strip() or "User"
        existing = await self._repository.get_user_by_telegram_id(telegram_id)

        if existing is None:
            try:
                created = await self._repository.create_user(
                    telegram_id=telegram_id,
                    username=username,
                    first_name=normalized_first_name,
                    language_code=language_code,
                    interface_language=DEFAULT_LANGUAGE,
                    onboarding_completed=True,
                )
                return created, True
            except UserAlreadyExistsError:
                logger.debug(
                    "Concurrent registration detected for user={}; falling back to update.",
                    mask_telegram_id(telegram_id),
                )
                existing = await self._repository.get_user_by_telegram_id(telegram_id)
                if existing is None:
                    raise

        updated = await self._sync_profile_fields(
            existing=existing,
            username=username,
            first_name=normalized_first_name,
            language_code=language_code,
        )
        return updated, False

    async def get_user_profile(self, telegram_id: int) -> UserModel | None:
        """Load user profile from Firestore without modifying unrelated fields."""
        return await self._repository.get_user_by_telegram_id(telegram_id)

    async def change_interface_language(self, telegram_id: int, language_code: str) -> UserModel:
        """Change user interface language if the target language is active."""
        meta = LANGUAGES.get(language_code)
        if meta is None or not meta.enabled:
            raise ValueError(f"Language '{language_code}' is not active.")

        return await self._repository.update_user(
            telegram_id,
            interface_language=language_code,
            last_activity=datetime.now(UTC),
        )

    async def _sync_profile_fields(
        self,
        existing: UserModel,
        username: str | None,
        first_name: str,
        language_code: str | None,
    ) -> UserModel:
        changes: dict[str, Any] = {}
        if existing.username != username:
            changes["username"] = username
        if existing.first_name != first_name:
            changes["first_name"] = first_name
        if existing.language_code != language_code:
            changes["language_code"] = language_code
        if not existing.onboarding_completed:
            changes["onboarding_completed"] = True

        # Only write to Firestore when profile data changed or last_activity is missing.
        if existing.last_activity is None:
            changes["last_activity"] = datetime.now(UTC)
        elif changes:
            changes["last_activity"] = datetime.now(UTC)

        if not changes:
            return existing

        return await self._repository.update_user(existing.telegram_id, **changes)
