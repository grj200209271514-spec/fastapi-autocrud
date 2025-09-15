from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from typing import AsyncGenerator # (关键修复) 导入 AsyncGenerator

# 调用 get_database_url() 方法来获取连接字符串
engine = create_async_engine(settings.get_database_url(), pool_pre_ping=True)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    一个异步生成器，用于提供数据库会话的依赖注入。
    """
    async with SessionLocal() as session:
        yield session