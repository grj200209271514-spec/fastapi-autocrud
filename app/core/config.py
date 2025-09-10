# app/core/config.py
from pydantic_settings import BaseSettings
from typing import Optional # 确保导入 Optional

class Settings(BaseSettings):
    DATABASE_URL: str
    PROJECT_NAME: str = "FastAPI Enterprise App"

    # (新) 添加 Redis 配置
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0

    class Config:
        env_file = ".env"

settings = Settings()