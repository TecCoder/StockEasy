"""Local administrative commands. Passwords are read from the terminal, never arguments."""

import argparse
import getpass

from sqlalchemy import select

from app.auth.security import hasher
from app.db.session import SessionLocal
from app.models import User


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["create-user"])
    parser.add_argument("--username", required=True)
    args = parser.parse_args()
    username = args.username.strip().lower()
    if not 1 <= len(username) <= 64:
        parser.error("Username must be 1–64 characters")
    password = getpass.getpass("Password (12+ characters): ")
    if not 12 <= len(password) <= 256 or password != getpass.getpass("Repeat password: "):
        parser.error("Passwords must match and contain 12–256 characters")
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.username == username)):
            parser.error("Username already exists")
        db.add(User(username=username, password_hash=hasher.hash(password)))
        db.commit()
    print("User created. Start StockEasy and log in.")


if __name__ == "__main__":
    main()
