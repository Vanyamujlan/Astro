"""Helpers for masking secrets and sensitive user data in logs."""

import re

_BOT_TOKEN_PATTERN = re.compile(r"(?:\bbot|\b)\d{6,12}:[A-Za-z0-9_-]{20,}")
_BEARER_PATTERN = re.compile(r"(Bearer\s+)[A-Za-z0-9._\-+/=]+", re.IGNORECASE)
_PRIVATE_KEY_PATTERN = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"
)


def sanitize_secrets(text: str) -> str:
    """Redact common secret formats (bot tokens, bearer tokens, private keys) from text."""
    if not text:
        return text
    masked = _BOT_TOKEN_PATTERN.sub("[REDACTED_BOT_TOKEN]", text)
    masked = _BEARER_PATTERN.sub(r"\1[REDACTED_TOKEN]", masked)
    masked = _PRIVATE_KEY_PATTERN.sub("[REDACTED_PRIVATE_KEY]", masked)
    return masked


def mask_telegram_id(telegram_id: int) -> str:
    """Return a partially masked Telegram ID for safe diagnostic logging."""
    raw = str(telegram_id)
    if len(raw) <= 4:
        return "***" + raw[-1:]
    return f"{raw[:2]}***{raw[-2:]}"
