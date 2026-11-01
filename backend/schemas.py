"""Validated request models shared by API route modules."""
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


MAX_AUDIO_BYTES = 20 * 1024 * 1024
MAX_AUDIO_DATA_LENGTH = ((MAX_AUDIO_BYTES + 2) // 3) * 4 + 256


class JournalInput(BaseModel):
    transcript: str = Field(min_length=2, max_length=20000)
    audio_data: Optional[str] = Field(default=None, max_length=MAX_AUDIO_DATA_LENGTH)
    audio_type: Optional[str] = Field(default=None, max_length=100)


class RelationInput(BaseModel):
    status: str = Field(pattern="^(confirmed|rejected|suggested)$")
    situation: Optional[str] = Field(default=None, max_length=180)
    emotion: Optional[str] = Field(default=None, min_length=2, max_length=40)
    activity: Optional[str] = Field(default=None, max_length=120)


class MapperPatternInput(BaseModel):
    journal_id: Optional[int] = None
    situation: str = Field(min_length=2, max_length=180)
    emotion: str = Field(min_length=2, max_length=40)
    activity: str = Field(min_length=2, max_length=120)


class FeedbackInput(BaseModel):
    feedback: str = Field(pattern="^(helpful|somewhat_helpful|not_helpful)$")


class ConsentInput(BaseModel):
    recording_consent: bool


class EchoThemeFeedbackInput(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    status: str = Field(pattern="^(confirmed|dismissed|suggested)$")


class EchoPreferenceInput(BaseModel):
    external_ai_consent: bool


class RegisterInput(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    terms_accepted: bool


class LoginInput(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    remember: bool = False


class ForgotPasswordInput(BaseModel):
    email: EmailStr


class ResetPasswordInput(BaseModel):
    token: str = Field(min_length=32, max_length=300)
    password: str = Field(min_length=10, max_length=128)
