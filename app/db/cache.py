# app/db/cache.py (新文件)

import redis.asyncio as aioredis
from redis.asyncio.connection import ConnectionPool
from app.core.config import settings
import logging

user_activity_logger = logging.getLogger("user_activity")

# 我们将创建一个全局连接池，由 lifespan 管理
redis_pool: ConnectionPool | None = None


def get_redis_url() -> str:
    """构建用于 aioredis 连接池的 URL。"""
    # redis://[:password@]host:port/db
    password = f":{settings.REDIS_PASSWORD}@" if settings.REDIS_PASSWORD else ""
    return f"redis://{password}{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"


async def init_redis_pool():
    """在应用启动时初始化 Redis 连接池"""
    global redis_pool
    if redis_pool is None:
        redis_url = get_redis_url()
        user_activity_logger.info(
            f"Initializing Redis connection pool for: redis://...:{settings.REDIS_PORT}/{settings.REDIS_DB}")
        try:
            redis_pool = aioredis.ConnectionPool.from_url(
                redis_url,
                decode_responses=True  # 关键：自动将 redis 的 bytes 解码为 str
            )
            # 测试连接
            async with aioredis.Redis(connection_pool=redis_pool) as redis:
                await redis.ping()
            user_activity_logger.info("Redis pool initialized successfully.")
        except Exception as e:
            user_activity_logger.error(f"Failed to initialize Redis pool: {e}", exc_info=True)
            redis_pool = None  # 保持 None 以便重试或失败
            raise RuntimeError(f"Failed to connect to Redis at {redis_url}") from e


async def close_redis_pool():
    """在应用关闭时关闭 Redis 连接池"""
    global redis_pool
    if redis_pool:
        user_activity_logger.info("Closing Redis connection pool...")
        await redis_pool.disconnect()
        redis_pool = None


async def get_redis():
    """
    FastAPI 依赖项：从池中获取一个单独的 Redis 连接。
    """
    if redis_pool is None:
        # 这是一个后备，以防 lifespan 由于某种原因未运行（例如在测试中）
        # 但在生产中，lifespan 应该已经设置了它
        await init_redis_pool()

    if redis_pool:  # 再次检查，因为 init 可能会失败
        async with aioredis.Redis(connection_pool=redis_pool) as redis:
            yield redis
    else:
        # 如果 Redis 真的不可用，我们可以选择让请求失败，或者（不推荐）继续而不进行缓存
        raise RuntimeError("Redis connection pool is not available.")