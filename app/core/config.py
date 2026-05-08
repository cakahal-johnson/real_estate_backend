# app/core/config.py
from __future__ import annotations
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # === App Environment ===
    # ENV: str = "production"  # 👈 ADD THIS
    ENV: str = "development"  # ✅ Default to dev

    # === Frontend URL === ✅ REQUIRED
    FRONTEND_URL: str = "http://127.0.0.1:3000"

    # === Database & JWT Auth ===
    DATABASE_URL: str = "sqlite:///./real_estate.db"
    SECRET_KEY: str = "supersecretkey"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    REFRESH_TOKEN_SECRET_KEY: str

    PAYSTACK_SECRET_KEY: str
    ADMIN_EMAIL: Optional[str] = None

    # === Email Settings ===
    MAIL_USERNAME: str = "youremail@gmail.com"
    MAIL_PASSWORD: str = "yourapppassword"
    MAIL_FROM: str = "youremail@gmail.com"
    MAIL_PORT: int = 587
    MAIL_SERVER: str = "smtp.gmail.com"
    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False
    USE_CREDENTIALS: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"


settings = Settings()
