import logging
import redis.asyncio as aioredis
from typing import Any, TypeVar, Tuple, List
from pydantic import BaseModel

from fastcrud import FastCRUD
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.exc import NoResultFound

from app.db import cache
from app.exceptions.exceptions import ResourceNotFoundException

# 1. (关键修改) 新增 ReadSchemaType, ReadMultiSchemaType, DeleteSchemaType 的泛型定义
ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)
ReadSchemaType = TypeVar("ReadSchemaType", bound=BaseModel)
ReadMultiSchemaType = TypeVar("ReadMultiSchemaType", bound=BaseModel)
DeleteSchemaType = TypeVar("DeleteSchemaType", bound=BaseModel)

# 获取用户活动记录器
user_activity_logger = logging.getLogger("user_activity")


# 2. (关键修改) 更新 LoggingFastCRUD 的继承声明，包含了所有必需的类型
class LoggingFastCRUD(
    FastCRUD[ModelType, CreateSchemaType, UpdateSchemaType, ReadSchemaType, ReadMultiSchemaType, DeleteSchemaType]
):
    """
    一个自定义的 FastCRUD 子类，它会自动为
    Create, Update, Delete 操作添加日志和缓存失效，
    并增加了用于分页的计数功能。
    """

    # --- 辅助方法 ---
    def _get_model_name(self) -> str:
        return self.model.__name__

    def _get_cache_key(self, id: Any) -> str:
        return f"{self._get_model_name()}:{id}"

    def _get_primary_key_info(self, kwargs: dict) -> tuple[str, Any]:
        pk_name = self._primary_keys[0].name
        pk_value = kwargs.get(pk_name)
        if pk_value is None:
            raise ValueError(f"Primary key '{pk_name}' not found in arguments.")
        return pk_name, pk_value

    # --- 分页功能 ---
    async def count(self, db: AsyncSession, **kwargs: Any) -> int:
        query = select(func.count()).select_from(self.model)
        if kwargs:
            query = query.filter_by(**kwargs)
        result = await db.execute(query)
        return result.scalar_one()

    async def get_multi_and_count(
            self,
            db: AsyncSession,
            offset: int = 0,
            limit: int = 100,
            **kwargs: Any
    ) -> Tuple[List[ModelType], int]:
        items = await super().get_multi(db=db, offset=offset, limit=limit, **kwargs)
        total_count = await self.count(db=db, **kwargs)
        return items, total_count

    # --- 带日志和缓存的 CUD 操作 ---
    async def create(
            self,
            db: AsyncSession,
            object: CreateSchemaType,
            **kwargs: Any
    ) -> ModelType:
        model_name = self._get_model_name()
        log_data = "Data: " + object.model_dump_json()
        try:
            user_activity_logger.info(f"Attempting to CREATE entity: {model_name}. {log_data}")
            new_item = await super().create(db, object, **kwargs)
            pk_name = self._primary_keys[0].name
            new_id = getattr(new_item, pk_name, "UNKNOWN_ID")
            user_activity_logger.info(f"SUCCESS: Created {model_name} with ID: {new_id}.")
            return new_item
        except Exception as e:
            user_activity_logger.error(f"FAILED to CREATE {model_name}. {log_data}. Error: {e}", exc_info=True)
            raise e

    async def update(
            self,
            db: AsyncSession,
            object: UpdateSchemaType,
            **kwargs: Any
    ) -> ModelType:
        model_name = self._get_model_name()
        log_data = "Data: " + object.model_dump_json(exclude_unset=True)
        pk_name, pk_value = self._get_primary_key_info(kwargs)

        try:
            user_activity_logger.info(f"Attempting to UPDATE {model_name} where {pk_name}={pk_value}. {log_data}")
            updated_item = await super().update(db=db, object=object, **kwargs)
            user_activity_logger.info(f"SUCCESS: Updated {model_name} with ID: {pk_value}.")

            cache_key = self._get_cache_key(pk_value)
            try:
                if cache.redis_pool:
                    async with aioredis.Redis(connection_pool=cache.redis_pool) as redis:
                        await redis.delete(cache_key)
                        user_activity_logger.info(f"CACHE: Invalidated (deleted) key: {cache_key}")
            except Exception as e:
                user_activity_logger.error(f"CACHE_ERROR: Failed to invalidate key {cache_key}. Error: {e}",
                                           exc_info=True)

            return updated_item
        except NoResultFound:
            user_activity_logger.warning(f"FAILED to UPDATE {model_name} with ID: {pk_value}. Item not found.")
            raise ResourceNotFoundException(detail=f"未能找到 ID 为 '{pk_value}' 的 {model_name}。")
        except Exception as e:
            user_activity_logger.error(f"FAILED to UPDATE {model_name} with ID {pk_value}. {log_data}. Error: {e}",
                                       exc_info=True)
            raise e

    async def delete(
            self,
            db: AsyncSession,
            **kwargs: Any
    ) -> ModelType:
        model_name = self._get_model_name()
        pk_name, pk_value = self._get_primary_key_info(kwargs)
        try:
            user_activity_logger.info(f"Attempting to DELETE {model_name} where {pk_name}={pk_value}.")
            deleted_item = await super().delete(db=db, **kwargs)
            user_activity_logger.info(f"SUCCESS: Deleted {model_name} with ID: {pk_value}.")

            cache_key = self._get_cache_key(pk_value)
            try:
                if cache.redis_pool:
                    async with aioredis.Redis(connection_pool=cache.redis_pool) as redis:
                        await redis.delete(cache_key)
                        user_activity_logger.info(f"CACHE: Invalidated (deleted) key: {cache_key}")
            except Exception as e:
                user_activity_logger.error(f"CACHE_ERROR: Failed to invalidate key {cache_key}. Error: {e}",
                                           exc_info=True)

            return deleted_item
        except NoResultFound:
            user_activity_logger.warning(f"FAILED to DELETE {model_name} with ID: {pk_value}. Item not found.")
            raise ResourceNotFoundException(detail=f"未能找到 ID 为 '{pk_value}' 的 {model_name}。")
        except Exception as e:
            user_activity_logger.error(f"FAILED to DELETE {model_name} with ID {pk_value}. Error: {e}", exc_info=True)
            raise e

