from pydantic_settings import BaseSettings
from typing import Optional
import os  # 导入 os 模块


class Settings(BaseSettings):
    # --- 生产/开发数据库 ---
    DATABASE_URL: str
    # --- (新增) 专门用于测试的数据库 ---
    DATABASE_URL_TEST: str = "sqlite+aiosqlite:///./test.db"

    PROJECT_NAME: str = "FastAPI Enterprise App"
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0
    LOG_CLEANUP_INTERVAL_MINUTES: int = 2

    class Config:
        env_file = ".env"

    def get_database_url(self) -> str:
        """
        (新增) 根据是否处于测试环境，返回正确的数据库URL。
        """
        if os.getenv("TESTING"):
            return self.DATABASE_URL_TEST
        return self.DATABASE_URL


settings = Settings()