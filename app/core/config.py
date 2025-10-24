from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # === App Environment ===
    ENV: str = "production"  # 👈 ADD THIS

    # === Database & JWT Auth ===
    DATABASE_URL: str = "sqlite:///./real_estate.db"
    SECRET_KEY: str = "supersecretkey"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

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

settings = Settings()
