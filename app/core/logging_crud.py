import logging
import redis.asyncio as aioredis
from app.db import cache
from fastcrud import FastCRUD
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, TypeVar
from pydantic import BaseModel

# --- (关键修复 1) 导入 SQLAlchemy 的 inspect 功能 ---
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError, NoResultFound
from app.exceptions.exceptions import ResourceNotFoundException,DuplicateResourceException

# --- 泛型类型定义 ---
ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)
ReadSchemaType = TypeVar("ReadSchemaType", bound=BaseModel)
ReadMultiSchemaType = TypeVar("ReadMultiSchemaType", bound=BaseModel)
DeleteSchemaType = TypeVar("DeleteSchemaType", bound=BaseModel) # <-- 添加这一行


# 获取用户活动记录器
user_activity_logger = logging.getLogger("user_activity")


class LoggingFastCRUD(
    FastCRUD[ModelType, CreateSchemaType, UpdateSchemaType, ReadSchemaType, ReadMultiSchemaType,DeleteSchemaType]):
    """
    一个自定义的 FastCRUD 子类，它会自动为
    Create, Update, 和 Delete 操作添加详细的日志记录和缓存失效。
    """

    def __init__(self, model: ModelType):
        # 首先，调用父类的构造方法，以运行它可能有的任何基础设置
        super().__init__(model)

        # --- (关键修复 2) 手动检查模型并设置主键 ---
        # 无论父类做了什么，我们都用 SQLAlchemy 的官方方法来确保 _primary_keys 属性被正确设置。
        # 这使得我们的代码不再受 fastcrud 库内部实现变化的影响。
        self._primary_keys = inspect(model).primary_key

    def _get_model_name(self) -> str:
        """获取模型类的名称 (例如："Items", "Product")"""
        return self.model.__name__

    def _get_cache_key(self, id: Any) -> str:
        """为单个条目生成标准化的 Redis 缓存键。"""
        return f"{self._get_model_name()}:{id}"

    def _get_primary_key_info(self, kwargs: dict) -> tuple[str, Any]:
        """一个辅助函数，用于从 kwargs 中提取主键名和值。"""
        # 现在这行代码可以安全地执行了
        pk_name = self._primary_keys[0].name
        pk_value = kwargs.get(pk_name)
        if pk_value is None:
            raise ValueError(f"主键 '{pk_name}' 未在参数中找到。")
        return pk_name, pk_value

    async def create(
            self,
            db: AsyncSession,
            object: CreateSchemaType,
            **kwargs: Any
    ) -> ModelType:
        model_name = self._get_model_name()
        log_data = "Data: " + object.model_dump_json()

        try:
            user_activity_logger.info(f"尝试创建实体: {model_name}. {log_data}")
            new_item = await super().create(db, object, **kwargs)
            pk_name = self._primary_keys[0].name
            new_id = getattr(new_item, pk_name, "UNKNOWN_ID")
            user_activity_logger.info(f"成功: 创建了 {model_name}，ID为: {new_id}。")
            return new_item


            # (关键修复 2) 捕获数据库的 IntegrityError
        except IntegrityError as e:
            # 将其“翻译”成我们自定义的、更具体的业务异常
            user_activity_logger.warning(
                f"警告: 创建 {model_name} 失败，资源已存在. {log_data}. 数据库错误: {e.orig}"
            )
            # 这里的 DuplicateResourceException 会被中间件捕获，并返回 409 Conflict
            raise DuplicateResourceException() from e

        except Exception as e:
            user_activity_logger.error(f"失败: 创建 {model_name} 失败. {log_data}. 错误: {e}", exc_info=True)
            raise e

    async def update(
            self,
            db: AsyncSession,
            object: UpdateSchemaType,
            **kwargs: Any
    ) -> ModelType:
        model_name = self._get_model_name()
        log_data = "Data: " + object.model_dump_json(exclude_unset=True)

        try:
            pk_name, pk_value = self._get_primary_key_info(kwargs)
            user_activity_logger.info(f"尝试更新 {model_name} (条件: {pk_name}={pk_value}). {log_data}")
            updated_item = await super().update(db=db, object=object, **kwargs)
            user_activity_logger.info(f"成功: 更新了 {model_name}，ID为: {pk_value}。")

            cache_key = self._get_cache_key(pk_value)
            try:
                if cache.redis_pool:
                    async with aioredis.Redis(connection_pool=cache.redis_pool) as redis:
                        await redis.delete(cache_key)
                        user_activity_logger.info(f"缓存: 已使键失效 (删除): {cache_key}")
                else:
                    user_activity_logger.warning("缓存: Redis 连接池不可用，跳过失效操作。")
            except Exception as e:
                user_activity_logger.error(f"缓存错误: 使键 {cache_key} 失效失败. 错误: {e}",
                                           exc_info=True)
            return updated_item
        except NoResultFound:
            pk_name, pk_value = self._get_primary_key_info(kwargs)
            user_activity_logger.warning(
                f"失败: 更新 {model_name} (ID: {pk_value}) 失败. 物品未找到。"
            )
            raise ResourceNotFoundException(
                detail=f"未能找到 ID 为 '{pk_value}' 的 {model_name}。"
            )
        except Exception as e:
            pk_info_str = f"参数为 kwargs={kwargs}"
            user_activity_logger.error(f"失败: 更新 {model_name} ({pk_info_str}) 失败. 数据: {log_data}. 错误: {e}",
                                       exc_info=True)
            raise e

    async def delete(
            self,
            db: AsyncSession,
            **kwargs: Any
    ) -> None:
        model_name = self._get_model_name()
        try:
            pk_name, pk_value = self._get_primary_key_info(kwargs)
            user_activity_logger.info(f"尝试删除 {model_name} (条件: {pk_name}={pk_value}).")

            await super().delete(db=db, **kwargs)
            user_activity_logger.info(f"成功: 删除了 {model_name}，ID为: {pk_value}。")

            cache_key = self._get_cache_key(pk_value)
            try:
                if cache.redis_pool:
                    async with aioredis.Redis(connection_pool=cache.redis_pool) as redis:
                        await redis.delete(cache_key)
                        user_activity_logger.info(f"缓存: 已使键失效 (删除): {cache_key}")
                else:
                    user_activity_logger.warning("缓存: Redis 连接池不可用，跳过失效操作。")
            except Exception as e:
                user_activity_logger.error(f"缓存错误: 使键 {cache_key} 失效失败. 错误: {e}",
                                           exc_info=True)
        except NoResultFound:
            pk_name, pk_value = self._get_primary_key_info(kwargs)
            user_activity_logger.warning(
                f"失败: 删除 {model_name} (ID: {pk_value}) 失败. 物品未找到。"
            )
            raise ResourceNotFoundException(
                detail=f"未能找到 ID 为 '{pk_value}' 的 {model_name}。"
            )
        except Exception as e:
            pk_info_str = f"参数为 kwargs={kwargs}"
            user_activity_logger.error(f"失败: 删除 {model_name} ({pk_info_str}) 失败. 错误: {e}", exc_info=True)
            raise e

