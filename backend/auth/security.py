"""Password hashing and signed session-cookie helpers."""
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Cookie, Depends, HTTPException, Response
from jose import JWTError, jwt
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User


COOKIE_NAME = "sentinel_session"
password_hasher = PasswordHash.recommended()


def jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET_KEY", "").strip()
    if len(secret) < 32:
        raise HTTPException(503, "Authentication is not configured. Set a random JWT_SECRET_KEY of at least 32 characters.")
    return secret


def make_access_token(user: User, remember: bool = False) -> tuple[str, datetime]:
    expiry = timedelta(days=30) if remember else timedelta(hours=12)
    expires = datetime.now(timezone.utc) + expiry
    now = datetime.now(timezone.utc)
    token = jwt.encode({"sub": user.id, "sv": user.session_version, "exp": expires, "iat": now}, jwt_secret(), algorithm="HS256")
    return token, expires


def set_session_cookie(response: Response, user: User, remember: bool = False) -> None:
    token, expires = make_access_token(user, remember)
    secure_default = "true" if os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME") else "false"
    response.set_cookie(COOKIE_NAME, token, httponly=True, secure=os.getenv("COOKIE_SECURE", secure_default).lower() == "true", samesite="lax", path="/api", expires=expires)


def clear_session_cookie(response: Response) -> None:
    secure_default = "true" if os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME") else "false"
    response.delete_cookie(COOKIE_NAME, path="/api", httponly=True, secure=os.getenv("COOKIE_SECURE", secure_default).lower() == "true", samesite="lax")


def user_payload(user: User) -> dict:
    return {"id": user.id, "name": user.name, "email": user.email, "created_at": user.created_at.isoformat() + "Z"}


def user_key(session: Optional[str] = Cookie(None, alias=COOKIE_NAME), db: Session = Depends(get_db)) -> str:
    if not session:
        raise HTTPException(401, "Please sign in to continue.")
    try:
        claims = jwt.decode(session, jwt_secret(), algorithms=["HS256"])
        subject = claims.get("sub")
        if not subject:
            raise JWTError("Missing subject")
    except HTTPException:
        raise
    except JWTError:
        raise HTTPException(401, "Your session has expired or is invalid. Please sign in again.")
    user = db.query(User).filter_by(id=subject).first()
    if not user or claims.get("sv") != user.session_version:
        raise HTTPException(401, "Your session is no longer valid. Please sign in again.")
    return user.id
