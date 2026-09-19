from fastapi import APIRouter
from pydantic import BaseModel

from app.auth.security import DB, CurrentUser
from app.models import Preference

router = APIRouter(prefix="/settings", tags=["Settings"])


class Preferences(BaseModel):
    theme: str = "dark"
    base_currency: str = "EUR"


@router.get("")
def get_settings(user: CurrentUser, db: DB) -> dict[str, str]:
    return {
        key: row.value if (row := db.get(Preference, (user.id, key))) else default
        for key, default in {"theme": "dark", "base_currency": "EUR"}.items()
    }


@router.put("")
def put_settings(body: Preferences, user: CurrentUser, db: DB) -> dict[str, str]:
    from fastapi import HTTPException

    if body.theme not in {"dark", "light"} or body.base_currency not in {
        "EUR",
        "USD",
        "GBP",
        "JPY",
        "CHF",
    }:
        raise HTTPException(422, "Preferencias inválidas")
    for key, value in body.model_dump().items():
        db.merge(Preference(user_id=user.id, key=key, value=value))
    db.commit()
    return body.model_dump()
