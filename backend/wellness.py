"""Compatibility exports for earlier SentinelText imports.

New code should import database/models/auth/services/routes from their modules.
The API paths remain assembled by ``backend.routes``.
"""
from backend.auth.security import COOKIE_NAME
from backend.database import Base, SessionLocal, engine, get_db, init_db
from backend.models import EchoPreference, EchoThemeFeedback, Journal, PasswordReset, ProfileSetting, Recommendation, Relation, User
from backend.routes import router

init_db()

__all__ = [
    "Base",
    "COOKIE_NAME",
    "EchoPreference",
    "EchoThemeFeedback",
    "Journal",
    "PasswordReset",
    "ProfileSetting",
    "Recommendation",
    "Relation",
    "SessionLocal",
    "User",
    "engine",
    "get_db",
    "init_db",
    "router",
]
