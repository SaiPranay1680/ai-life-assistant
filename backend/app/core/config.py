from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://ai_app:1627@localhost:5432/ai_life_assistant"
    frontend_url: str = "http://localhost:3000"
    jwt_secret: str = "dev-only-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    storage_backend: str = "local"
    upload_dir: str = str(BACKEND_DIR / "uploads")
    quarantine_dir: str = str(BACKEND_DIR / "quarantine")
    quarantine_ttl_seconds: int = 3600
    max_upload_bytes: int = 20 * 1024 * 1024
    max_image_upload_bytes: int = 10 * 1024 * 1024
    max_pdf_pages: int = 30
    max_workspace_documents: int = 50
    max_workspace_bytes: int = 500 * 1024 * 1024
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"
    aws_region: str = "ap-south-1"
    aws_s3_quarantine_bucket: str = ""
    aws_s3_permanent_bucket: str = ""
    aws_s3_quarantine_prefix: str = ""
    aws_s3_permanent_prefix: str = ""
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    clamav_host: str = "127.0.0.1"
    clamav_port: int = 3310
    clamav_required: bool = False
    clamav_timeout_seconds: int = 30
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_from_name: str = "AI Life Assistant"
    smtp_use_tls: bool = True
    otp_expiry_minutes: int = 10
    otp_max_attempts: int = 5
    otp_resend_cooldown_seconds: int = 60
    otp_request_limit: int = 5
    otp_request_window_seconds: int = 3600
    otp_verify_limit: int = 10
    otp_verify_window_seconds: int = 900
    password_reset_token_minutes: int = 10

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
