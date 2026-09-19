import hashlib
import secrets
from datetime import UTC, timedelta
from typing import Annotated

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.base import utcnow
from app.db.session import get_db
from app.models import LoginAttempt, LoginSession, User

hasher = PasswordHasher()
dummy_hash = hasher.hash(secrets.token_urlsafe(32))
DB = Annotated[Session, Depends(get_db)]


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def verify_password(password: str, encoded: str) -> bool:
    try:
        return hasher.verify(encoded, password)
    except (VerificationError, InvalidHashError):
        return False


def require_session(request: Request, db: DB) -> LoginSession:
    token = request.cookies.get("stockeasy_session", "")
    session = db.get(LoginSession, digest(token))
    if session is None or session.expires_at.replace(tzinfo=UTC) <= utcnow():
        raise HTTPException(401, "Inicia sesión para continuar")
    user = db.get(User, session.user_id)
    if user is None or not user.is_active:
        raise HTTPException(401, "Sesión no disponible")
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        csrf = request.headers.get("X-CSRF-Token", "")
        if not secrets.compare_digest(csrf, session.csrf_token):
            raise HTTPException(403, "Token CSRF inválido")
    return session


AuthSession = Annotated[LoginSession, Depends(require_session)]


def current_user(session: AuthSession, db: DB) -> User:
    user = db.get(User, session.user_id)
    assert user is not None
    return user


CurrentUser = Annotated[User, Depends(current_user)]


def limit_login(db: Session, ip: str) -> None:
    """Persist attempts, including unknown usernames, to resist username rotation."""
    key = digest(ip)
    record = db.get(LoginAttempt, key)
    now = utcnow()
    if record is None:
        record = LoginAttempt(key=key, count=0, window_start=now)
        db.add(record)
    if record.window_start.replace(tzinfo=UTC) < now - timedelta(minutes=15):
        record.count, record.window_start = 0, now
    if record.count >= 20:
        raise HTTPException(429, "Demasiados intentos. Espera 15 minutos.")
    record.count += 1
    db.commit()
