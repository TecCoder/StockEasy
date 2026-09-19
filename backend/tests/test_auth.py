from sqlalchemy import select

from app.models import User


def test_login_cookie_and_password_hash(client, db):
    assert client.get("/api/auth/me").status_code == 401
    r = client.post(
        "/api/auth/login", json={"username": "alice", "password": "a secure test password"}
    )
    assert r.status_code == 200
    assert "HttpOnly" in r.headers["set-cookie"] and "SameSite=strict" in r.headers["set-cookie"]
    assert client.get("/api/auth/me").json()["username"] == "alice"
    assert db.scalar(select(User).where(User.username == "alice")).password_hash.startswith(
        "$argon2id$"
    )
    assert client.post("/api/auth/logout").status_code == 403
    client.headers["X-CSRF-Token"] = r.json()["csrf_token"]
    assert client.post("/api/auth/logout").status_code == 200
    assert client.get("/api/auth/me").status_code == 401


def test_password_change_revokes_sessions(auth):
    assert (
        auth.post(
            "/api/auth/password",
            json={"current_password": "wrong", "new_password": "new long password"},
        ).status_code
        == 400
    )
    assert (
        auth.post(
            "/api/auth/password",
            json={
                "current_password": "a secure test password",
                "new_password": "new long password",
            },
        ).status_code
        == 200
    )
    assert auth.get("/api/auth/me").status_code == 401


def test_login_errors_and_origin(client):
    assert (
        client.post("/api/auth/login", json={"username": "none", "password": "bad"}).status_code
        == 401
    )
    assert (
        client.post(
            "/api/auth/login",
            headers={"Origin": "https://evil.invalid"},
            json={"username": "alice", "password": "a secure test password"},
        ).status_code
        == 403
    )


def test_preferences_are_private(auth, client):
    assert (
        auth.put("/api/settings", json={"theme": "light", "base_currency": "USD"}).status_code
        == 200
    )
    r = client.post(
        "/api/auth/login", json={"username": "bob", "password": "another secure password"}
    )
    client.headers["X-CSRF-Token"] = r.json()["csrf_token"]
    assert client.get("/api/settings").json()["theme"] == "dark"
