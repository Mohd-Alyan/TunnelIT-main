import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    PUBLIC_BASE_URL: str = "http://localhost:8000"
    TUNNEL_ID_LENGTH: int = 8
    REQUEST_TIMEOUT: int = 30
    MAX_TUNNELS: int = 100
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

settings = Settings()
