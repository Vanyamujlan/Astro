"""Database package exporting Firebase manager and collection schemas."""

from app.database.firebase import (
    FirebaseManager,
    close_firebase,
    get_firestore_client,
    init_firebase,
)
from app.database.models import PLANNED_COLLECTIONS, UserModel

__all__ = [
    "FirebaseManager",
    "PLANNED_COLLECTIONS",
    "UserModel",
    "close_firebase",
    "get_firestore_client",
    "init_firebase",
]
