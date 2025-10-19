# app/core/config.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./realestate.db"
    SECRET_KEY: str = "supersecretkey"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    class Config:
        env_file = ".env"


settings = Settings()
