import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

# 从项目根目录导入 logging_config。
# 注意：这个导入依赖于 run.py 脚本将项目根目录添加到了 sys.path 中。
from logging_config import LOG_DIR, LOGGERS_TO_SETUP
from app.db.cache import init_redis_pool, close_redis_pool
from app.db.session import engine
from models import Base

user_activity_logger = logging.getLogger("user_activity")


async def create_db_and_tables():
    """在应用启动时异步创建所有数据库表。"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    user_activity_logger.info("Database tables checked/created.")


async def cleanup_logs():
    """
    (优化后) 动态地从日志配置中获取所有日志文件并进行清理。
    """
    # 关键修改：不再硬编码文件名，而是从 LOGGERS_TO_SETUP 动态生成列表
    # 这确保了将来你新增任何日志文件，它都会被自动纳入清理范围
    log_files = [LOG_DIR / config["filename"] for config in LOGGERS_TO_SETUP]

    target_files_str = ", ".join(f.name for f in log_files)
    user_activity_logger.info(f"Starting scheduled log cleanup. Targets: [{target_files_str}]")

    for log_file in log_files:
        if log_file.exists():
            try:
                # 使用 'w' 模式打开文件会立即清空其内容
                with open(log_file, "w") as f:
                    pass
                user_activity_logger.info(f"Successfully cleared log file: {log_file.name}")
            except Exception as e:
                user_activity_logger.error(f"Failed to clear log file {log_file.name}: {e}", exc_info=True)
        else:
            user_activity_logger.info(f"Log file not found, skipping cleanup: {log_file.name}")


async def scheduled_log_cleanup():
    """一个无限循环的后台任务，定期执行日志清理。"""
    while True:
        try:
            # 等待 30 分钟
            await asyncio.sleep(30 * 60)
            await cleanup_logs()
        except asyncio.CancelledError:
            user_activity_logger.info("Log cleanup scheduler is stopping gracefully.")
            break
        except Exception as e:
            user_activity_logger.error(f"An error occurred in the log cleanup scheduler: {e}", exc_info=True)
            await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI 的生命周期管理器。"""
    # --- 启动时执行 ---
    user_activity_logger.info("Application startup...")
    await create_db_and_tables()
    try:
        await init_redis_pool()
    except Exception as e:
        user_activity_logger.critical(f"FATAL: Failed to initialize Redis. Error: {e}")
        raise RuntimeError("Failed to connect to required service: Redis") from e

    user_activity_logger.info("Starting background tasks...")
    cleanup_task = asyncio.create_task(scheduled_log_cleanup())

    yield

    # --- 关闭时执行 ---
    user_activity_logger.info("Application shutdown...")
    user_activity_logger.info("Stopping background tasks.")
    cleanup_task.cancel()
    await close_redis_pool()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        user_activity_logger.info("Log cleanup task was cancelled successfully.")

