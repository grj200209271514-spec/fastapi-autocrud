import asyncio
import logging
from contextlib import asynccontextmanager  # (关键修复 1) 确保导入
from fastapi import FastAPI
import os
from typing import Union
from pathlib import Path

from app.core.logging_config import LOG_DIR
from app.db.cache import init_redis_pool, close_redis_pool
from app.db.session import engine
from app.models import Base

logger = logging.getLogger(__name__)


async def create_db_and_tables():
    """在应用启动时异步创建所有数据库表。"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("数据库表已检查/创建。")


# (关键修复 1) 让 cleanup_logs 函数接收一个路径参数
async def cleanup_logs(log_dir: Union[Path, str]):
    """明确地清理所有目标日志文件。"""
    LOG_DIR = Path(log_dir)
    log_filenames = ["info.log", "error.log", "api_traffic.log"]
    log_files = [LOG_DIR / filename for filename in log_filenames]
    # ... (函数其余部分不变)
    target_files_str = ", ".join(log_filenames)
    logger.info(f"开始定时清理日志。目标文件: [{target_files_str}]")
    for log_file in log_files:
        if log_file.exists():
            try:
                with open(log_file, "w", encoding='utf-8') as f:
                    pass
                logger.info(f"成功清理日志文件: {log_file.name}")
            except Exception as e:
                logger.error(f"清理日志文件 {log_file.name} 失败: {e}", exc_info=True)
        else:
            logger.info(f"日志文件未找到，跳过清理: {log_file.name}")


# (关键修复 2) 让 scheduled_log_cleanup 函数接收并传递路径参数
async def scheduled_log_cleanup(log_dir: Union[Path, str],minute:int):
    """一个无限循环的后台任务，定期执行日志清理。"""
    while True:
        try:
            await asyncio.sleep(minute * 60)
            await cleanup_logs(log_dir)
        except asyncio.CancelledError:
            logger.info("日志清理调度器正在正常停止。")
            break
        except Exception as e:
            logger.error(f"日志清理调度器发生错误: {e}", exc_info=True)
            await asyncio.sleep(60)


# (关键修复 2) 添加回 @asynccontextmanager 装饰器
@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI 的生命周期管理器。"""

    if os.getenv("TESTING"):
        logger.info("检测到测试环境，跳过应用生命周期事件。")
        yield
        return

    logger.info("应用启动中...")
    await create_db_and_tables()
    try:
        await init_redis_pool()
    except Exception as e:
        logger.critical(f"致命错误: 初始化 Redis 失败。错误: {e}")
        raise RuntimeError("连接到必要的服务失败: Redis") from e

    logger.info("正在启动后台任务...")
    cleanup_task = asyncio.create_task(scheduled_log_cleanup(LOG_DIR,1))

    yield

    logger.info("应用关闭中...")
    logger.info("正在停止后台任务。")
    cleanup_task.cancel()
    await close_redis_pool()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        logger.info("日志清理任务已成功取消。")

