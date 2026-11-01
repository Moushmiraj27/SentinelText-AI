"""Authentication and password-reset HTTP endpoints."""
import hashlib
import re
import secrets
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from backend.auth.email import send_reset_email, smtp_is_configured
from backend.auth.security import clear_session_cookie, jwt_secret, password_hasher, set_session_cookie, user_key, user_payload
from backend.database import get_db
from backend.models import PasswordReset, User
from backend.schemas import ForgotPasswordInput, LoginInput, RegisterInput, ResetPasswordInput


router = APIRouter()


def valid_password(password: str) -> bool:
    return bool(re.search(r"[A-Za-z]", password) and re.search(r"\d", password))


@router.post("/auth/register", status_code=201)
def register(payload: RegisterInput, response: Response, db: Session = Depends(get_db)):
    jwt_secret()
    if not payload.terms_accepted:
        raise HTTPException(422, "Please accept the terms and privacy notice to create an account.")
    if not valid_password(payload.password):
        raise HTTPException(422, "Choose a password with at least one letter and one number.")

    email = str(payload.email).strip().lower()
    if db.query(User).filter_by(email=email).first():
        raise HTTPException(409, "An account with this email already exists. Try signing in.")
    user = User(id=str(uuid.uuid4()), name=payload.name.strip(), email=email, password_hash=password_hasher.hash(payload.password), session_version=0)
    if len(user.name) < 2:
        raise HTTPException(422, "Enter your name.")
    db.add(user)
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(409, "An account with this email already exists. Try signing in.") from exc
    db.refresh(user)
    set_session_cookie(response, user)
    return {"user": user_payload(user)}


@router.post("/auth/login")
def login(payload: LoginInput, response: Response, db: Session = Depends(get_db)):
    jwt_secret()
    email = str(payload.email).strip().lower()
    user = db.query(User).filter_by(email=email).first()
    if not user or not password_hasher.verify(payload.password, user.password_hash):
        raise HTTPException(401, "Email or password is incorrect.")
    set_session_cookie(response, user, payload.remember)
    return {"user": user_payload(user)}


@router.get("/auth/me")
def auth_me(user_id: str = Depends(user_key), db: Session = Depends(get_db)):
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(401, "Please sign in to continue.")
    return {"user": user_payload(user)}


@router.post("/auth/logout")
def logout(response: Response, user_id: str = Depends(user_key), db: Session = Depends(get_db)):
    user = db.query(User).filter_by(id=user_id).first()
    if user:
        user.session_version += 1
        db.commit()
    clear_session_cookie(response)
    return {"logged_out": True}


@router.post("/auth/forgot-password", status_code=202)
def forgot_password(payload: ForgotPasswordInput, db: Session = Depends(get_db)):
    if not smtp_is_configured():
        raise HTTPException(503, "Password reset email is not configured. Contact the site administrator.")
    email = str(payload.email).strip().lower()
    user = db.query(User).filter_by(email=email).first()
    if user:
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        db.query(PasswordReset).filter_by(user_id=user.id, used_at=None).delete()
        db.add(PasswordReset(user_id=user.id, token_hash=token_hash, expires_at=datetime.utcnow() + timedelta(minutes=30)))
        db.commit()
        try:
            send_reset_email(user.email, raw_token)
        except Exception:
            db.query(PasswordReset).filter_by(token_hash=token_hash).delete()
            db.commit()
            # Keep this response independent of whether the address belongs to an account.
    return {"message": "If an account exists for that email, a password reset link has been sent."}


@router.post("/auth/reset-password")
def reset_password(payload: ResetPasswordInput, response: Response, db: Session = Depends(get_db)):
    if not valid_password(payload.password):
        raise HTTPException(422, "Choose a password with at least one letter and one number.")
    token_hash = hashlib.sha256(payload.token.encode()).hexdigest()
    record = db.query(PasswordReset).filter_by(token_hash=token_hash, used_at=None).first()
    invalid_link = "This reset link is invalid or expired. Request a new one."
    if not record or record.expires_at < datetime.utcnow():
        raise HTTPException(400, invalid_link)
    user = db.query(User).filter_by(id=record.user_id).first()
    if not user:
        raise HTTPException(400, invalid_link)
    user.password_hash = password_hasher.hash(payload.password)
    user.session_version += 1
    record.used_at = datetime.utcnow()
    db.commit()
    db.query(PasswordReset).filter(PasswordReset.user_id == user.id, PasswordReset.id != record.id).delete()
    db.commit()
    clear_session_cookie(response)
    return {"password_reset": True}
