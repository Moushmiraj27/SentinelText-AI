"""Persistent SQLAlchemy models. Existing table names remain unchanged."""
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, LargeBinary, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from backend.database import Base


class Journal(Base):
    __tablename__ = "journals"

    id = Column(Integer, primary_key=True)
    user_id = Column(String(80), index=True, nullable=False)
    transcript = Column(Text, nullable=False)
    audio = Column(LargeBinary)
    audio_type = Column(String(100))
    emotion = Column(String(40), nullable=False)
    confidence = Column(Float, nullable=False)
    sentiment = Column(String(30), nullable=False)
    topics = Column(Text, default="[]")
    phrases = Column(Text, default="[]")
    reflection = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class Relation(Base):
    __tablename__ = "relationships"

    id = Column(Integer, primary_key=True)
    user_id = Column(String(80), index=True, nullable=False)
    journal_id = Column(Integer, ForeignKey("journals.id", ondelete="CASCADE"), nullable=False)
    situation = Column(String(180), nullable=False)
    emotion = Column(String(40), nullable=False)
    activity = Column(String(120))
    status = Column(String(20), default="suggested")
    journal = relationship("Journal")


class ManualPattern(Base):
    """User-entered mapper pattern that can exist without a source journal."""
    __tablename__ = "manual_patterns"

    id = Column(Integer, primary_key=True)
    user_id = Column(String(80), index=True, nullable=False)
    journal_id = Column(Integer, ForeignKey("journals.id", ondelete="SET NULL"), nullable=True)
    situation = Column(String(180), nullable=False)
    emotion = Column(String(40), nullable=False)
    activity = Column(String(120), nullable=False)
    status = Column(String(20), default="confirmed", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    journal = relationship("Journal")


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True)
    user_id = Column(String(80), index=True, nullable=False)
    journal_id = Column(Integer, ForeignKey("journals.id", ondelete="SET NULL"))
    activity = Column(String(120), nullable=False)
    description = Column(Text, nullable=False)
    feedback = Column(String(30))
    created_at = Column(DateTime, default=datetime.utcnow)


class ProfileSetting(Base):
    __tablename__ = "profile_settings"

    user_id = Column(String(80), primary_key=True)
    recording_consent = Column(Integer, default=0, nullable=False)


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True)
    name = Column(String(120), nullable=False)
    email = Column(String(320), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    session_version = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class PasswordReset(Base):
    __tablename__ = "password_resets"

    id = Column(Integer, primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    token_hash = Column(String(64), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime)


class EchoThemeFeedback(Base):
    __tablename__ = "echo_theme_feedback"
    __table_args__ = (UniqueConstraint("user_id", "theme_key", name="uq_echo_theme_feedback_user_key"),)

    id = Column(Integer, primary_key=True)
    user_id = Column(String(36), index=True, nullable=False)
    theme_key = Column(String(64), nullable=False)
    title = Column(String(120), nullable=False)
    status = Column(String(20), nullable=False, default="suggested")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class EchoPreference(Base):
    __tablename__ = "echo_preferences"

    user_id = Column(String(36), primary_key=True)
    external_ai_consent = Column(Integer, nullable=False, default=0)
