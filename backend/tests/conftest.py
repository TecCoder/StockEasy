import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.auth.security import hasher
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models import User


@pytest.fixture
def db(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False}
    )

    @event.listens_for(engine, "connect")
    def pragmas(conn, _):
        conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        session.add(User(username="alice", password_hash=hasher.hash("a secure test password")))
        session.add(User(username="bob", password_hash=hasher.hash("another secure password")))
        session.commit()
        yield session
    engine.dispose()


@pytest.fixture
def client(db):
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as client:
        yield client


@pytest.fixture
def auth(client):
    response = client.post(
        "/api/auth/login", json={"username": "alice", "password": "a secure test password"}
    )
    client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
    return client
