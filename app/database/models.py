"""Firestore data models and collection architecture specification."""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


def _utc_now() -> datetime:
    return datetime.now(UTC)


def default_subscription_payload() -> dict[str, Any]:
    """Return default free-tier subscription state stored inside user document."""
    return {
        "plan": "free",
        "status": "inactive",
        "expires_at": None,
    }


class UserModel(BaseModel):
    """Schema for documents in the Firestore `users` collection.

    Document ID is always `str(telegram_id)` so lookups are direct, unique,
    and unaffected by Telegram `@username` changes.
    """

    telegram_id: int
    username: str | None = None
    first_name: str
    language_code: str | None = None
    interface_language: str = "ru"
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)
    last_activity: datetime | None = None
    onboarding_completed: bool = False
    subscription: dict[str, Any] = Field(default_factory=default_subscription_payload)
    birth_data: dict[str, Any] | None = None

    def to_firestore_dict(self) -> dict[str, Any]:
        """Serialize model into a Firestore-compatible dictionary."""
        return self.model_dump(mode="python")


# Architectural specification of Firestore collections for Astralio.
# Only `users` is implemented in Stage 1.x; remaining collections are documented blueprints.
PLANNED_COLLECTIONS: dict[str, list[str]] = {
    "users": [
        "telegram_id",
        "username",
        "first_name",
        "language_code",
        "interface_language",
        "created_at",
        "updated_at",
        "last_activity",
        "onboarding_completed",
        "subscription",
        "birth_data",
    ],
    "payments": [
        "telegram_id",
        "amount",
        "currency",
        "status",
        "provider_charge_id",
        "created_at",
    ],
    "subscriptions": [
        "telegram_id",
        "plan",
        "status",
        "started_at",
        "expires_at",
    ],
    "ai_usage": [
        "telegram_id",
        "model",
        "request_type",
        "tokens_used",
        "created_at",
    ],
}
