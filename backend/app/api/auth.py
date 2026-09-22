import os
import secrets
from datetime import timedelta

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import delete, select

from app.auth.security import (
    DB,
    AuthSession,
    CurrentUser,
    digest,
    dummy_hash,
    hasher,
    limit_login,
    verify_password,
)
from app.core.config import settings
from app.db.base import utcnow
from app.models import LoginSession, User

router = APIRouter(prefix="/auth", tags=["Authentication"])


class Credentials(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class PasswordChange(BaseModel):
    current_password: str = Field(max_length=256)
    new_password: str = Field(min_length=12, max_length=256)


@router.post("/login")
def login(body: Credentials, request: Request, response: Response, db: DB) -> dict[str, str]:
    limit_login(db, request.client.host if request.client else "unknown")
    user = db.scalar(select(User).where(User.username == body.username.strip().lower()))
    valid = verify_password(body.password, user.password_hash if user else dummy_hash)
    if not user or not valid or not user.is_active:
        raise HTTPException(401, "Usuario o contraseña incorrectos")
    if hasher.check_needs_rehash(user.password_hash):
        user.password_hash = hasher.hash(body.password)
    old = request.cookies.get("stockeasy_session")
    if old:
        db.execute(delete(LoginSession).where(LoginSession.token_hash == digest(old)))
    db.execute(delete(LoginSession).where(LoginSession.expires_at < utcnow()))
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    db.add(
        LoginSession(
            token_hash=digest(token),
            user_id=user.id,
            csrf_token=csrf,
            expires_at=utcnow() + timedelta(hours=settings.session_hours),
        )
    )
    db.commit()
    response.set_cookie(
        "stockeasy_session",
        token,
        httponly=True,
        secure=settings.cookie_secure or bool(os.getenv("VERCEL")),
        samesite="strict",
        max_age=settings.session_hours * 3600,
        path="/",
    )
    return {"id": user.id, "username": user.username, "csrf_token": csrf}


@router.get("/me")
def me(user: CurrentUser, session: AuthSession) -> dict[str, str]:
    return {"id": user.id, "username": user.username, "csrf_token": session.csrf_token}


@router.post("/logout")
def logout(session: AuthSession, db: DB, response: Response) -> dict[str, bool]:
    db.delete(session)
    db.commit()
    response.delete_cookie("stockeasy_session", path="/")
    return {"ok": True}


@router.post("/logout-and-shutdown")
def logout_and_shutdown(
    request: Request,
    background_tasks: BackgroundTasks,
    session: AuthSession,
    db: DB,
    response: Response,
) -> dict[str, bool]:
    """End the session and stop a server owned by the desktop launcher."""
    db.delete(session)
    db.commit()
    response.delete_cookie("stockeasy_session", path="/")
    shutdown_callback = request.app.state.shutdown_callback
    if shutdown_callback is not None:
        # Background tasks run after the response has been sent, so the browser
        # can complete logout before the local server exits.
        background_tasks.add_task(shutdown_callback)
    return {"ok": True, "shutdown": shutdown_callback is not None}


@router.post("/password")
def change_password(
    body: PasswordChange, user: CurrentUser, db: DB, response: Response
) -> dict[str, bool]:
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(400, "Contraseña actual incorrecta")
    user.password_hash = hasher.hash(body.new_password)
    db.execute(delete(LoginSession).where(LoginSession.user_id == user.id))
    db.commit()
    response.delete_cookie("stockeasy_session", path="/")
    return {"ok": True}
