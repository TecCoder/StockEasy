from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    database_url: str = f"sqlite:///{ROOT / 'data' / 'stockeasy.db'}"
    allowed_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8080,http://127.0.0.1:8080"
    )
    cookie_secure: bool = False
    session_hours: int = 12
    alpha_vantage_api_key: str = ""
    fmp_api_key: str = ""
    coingecko_api_key: str = ""
    sec_user_agent: str = ""
    quote_ttl: int = 900
    history_ttl: int = 86400
    fundamental_ttl: int = 86400
    profile_ttl: int = 604800
    fx_ttl: int = 86400

    @property
    def origins(self) -> list[str]:
        return self.allowed_origins.split(",")


settings = Settings()
