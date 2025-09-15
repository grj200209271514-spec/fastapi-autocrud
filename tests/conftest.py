import pytest_asyncio
from typing import AsyncGenerator
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import os

# 导入您的 FastAPI 应用实例和数据库模型基类
from app.main import app
from app.models import Base
from app.db.session import get_db

# --- 设置测试环境变量 ---
os.environ['TESTING'] = 'True'

# --- (关键 1) 使用一个独立的、异步的测试数据库 ---
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine, class_=AsyncSession
)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    一个用于测试的异步依赖重写函数。
    """
    async with TestingSessionLocal() as session:
        yield session


# --- 使用 FastAPI 的依赖重写功能 ---
app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture(scope="session", autouse=True)
async def db_engine() -> AsyncGenerator[None, None]:
    """
    一个会话级别的夹具，在所有测试开始前异步创建数据库表。
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest_asyncio.fixture(scope="function")
async def client() -> AsyncGenerator[AsyncClient, None]:
    """
    (关键 2) 提供一个纯异步的 httpx.AsyncClient 实例。
    """
    # 禁用应用的生命周期，因为我们在这里手动管理数据库
    app.lifespan = None
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac