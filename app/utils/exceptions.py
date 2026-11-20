"""Domain and infrastructure exceptions for Astralio."""


class AstralioError(Exception):
    """Base exception for all application-level errors."""


# Backward-compatible alias for Stage 1.1 imports
AstroError = AstralioError


class ConfigurationError(AstralioError):
    """Raised when required environment settings are missing or invalid."""


class DatabaseConnectionError(AstralioError):
    """Raised when Firebase / Firestore initialization or connection fails."""


class DatabaseOperationError(AstralioError):
    """Raised when a Firestore read or write operation fails."""


class UserAlreadyExistsError(DatabaseOperationError):
    """Raised when attempting to create a user document that already exists."""


class UserNotFoundError(DatabaseOperationError):
    """Raised when a requested user document does not exist in Firestore."""
