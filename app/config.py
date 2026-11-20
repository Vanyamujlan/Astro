"""Application configuration powered by Pydantic Settings."""

import base64
import binascii
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.utils.exceptions import ConfigurationError
from app.utils.sanitizers import sanitize_secrets

LogLevelType = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
EnvironmentType = Literal["development", "staging", "production", "test"]

_PEM_MARKERS: tuple[tuple[str, str], ...] = (
    ("-----BEGIN PRIVATE KEY-----", "-----END PRIVATE KEY-----"),
    ("-----BEGIN RSA PRIVATE KEY-----", "-----END RSA PRIVATE KEY-----"),
)


def normalize_private_key(raw_key: str) -> str:
    """Normalize single-line escaped PEM newlines and outer quotes into standard PEM text."""
    cleaned = raw_key.strip()
    if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in {'"', "'"}:
        cleaned = cleaned[1:-1].strip()
    normalized = (
        cleaned.replace("\\r\\n", "\n").replace("\\n", "\n").replace("\r\n", "\n").strip()
    )
    return f"{normalized}\n" if normalized else ""


class Settings(BaseSettings):
    """Typed application settings loaded strictly from environment variables / .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    bot_token: SecretStr = Field(
        ...,
        description="Telegram Bot API token obtained from @BotFather.",
    )
    firebase_project_id: str = Field(
        ...,
        description="Google Cloud / Firebase project ID for Cloud Firestore.",
    )
    firebase_client_email: str = Field(
        ...,
        description="Firebase Service Account client_email for Admin SDK authentication.",
    )
    firebase_private_key: SecretStr = Field(
        ...,
        description="Firebase Service Account private key in PEM format (env variable only).",
    )
    firebase_database_id: str | None = Field(
        default=None,
        description="Optional Firestore database ID (None or '(default)' uses default DB).",
    )
    log_level: LogLevelType = Field(
        default="INFO",
        description="Application log verbosity.",
    )
    environment: EnvironmentType = Field(
        default="development",
        description="Execution environment name.",
    )

    @field_validator("bot_token")
    @classmethod
    def validate_bot_token(cls, value: SecretStr) -> SecretStr:
        raw = value.get_secret_value().strip()
        if not raw:
            raise ValueError("BOT_TOKEN must not be empty.")
        if ":" not in raw or any(ch.isspace() for ch in raw):
            raise ValueError("BOT_TOKEN has invalid format (expected '<bot_id>:<secret>').")
        return SecretStr(raw)

    @field_validator("firebase_project_id")
    @classmethod
    def validate_firebase_project_id(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("FIREBASE_PROJECT_ID must not be empty.")
        return cleaned

    @field_validator("firebase_client_email")
    @classmethod
    def validate_firebase_client_email(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("FIREBASE_CLIENT_EMAIL must not be empty.")
        local, sep, domain = cleaned.partition("@")
        if (
            not sep
            or not local
            or not domain
            or "." not in domain
            or any(ch.isspace() for ch in cleaned)
        ):
            raise ValueError("FIREBASE_CLIENT_EMAIL must be a valid service account email.")
        return cleaned

    @field_validator("firebase_private_key")
    @classmethod
    def validate_firebase_private_key(cls, value: SecretStr) -> SecretStr:
        normalized = normalize_private_key(value.get_secret_value()).rstrip("\n")
        if not normalized:
            raise ValueError("FIREBASE_PRIVATE_KEY must not be empty.")

        for begin_marker, end_marker in _PEM_MARKERS:
            if normalized.startswith(begin_marker) and normalized.endswith(end_marker):
                body = normalized[len(begin_marker) : -len(end_marker)].strip()
                if not body:
                    raise ValueError("FIREBASE_PRIVATE_KEY body must not be empty.")
                compact_body = "".join(body.split())
                try:
                    decoded = base64.b64decode(compact_body, validate=True)
                except (binascii.Error, ValueError) as exc:
                    raise ValueError(
                        "FIREBASE_PRIVATE_KEY contains invalid PEM base64 encoding."
                    ) from exc
                if not decoded:
                    raise ValueError("FIREBASE_PRIVATE_KEY body must not be empty.")
                return SecretStr(f"{begin_marker}\n{body}\n{end_marker}\n")

        raise ValueError(
            "FIREBASE_PRIVATE_KEY has invalid format (expected PEM PRIVATE KEY block)."
        )

    @field_validator("firebase_database_id", mode="before")
    @classmethod
    def normalize_optional_str(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None

    @field_validator("log_level", mode="before")
    @classmethod
    def normalize_log_level(cls, value: str | None) -> str:
        if not value:
            return "INFO"
        return str(value).strip().upper()

    @field_validator("environment", mode="before")
    @classmethod
    def normalize_environment(cls, value: str | None) -> str:
        if not value:
            return "development"
        return str(value).strip().lower()

    @property
    def effective_database_id(self) -> str | None:
        """Return explicit Firestore database_id, or None when using '(default)'."""
        if not self.firebase_database_id or self.firebase_database_id == "(default)":
            return None
        return self.firebase_database_id


def load_settings(env_file: str | Path | None = ".env") -> Settings:
    """Load and validate application settings, raising ConfigurationError on failure."""
    try:
        return Settings(_env_file=env_file)
    except ValidationError as exc:
        missing_or_invalid: list[str] = []
        for err in exc.errors():
            loc = ".".join(str(part) for part in err.get("loc", ()))
            msg = sanitize_secrets(str(err.get("msg", "invalid value")))
            missing_or_invalid.append(f"{loc.upper()}: {msg}")
        details = "; ".join(missing_or_invalid)
        raise ConfigurationError(
            f"Ошибка конфигурации приложения. Проверьте .env или переменные окружения ({details})."
        ) from exc
