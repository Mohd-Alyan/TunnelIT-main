import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    RELAY_URL: str = "wss://tunnel-it.example.com/ws"
    REQUEST_TIMEOUT: int = 30
    RECONNECT_ENABLED: bool = True
    RECONNECT_DELAY: int = 5
    LOG_LEVEL: str = "INFO"
    MAX_RESPONSE_SIZE: int = 5242880  # 5MB

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
