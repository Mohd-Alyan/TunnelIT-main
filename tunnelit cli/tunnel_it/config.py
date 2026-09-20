import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

USER_CONFIG_PATH = Path.home() / ".tunnelit"
env_file_path = USER_CONFIG_PATH / "config.env"

class Settings(BaseSettings):
    RELAY_URL: str = "wss://tunnelit-main.onrender.com/ws"
    REQUEST_TIMEOUT: int = 30
    RECONNECT_ENABLED: bool = True
    RECONNECT_DELAY: int = 5
    LOG_LEVEL: str = "INFO"
    MAX_RESPONSE_SIZE: int = 5242880  # 5MB
    WAKEUP_TIMEOUT: int = 90
    WAKEUP_INTERVAL: int = 3
    DASHBOARD_ENABLED: bool = True
    DASHBOARD_HOST: str = "127.0.0.1"
    DASHBOARD_PORT: int = 0  # 0 = auto-pick free port

    model_config = SettingsConfigDict(env_file=str(env_file_path), env_file_encoding="utf-8", extra="ignore")

settings = Settings()