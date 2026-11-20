"""Tests for application configuration and log sanitization."""

import pytest
from app.config import load_settings
from app.utils.exceptions import ConfigurationError
from app.utils.sanitizers import mask_telegram_id, sanitize_secrets

# Harmless non-key base64 stub for unit tests (decodes to ASCII test label, not a real key).
_TEST_PEM_SINGLE_LINE = (
    "-----BEGIN PRIVATE KEY-----\\n"
    "YXN0cmFsaW8tdGVzdC1wbGFjZWhvbGRlcg==\\n"
    "-----END PRIVATE KEY-----\\n"
)
_TEST_CLIENT_EMAIL = "firebase-adminsdk-test@astralio-test.iam.gserviceaccount.com"


def test_load_settings_success_and_single_line_key_normalization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Valid env vars load cleanly and convert single-line \\n keys into real PEM newlines."""
    monkeypatch.setenv("BOT_TOKEN", "123456789:FakeTestTokenValueForUnitTests")
    monkeypatch.setenv("FIREBASE_PROJECT_ID", "astralio-test")
    monkeypatch.setenv("FIREBASE_CLIENT_EMAIL", _TEST_CLIENT_EMAIL)
    monkeypatch.setenv("FIREBASE_PRIVATE_KEY", f'"{_TEST_PEM_SINGLE_LINE}"')
    monkeypatch.setenv("FIREBASE_DATABASE_ID", "(default)")
    monkeypatch.setenv("LOG_LEVEL", "debug")
    monkeypatch.setenv("ENVIRONMENT", "development")

    settings = load_settings(env_file=None)

    assert settings.bot_token.get_secret_value() == "123456789:FakeTestTokenValueForUnitTests"
    assert settings.firebase_project_id == "astralio-test"
    assert settings.firebase_client_email == _TEST_CLIENT_EMAIL
    normalized_key = settings.firebase_private_key.get_secret_value()
    assert "\\n" not in normalized_key
    assert normalized_key == (
        "-----BEGIN PRIVATE KEY-----\n"
        "YXN0cmFsaW8tdGVzdC1wbGFjZWhvbGRlcg==\n"
        "-----END PRIVATE KEY-----\n"
    )
    assert settings.effective_database_id is None
    assert settings.log_level == "DEBUG"
    assert settings.environment == "development"
    # SecretStr must not expose token or private key in repr/str
    assert "FakeTestTokenValueForUnitTests" not in repr(settings)
    assert "YXN0cmFsaW8tdGVzdC1wbGFjZWhvbGRlcg==" not in repr(settings)


def test_load_settings_custom_database_id(monkeypatch: pytest.MonkeyPatch) -> None:
    """Non-default FIREBASE_DATABASE_ID is preserved."""
    monkeypatch.setenv("BOT_TOKEN", "123456:FakeToken")
    monkeypatch.setenv("FIREBASE_PROJECT_ID", "astralio-prod")
    monkeypatch.setenv("FIREBASE_CLIENT_EMAIL", _TEST_CLIENT_EMAIL)
    monkeypatch.setenv("FIREBASE_PRIVATE_KEY", _TEST_PEM_SINGLE_LINE)
    monkeypatch.setenv("FIREBASE_DATABASE_ID", "astralio-db-eu")

    settings = load_settings(env_file=None)
    assert settings.effective_database_id == "astralio-db-eu"


def test_load_settings_missing_bot_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing BOT_TOKEN raises ConfigurationError with clear details."""
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    monkeypatch.setenv("FIREBASE_PROJECT_ID", "astralio-test")
    monkeypatch.setenv("FIREBASE_CLIENT_EMAIL", _TEST_CLIENT_EMAIL)
    monkeypatch.setenv("FIREBASE_PRIVATE_KEY", _TEST_PEM_SINGLE_LINE)

    with pytest.raises(ConfigurationError) as exc_info:
        load_settings(env_file=None)

    assert "BOT_TOKEN" in str(exc_info.value)


def test_load_settings_missing_firebase_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing required Firebase env variables raise ConfigurationError."""
    monkeypatch.setenv("BOT_TOKEN", "123456:FakeToken")

    # Missing FIREBASE_PROJECT_ID
    monkeypatch.delenv("FIREBASE_PROJECT_ID", raising=False)
    monkeypatch.setenv("FIREBASE_CLIENT_EMAIL", _TEST_CLIENT_EMAIL)
    monkeypatch.setenv("FIREBASE_PRIVATE_KEY", _TEST_PEM_SINGLE_LINE)
    with pytest.raises(ConfigurationError) as exc_project:
        load_settings(env_file=None)
    assert "FIREBASE_PROJECT_ID" in str(exc_project.value)

    # Missing FIREBASE_CLIENT_EMAIL
    monkeypatch.setenv("FIREBASE_PROJECT_ID", "astralio-test")
    monkeypatch.delenv("FIREBASE_CLIENT_EMAIL", raising=False)
    with pytest.raises(ConfigurationError) as exc_email:
        load_settings(env_file=None)
    assert "FIREBASE_CLIENT_EMAIL" in str(exc_email.value)

    # Missing FIREBASE_PRIVATE_KEY
    monkeypatch.setenv("FIREBASE_CLIENT_EMAIL", _TEST_CLIENT_EMAIL)
    monkeypatch.delenv("FIREBASE_PRIVATE_KEY", raising=False)
    with pytest.raises(ConfigurationError) as exc_key:
        load_settings(env_file=None)
    assert "FIREBASE_PRIVATE_KEY" in str(exc_key.value)


def test_load_settings_blank_values_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """Whitespace-only required secrets are rejected."""
    monkeypatch.setenv("BOT_TOKEN", "   ")
    monkeypatch.setenv("FIREBASE_PROJECT_ID", "   ")
    monkeypatch.setenv("FIREBASE_CLIENT_EMAIL", "   ")
    monkeypatch.setenv("FIREBASE_PRIVATE_KEY", "   ")

    with pytest.raises(ConfigurationError):
        load_settings(env_file=None)


def test_load_settings_invalid_client_email_and_private_key_format(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Malformed client_email or private_key is rejected without leaking input values."""
    monkeypatch.setenv("BOT_TOKEN", "123456:FakeToken")
    monkeypatch.setenv("FIREBASE_PROJECT_ID", "astralio-test")

    # Invalid email
    monkeypatch.setenv("FIREBASE_CLIENT_EMAIL", "not-an-email")
    monkeypatch.setenv("FIREBASE_PRIVATE_KEY", _TEST_PEM_SINGLE_LINE)
    with pytest.raises(ConfigurationError) as exc_email:
        load_settings(env_file=None)
    assert "FIREBASE_CLIENT_EMAIL" in str(exc_email.value)
    assert "not-an-email" not in str(exc_email.value)

    # Invalid PEM headers
    monkeypatch.setenv("FIREBASE_CLIENT_EMAIL", _TEST_CLIENT_EMAIL)
    monkeypatch.setenv("FIREBASE_PRIVATE_KEY", "SUPER_SECRET_RAW_INVALID_VALUE")
    with pytest.raises(ConfigurationError) as exc_pem:
        load_settings(env_file=None)
    assert "FIREBASE_PRIVATE_KEY" in str(exc_pem.value)
    assert "SUPER_SECRET_RAW_INVALID_VALUE" not in str(exc_pem.value)

    # Empty PEM body
    monkeypatch.setenv(
        "FIREBASE_PRIVATE_KEY",
        "-----BEGIN PRIVATE KEY-----\\n   \\n-----END PRIVATE KEY-----",
    )
    with pytest.raises(ConfigurationError):
        load_settings(env_file=None)

    # Non-base64 characters inside PEM block must not leak into error message
    monkeypatch.setenv(
        "FIREBASE_PRIVATE_KEY",
        "-----BEGIN PRIVATE KEY-----\\nSECRET_NOT_BASE64!@#\\n-----END PRIVATE KEY-----",
    )
    with pytest.raises(ConfigurationError) as exc_b64:
        load_settings(env_file=None)
    assert "SECRET_NOT_BASE64" not in str(exc_b64.value)


def test_load_settings_invalid_bot_token_format(monkeypatch: pytest.MonkeyPatch) -> None:
    """Malformed BOT_TOKEN without colon separator or containing spaces is rejected."""
    monkeypatch.setenv("FIREBASE_PROJECT_ID", "astralio-test")
    monkeypatch.setenv("FIREBASE_CLIENT_EMAIL", _TEST_CLIENT_EMAIL)
    monkeypatch.setenv("FIREBASE_PRIVATE_KEY", _TEST_PEM_SINGLE_LINE)
    monkeypatch.setenv("BOT_TOKEN", "invalid_token_without_colon")

    with pytest.raises(ConfigurationError):
        load_settings(env_file=None)

    monkeypatch.setenv("BOT_TOKEN", "123456:bad token with spaces")
    with pytest.raises(ConfigurationError):
        load_settings(env_file=None)


def test_sanitize_secrets_and_mask_telegram_id() -> None:
    """Tokens, bearer secrets, private keys, and Telegram IDs are masked before logging."""
    raw = (
        "Failed request to https://api.telegram.org/bot987654321:ABCdefGHI_jklMNOpqrsTUVwxyz1234 "
        "with Bearer secret-jwt-token and "
        "-----BEGIN PRIVATE KEY-----\\nSENSITIVE_BODY\\n-----END PRIVATE KEY----- "
        "and truncated -----BEGIN RSA PRIVATE KEY-----PARTIAL_SECRET"
    )
    cleaned = sanitize_secrets(raw)

    assert "ABCdefGHI_jklMNOpqrsTUVwxyz1234" not in cleaned
    assert "secret-jwt-token" not in cleaned
    assert "SENSITIVE_BODY" not in cleaned
    assert "PARTIAL_SECRET" not in cleaned
    assert "[REDACTED_BOT_TOKEN]" in cleaned
    assert "[REDACTED_TOKEN]" in cleaned
    assert "[REDACTED_PRIVATE_KEY]" in cleaned
    assert mask_telegram_id(123456789) == "12***89"
    assert mask_telegram_id(42) == "***2"
