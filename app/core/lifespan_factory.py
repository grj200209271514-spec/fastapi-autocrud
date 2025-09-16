import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Type
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.orm import DeclarativeBase

# 导入库自身的后台任务
from .lifespan import scheduled_log_cleanup

logger = logging.getLogger(__name__)


def create_app_lifespan(
        db_engine: AsyncEngine,
        db_base: Type[DeclarativeBase],
        log_dir: Path,
        log_cleanup_interval_minutes: int = 60
):
    """
    生命周期管理的工厂函数。
    接收项目特定的组件，返回一个配置好的 lifespan 管理器。
    """

    async def _create_db_and_tables():
        """使用传入的 engine 和 Base 创建数据库表。"""
        async with db_engine.begin() as conn:
            await conn.run_sync(db_base.metadata.create_all)
        logger.info("项目数据库表已检查/创建。")

    @asynccontextmanager
    async def lifespan_manager(app):
        # --- 启动时执行 ---
        logger.info(f"'{app.title}' 正在启动...")

        # 1. 执行数据库初始化
        await _create_db_and_tables()

        # 2. 启动后台日志清理任务
        logger.info("正在启动后台日志清理任务...")
        cleanup_task = asyncio.create_task(
            scheduled_log_cleanup(log_dir, log_cleanup_interval_minutes)
        )

        yield

        # --- 关闭时执行 ---
        logger.info(f"'{app.title}' 正在关闭...")
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            logger.info("后台日志清理任务已成功取消。")

    # 返回最终配置好的 lifespan 管理器
    return lifespan_manager