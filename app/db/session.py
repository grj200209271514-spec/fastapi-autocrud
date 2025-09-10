# app/db/session.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# 1. 从我们的新配置文件中导入 settings
from app.core.config import settings

# 2. 使用 settings.DATABASE_URL 来创建 engine
engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    """FastAPI 依赖项，用于获取数据库会话。"""
    async with async_session() as session:
        yield session