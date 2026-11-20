"""Tests for application configuration and log sanitization."""

import pytest
from app.config import load_settings
from app.utils.exceptions import ConfigurationError
from app.utils.sanitizers import mask_telegram_id, sanitize_secrets


def test_load_settings_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Valid environment variables load cleanly into typed Settings."""
    monkeypatch.setenv("BOT_TOKEN", "123456789:FakeTestTokenValueForUnitTests")
    monkeypatch.setenv("FIREBASE_PROJECT_ID", "astro-test-project")
    monkeypatch.setenv("FIREBASE_CREDENTIALS_PATH", "")
    monkeypatch.setenv("FIREBASE_DATABASE_ID", "(default)")
    monkeypatch.setenv("LOG_LEVEL", "debug")
    monkeypatch.setenv("ENVIRONMENT", "development")

    settings = load_settings(env_file=None)

    assert settings.bot_token.get_secret_value() == "123456789:FakeTestTokenValueForUnitTests"
    assert settings.firebase_project_id == "astro-test-project"
    assert settings.credentials_file is None
    assert settings.effective_database_id is None
    assert settings.log_level == "DEBUG"
    assert settings.environment == "development"
    # SecretStr must not expose token in repr/str
    assert "FakeTestTokenValueForUnitTests" not in repr(settings)


def test_load_settings_custom_database_id(monkeypatch: pytest.MonkeyPatch) -> None:
    """Non-default FIREBASE_DATABASE_ID is preserved."""
    monkeypatch.setenv("BOT_TOKEN", "123456:FakeToken")
    monkeypatch.setenv("FIREBASE_PROJECT_ID", "astro-prod")
    monkeypatch.setenv("FIREBASE_DATABASE_ID", "astro-db-eu")

    settings = load_settings(env_file=None)
    assert settings.effective_database_id == "astro-db-eu"


def test_load_settings_missing_bot_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing BOT_TOKEN raises ConfigurationError with clear details."""
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    monkeypatch.setenv("FIREBASE_PROJECT_ID", "astro-test-project")

    with pytest.raises(ConfigurationError) as exc_info:
        load_settings(env_file=None)

    assert "BOT_TOKEN" in str(exc_info.value)


def test_load_settings_missing_firebase_project_id(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing FIREBASE_PROJECT_ID raises ConfigurationError."""
    monkeypatch.setenv("BOT_TOKEN", "123456:FakeToken")
    monkeypatch.delenv("FIREBASE_PROJECT_ID", raising=False)

    with pytest.raises(ConfigurationError) as exc_info:
        load_settings(env_file=None)

    assert "FIREBASE_PROJECT_ID" in str(exc_info.value)


def test_load_settings_blank_values_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """Whitespace-only required secrets are rejected."""
    monkeypatch.setenv("BOT_TOKEN", "   ")
    monkeypatch.setenv("FIREBASE_PROJECT_ID", "   ")

    with pytest.raises(ConfigurationError):
        load_settings(env_file=None)


def test_load_settings_invalid_bot_token_format(monkeypatch: pytest.MonkeyPatch) -> None:
    """Malformed BOT_TOKEN without colon separator or containing spaces is rejected."""
    monkeypatch.setenv("FIREBASE_PROJECT_ID", "astralio-test")
    monkeypatch.setenv("BOT_TOKEN", "invalid_token_without_colon")

    with pytest.raises(ConfigurationError):
        load_settings(env_file=None)

    monkeypatch.setenv("BOT_TOKEN", "123456:bad token with spaces")
    with pytest.raises(ConfigurationError):
        load_settings(env_file=None)


def test_sanitize_secrets_and_mask_telegram_id() -> None:
    """Secrets and Telegram IDs are masked before hitting logs."""
    raw = (
        "Failed request to https://api.telegram.org/bot987654321:ABCdefGHI_jklMNOpqrsTUVwxyz1234 "
        "with Bearer secret-jwt-token"
    )
    cleaned = sanitize_secrets(raw)

    assert "ABCdefGHI_jklMNOpqrsTUVwxyz1234" not in cleaned
    assert "secret-jwt-token" not in cleaned
    assert "[REDACTED_BOT_TOKEN]" in cleaned
    assert "[REDACTED_TOKEN]" in cleaned
    assert mask_telegram_id(123456789) == "12***89"
    assert mask_telegram_id(42) == "***2"
