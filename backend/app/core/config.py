from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://ai_app:1627@localhost:5432/ai_life_assistant"
    frontend_url: str = "http://localhost:3000"
    jwt_secret: str = "dev-only-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    upload_dir: str = str(BACKEND_DIR / "uploads")
    max_upload_bytes: int = 20 * 1024 * 1024
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"
    cors_allow_origins: str = "http://localhost:3000"

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        """Return the explicit browser origins permitted to call the API.

        Credentials must never be combined with a wildcard origin.  Keeping this
        parsing here makes local development convenient while production can set
        a comma-separated CORS_ALLOW_ORIGINS value.
        """
        origins = [origin.strip().rstrip("/") for origin in self.cors_allow_origins.split(",") if origin.strip()]
        if not origins or "*" in origins:
            raise ValueError("CORS_ALLOW_ORIGINS must contain one or more explicit origins, never '*'.")
        return origins


settings = Settings()
