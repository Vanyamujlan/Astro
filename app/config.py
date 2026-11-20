"""Application configuration powered by Pydantic Settings."""

from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.utils.exceptions import ConfigurationError

LogLevelType = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
EnvironmentType = Literal["development", "staging", "production", "test"]


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
    firebase_credentials_path: str | None = Field(
        default=None,
        description="Optional path to Firebase Admin SDK service account JSON file.",
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

    @field_validator("firebase_credentials_path", "firebase_database_id", mode="before")
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
    def credentials_file(self) -> Path | None:
        """Return resolved Path to Firebase credentials JSON if configured."""
        if not self.firebase_credentials_path:
            return None
        return Path(self.firebase_credentials_path).expanduser()

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
            msg = err.get("msg", "invalid value")
            missing_or_invalid.append(f"{loc.upper()}: {msg}")
        details = "; ".join(missing_or_invalid)
        raise ConfigurationError(
            f"Ошибка конфигурации приложения. Проверьте .env или переменные окружения ({details})."
        ) from exc
