import logging
import math
from enum import Enum
from typing import Type, Dict, Any, Callable
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis as AsyncRedis
from dataclasses import dataclass

from app.core.logging_crud import LoggingFastCRUD
from app.core.responses import StandardResponse, Success, PaginationMeta
from app.exceptions.exceptions import ResourceNotFoundException, MissingFieldException, AppException
from app.exceptions.error_codes import ErrorCode
from app.db.session import get_db
from app.db.cache import get_redis

logger = logging.getLogger(__name__)

@dataclass
class CRUDSchemas:
    Create: Type[BaseModel]
    Update: Type[BaseModel]
    Read: Type[BaseModel]
    MultiResponse: Type[BaseModel]


def create_actions_router(
    crud_instance: LoggingFastCRUD,
    schemas: CRUDSchemas,
    prefix: str,
    tags: list[str],
    primary_key_name: str = "id",
    custom_actions: Dict[str, Callable] = None # (关键新增 1) 允许传入自定义 action
) -> APIRouter:
    router = APIRouter(prefix=prefix, tags=tags)
    entity_name = crud_instance.model.__name__

    # --- 动态创建 Action 枚举 ---
    actions = {
        "get_by_id": "get_by_id",
        "get_all": "get_all",
        "create": "create",
        "update": "update",
        "delete": "delete",
    }
    # 将使用者传入的自定义 action 名称也加入到枚举中
    if custom_actions:
        for name in custom_actions:
            actions[name] = name
    ActionEnum = Enum("ActionEnum", actions)

    class ActionRequest(BaseModel):
        action: ActionEnum
        payload: dict = Field(default_factory=dict)

    # --- 通用 Handler 函数 ---
    async def _get_by_id_handler(payload: dict, db: AsyncSession, redis: AsyncRedis):
        entity_id = payload.get("id")
        if not entity_id: raise MissingFieldException(name="id")

        db_entity = await crud_instance.get(db=db, **{primary_key_name: entity_id})
        if not db_entity:
            raise ResourceNotFoundException(detail=f"ID为 {entity_id} 的{entity_name}未找到。")
        return schemas.Read.model_validate(db_entity)

    async def _get_all_handler(payload: dict, db: AsyncSession, redis: AsyncRedis):
        offset, limit = payload.get("offset", 0), payload.get("limit", 100)
        orm_list, total_count = await crud_instance.get_multi(db=db, offset=offset, limit=limit)
        pydantic_list = [schemas.Read.model_validate(item) for item in orm_list]
        total_pages = math.ceil(total_count / limit) if limit > 0 else 0
        current_page = (offset // limit) + 1 if limit > 0 else 1
        pagination_meta = {
            "pagination": PaginationMeta(total_items=total_count, total_pages=total_pages, current_page=current_page,
                                         page_size=limit).model_dump()}
        return {"data": schemas.MultiResponse(data=pydantic_list, total_count=total_count), "meta": pagination_meta}

    async def _create_handler(payload: dict, db: AsyncSession, redis: AsyncRedis):
        try:
            create_schema = schemas.Create.model_validate(payload)
        except Exception as e:
            raise AppException(ErrorCode.VALIDATION_ERROR, detail=str(e))
        new_orm = await crud_instance.create(db=db, object=create_schema)
        return schemas.Read.model_validate(new_orm)

    async def _update_handler(payload: dict, db: AsyncSession, redis: AsyncRedis):
        entity_id, update_data = payload.get("id"), payload.get("update_data")
        if not entity_id: raise MissingFieldException(name="id")
        if not update_data: raise MissingFieldException(name="update_data")

        try:
            update_schema = schemas.Update.model_validate(update_data)
        except Exception as e:
            raise AppException(ErrorCode.VALIDATION_ERROR, detail=str(e))

        updated_orm = await crud_instance.update(db=db, object=update_schema, **{primary_key_name: entity_id})
        # Note: Cache invalidation is handled inside crud_instance.update
        return schemas.Read.model_validate(updated_orm)

    async def _delete_handler(payload: dict, db: AsyncSession, redis: AsyncRedis):
        entity_id = payload.get("id")
        if not entity_id: raise MissingFieldException(name="id")

        await crud_instance.delete(db=db, **{primary_key_name: entity_id})
        return {"message": f"成功删除 ID 为 {entity_id} 的 {entity_name}。"}

    ACTION_HANDLERS: Dict[str, Callable] = {
        "get_by_id": _get_by_id_handler,
        "get_all": _get_all_handler,
        "create": _create_handler,
        "update": _update_handler,
        "delete": _delete_handler,
    }

    if custom_actions:
        ACTION_HANDLERS.update(custom_actions)  # (关键新增 2) 将自定义 handler 合并进来

    @router.post("/actions", response_model=StandardResponse, summary=f"统一处理 {entity_name} 操作")
    async def handle_actions(request: ActionRequest, db: AsyncSession = Depends(get_db),
                             redis: AsyncRedis = Depends(get_redis)):
        handler = ACTION_HANDLERS.get(request.action.value)
        if not handler:
            raise AppException(ErrorCode.BAD_REQUEST, detail=f"不支持的操作: '{request.action.value}'")

        result = await handler(payload=request.payload, db=db, redis=redis)

        # 检查 action 是否需要返回分页格式
        paginated_actions = ["get_all"]
        if custom_actions:
            paginated_actions.extend(custom_actions.keys())

        if request.action.value in paginated_actions:
            if result and isinstance(result, dict) and "data" in result and "meta" in result:
                return Success(data=result.get("data"), meta=result.get("meta"))

        return Success(data=result)

    return router