"""Centralized Firebase Admin SDK initialization and Cloud Firestore access."""

from __future__ import annotations

import firebase_admin
from firebase_admin import credentials, firestore
from firebase_admin.exceptions import FirebaseError
from google.api_core.exceptions import GoogleAPIError
from google.auth.exceptions import DefaultCredentialsError
from google.cloud.firestore_v1 import Client as FirestoreClient
from loguru import logger

from app.config import Settings
from app.utils.exceptions import DatabaseConnectionError


class FirebaseManager:
    """Singleton-style manager for Firebase Admin App and Firestore Native client."""

    def __init__(self) -> None:
        self._app: firebase_admin.App | None = None
        self._db: FirestoreClient | None = None

    @property
    def is_initialized(self) -> bool:
        """Return True if Firestore client is initialized and ready."""
        return self._db is not None

    def initialize(self, settings: Settings) -> FirestoreClient:
        """Initialize Firebase Admin SDK safely with duplicate-app protection."""
        if self._db is not None:
            return self._db

        try:
            app = self._get_or_create_app(settings)
            db_id = settings.effective_database_id

            if db_id is not None:
                client = firestore.client(app=app, database_id=db_id)
            else:
                client = firestore.client(app=app)

            self._app = app
            self._db = client
            logger.info(
                "Firebase Firestore initialized (project_id={}, database_id={}).",
                settings.firebase_project_id,
                db_id or "(default)",
            )
            return client
        except DatabaseConnectionError:
            raise
        except (FirebaseError, GoogleAPIError, DefaultCredentialsError, ValueError, OSError) as exc:
            logger.error(
                "Failed to initialize Firebase Firestore for project_id={}: {}",
                settings.firebase_project_id,
                type(exc).__name__,
            )
            raise DatabaseConnectionError(
                "Не удалось подключиться к Firebase Cloud Firestore. "
                "Проверьте FIREBASE_PROJECT_ID, FIREBASE_CREDENTIALS_PATH и права доступа."
            ) from exc

    def _get_or_create_app(self, settings: Settings) -> firebase_admin.App:
        """Return existing default Firebase App or initialize a new one."""
        try:
            existing_app = firebase_admin.get_app()
            existing_project = existing_app.project_id
            if existing_project and existing_project != settings.firebase_project_id:
                raise DatabaseConnectionError(
                    "Инициализированный Firebase App использует другой project_id."
                )
            logger.debug("Reusing already initialized Firebase Admin App.")
            return existing_app
        except ValueError:
            pass

        cred = self._build_credentials(settings)
        options = {"projectId": settings.firebase_project_id}
        return firebase_admin.initialize_app(credential=cred, options=options)

    def _build_credentials(self, settings: Settings) -> credentials.Base:
        """Load service account certificate if path is given, else Application Default."""
        creds_path = settings.credentials_file
        if creds_path is None:
            logger.debug("Using Firebase Application Default Credentials (ADC).")
            return credentials.ApplicationDefault()

        if not creds_path.exists() or not creds_path.is_file():
            raise DatabaseConnectionError(
                "Указанный файл учётных данных Firebase (FIREBASE_CREDENTIALS_PATH) "
                "не найден или недоступен."
            )

        logger.debug("Loading Firebase service account credentials from configured file.")
        return credentials.Certificate(str(creds_path))

    def get_client(self) -> FirestoreClient:
        """Return initialized Firestore client or raise DatabaseConnectionError."""
        if self._db is None:
            raise DatabaseConnectionError(
                "Firestore не инициализирован. Вызовите init_firebase() перед работой с БД."
            )
        return self._db

    def close(self) -> None:
        """Release Firestore client resources and clean up app state on shutdown."""
        if self._db is not None:
            close_fn = getattr(self._db, "close", None)
            if callable(close_fn):
                try:
                    close_fn()
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Error closing Firestore client: {}", type(exc).__name__)
            self._db = None

        if self._app is not None:
            try:
                firebase_admin.delete_app(self._app)
            except ValueError:
                pass
            self._app = None
        logger.info("Firebase resources released.")


_firebase_manager = FirebaseManager()


def init_firebase(settings: Settings) -> FirestoreClient:
    """Initialize global FirebaseManager and return Firestore client."""
    return _firebase_manager.initialize(settings)


def get_firestore_client() -> FirestoreClient:
    """Get centralized Firestore client instance."""
    return _firebase_manager.get_client()


def close_firebase() -> None:
    """Close centralized Firestore client and delete Firebase App."""
    _firebase_manager.close()
