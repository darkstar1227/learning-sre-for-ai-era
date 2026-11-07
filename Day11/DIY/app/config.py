from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """應用設定，從 .env 讀取"""

    # 應用設定
    app_name: str = "Day11 Failure Mode Analysis"
    log_level: str = "INFO"

    # 故障注入開關（用於 DIY 測試）
    chaos_enabled: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


def get_settings() -> Settings:
    return Settings()
