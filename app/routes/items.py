import logging
import math
from enum import Enum
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis as AsyncRedis
from pydantic import BaseModel, Field

from app.core.logging_crud import LoggingFastCRUD
from app.core.responses import StandardResponse, Success,PaginationMeta
# (关键修改 1) 导入新的异常类
from app.exceptions.exceptions import ResourceNotFoundException, MissingFieldException, AppException
from app.exceptions.error_codes import ErrorCode
from app.models import Items
from app.schemas import ItemCreate, ItemUpdate, ItemRead, ItemsResponse
from app.db.session import get_db
from app.db.cache import get_redis

logger = logging.getLogger(__name__)

router = APIRouter()
item_crud = LoggingFastCRUD(Items)

CACHE_TTL_SECONDS = 300


class ItemAction(str, Enum):
    GET_BY_ID = "get_by_id"
    GET_ALL = "get_all"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"

class ActionRequest(BaseModel):
    action: ItemAction
    payload: dict = Field(default_factory=dict)


async def _get_item_by_id_handler(payload: dict, db: AsyncSession, redis: AsyncRedis):
    item_id = payload.get("id")
    if not item_id:
        # (关键修改 2) 抛出结构化的异常，而不是 HTTPException
        raise MissingFieldException(name="id")

    cache_key = item_crud._get_cache_key(item_id)
    try:
        if cached_data := await redis.get(cache_key):
            logger.debug(f"CACHE: Hit for key {cache_key}")
            return ItemRead.model_validate_json(cached_data)
    except Exception as e:
        logger.error(f"CACHE_ERROR: Read failed for key {cache_key}: {e}", exc_info=True)

    logger.debug(f"CACHE: Miss for key {cache_key}. Fetching from DB.")
    db_item = await item_crud.get(db=db, iditems=item_id)
    if not db_item:
        # (关键修改 3) 抛出更具体的异常
        raise ResourceNotFoundException(detail=f"ID为 {item_id} 的物品未找到。")

    item_to_cache = ItemRead.model_validate(db_item)
    try:
        await redis.setex(cache_key, CACHE_TTL_SECONDS, item_to_cache.model_dump_json())
    except Exception as e:
        logger.error(f"CACHE_ERROR: Write failed for key {cache_key}: {e}", exc_info=True)
    return item_to_cache


async def _get_all_items_handler(payload: dict, db: AsyncSession, redis: AsyncRedis):
    offset = payload.get("offset", 0)
    limit = payload.get("limit", 100)
    items_orm_list, total_count = await item_crud.get_multi(db=db, offset=offset, limit=limit)
    items_list = [ItemRead.model_validate(item) for item in items_orm_list]
    total_pages = math.ceil(total_count / limit) if limit > 0 else 0
    current_page = (offset // limit) + 1 if limit > 0 else 1
    pagination_meta = {"pagination": PaginationMeta(total_items=total_count, total_pages=total_pages, current_page=current_page, page_size=limit).model_dump()}
    return {"data": ItemsResponse(data=items_list, total_count=total_count), "meta": pagination_meta}


async def _create_item_handler(payload: dict, db: AsyncSession, redis: AsyncRedis):
    try:
        item_create = ItemCreate.model_validate(payload)
    except Exception as e:
        # Pydantic 验证错误，可以抛出一个通用的验证异常
        raise AppException(ErrorCode.VALIDATION_ERROR, detail=str(e))
    new_item_orm = await item_crud.create(db=db, object=item_create)
    return ItemRead.model_validate(new_item_orm)


async def _update_item_handler(payload: dict, db: AsyncSession, redis: AsyncRedis):
    item_id = payload.get("id")
    update_data = payload.get("update_data")
    if not item_id: raise MissingFieldException(name="id")
    if not update_data: raise MissingFieldException(name="update_data")

    try:
        item_update = ItemUpdate.model_validate(update_data)
    except Exception as e:
        raise AppException(ErrorCode.VALIDATION_ERROR, detail=str(e))
    updated_item_orm = await item_crud.update(db=db, object=item_update, iditems=item_id)
    cache_key = item_crud._get_cache_key(item_id)
    try:
        await redis.delete(cache_key)
        logger.info(f"CACHE_INVALIDATE: Deleted cache for key {cache_key}")
    except Exception as e:
        logger.error(f"CACHE_ERROR: Failed to DELETE cache key {cache_key}: {e}", exc_info=True)
    return ItemRead.model_validate(updated_item_orm)


async def _delete_item_handler(payload: dict, db: AsyncSession, redis: AsyncRedis):
    item_id = payload.get("id")
    if not item_id:
        raise MissingFieldException(name="id")
    item_to_delete = await item_crud.get(db=db, iditems=item_id)
    if not item_to_delete:
        raise ResourceNotFoundException(detail=f"ID为 {item_id} 的物品未找到，无法删除。")
    await item_crud.delete(db=db, iditems=item_id)
    cache_key = item_crud._get_cache_key(item_id)
    try:
        await redis.delete(cache_key)
        logger.info(f"CACHE_INVALIDATE: Deleted cache for key {cache_key}")
    except Exception as e:
        logger.error(f"CACHE_ERROR: Failed to DELETE cache key {cache_key}: {e}", exc_info=True)
    return {"message": f"Successfully deleted item with id {item_id}"}


ACTION_HANDLERS = {
    ItemAction.GET_BY_ID: _get_item_by_id_handler,
    ItemAction.GET_ALL: _get_all_items_handler,
    ItemAction.CREATE: _create_item_handler,
    ItemAction.UPDATE: _update_item_handler,
    ItemAction.DELETE: _delete_item_handler,
}

@router.post("/actions", response_model=StandardResponse, summary="统一处理物品操作")
async def handle_item_actions(
        request: ActionRequest,
        db: AsyncSession = Depends(get_db),
        redis: AsyncRedis = Depends(get_redis)
):
    """
    统一处理所有关于 Item 的操作。
    - **action**: 操作名称 (`get_by_id`, `get_all`, `create`, `update`, `delete`)
    - **payload**: 操作所需参数
    """
    handler = ACTION_HANDLERS.get(request.action)
    if not handler:
        # (关键修改 4) 如果 action 不支持，也抛出异常
        raise AppException(ErrorCode.BAD_REQUEST, detail=f"不支持的操作: '{request.action}'")

    # (关键修改 5) 简化 try...except 块
    # 我们不再需要捕获业务异常，因为中间件会统一处理它们
    try:
        result = await handler(payload=request.payload, db=db, redis=redis)
        if request.action == ItemAction.GET_ALL:
            return Success(data=result.get("data"), meta=result.get("meta"))
        return Success(data=result)
    except Exception as e:
        # 如果是我们的自定义异常，直接重新抛出，让中间件处理
        if isinstance(e, AppException):
            raise e
        # 如果是未预料的异常，记录日志并返回一个通用的500错误
        logger.error(f"在操作 '{request.action}' 中发生未处理的服务器错误: {e}", exc_info=True)
        # 这里我们直接抛出，让中间件捕获并格式化500错误
        raise AppException(ErrorCode.UNEXPECTED_ERROR) from e
