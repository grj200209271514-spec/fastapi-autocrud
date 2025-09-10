import logging
import math
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis as AsyncRedis

from app.core.logging_crud import LoggingFastCRUD
from app.core.responses import StandardResponse, Success, PaginationMeta
from models import Items
from schemas import ItemCreate, ItemUpdate, ItemRead, ItemsResponse
from app.db.session import get_db
from app.db.cache import get_redis
from app.exceptions.exceptions import ResourceNotFoundException

user_activity_logger = logging.getLogger("user_activity")

router = APIRouter()
item_crud = LoggingFastCRUD(Items)

CACHE_TTL_SECONDS = 300


@router.get("/{id}", response_model=StandardResponse[ItemRead])
async def get_item_by_id_cached(
        id: int,
        db: AsyncSession = Depends(get_db),
        redis: AsyncRedis = Depends(get_redis)
):
    """
    通过 ID 获取单个 Item，采用旁路缓存策略。
    """
    cache_key = item_crud._get_cache_key(id)

    try:
        cached_data_json = await redis.get(cache_key)
        if cached_data_json:
            user_activity_logger.debug(f"CACHE: Hit for key {cache_key}")
            item_data = ItemRead.model_validate_json(cached_data_json)
            return Success(data=item_data)
    except Exception as e:
        user_activity_logger.error(f"CACHE_ERROR: Failed to READ from cache key {cache_key}: {e}", exc_info=True)

    user_activity_logger.debug(f"CACHE: Miss for key {cache_key}. Fetching from DB.")

    pk_name = item_crud._primary_keys[0].name
    db_item = await item_crud.get(db=db, **{pk_name: id})

    if db_item is None:
        raise ResourceNotFoundException(detail=f"Item with id={id} not found.")

    try:
        item_to_cache = ItemRead.model_validate(db_item)
        await redis.setex(
            cache_key,
            CACHE_TTL_SECONDS,
            item_to_cache.model_dump_json()
        )
    except Exception as e:
        user_activity_logger.error(f"CACHE_ERROR: Failed to WRITE to cache key {cache_key}: {e}", exc_info=True)

    return Success(data=db_item)


@router.get("/", response_model=StandardResponse[ItemsResponse])
async def get_all_items(
        db: AsyncSession = Depends(get_db),
        offset: int = 0,
        limit: int = 100
):
    """
    获取物品列表 (get_multi)，并返回带有完整分页元数据的响应。
    """
    # (关键修复) 直接使用 fastcrud 自带的 get_multi，它已包含数据和总数
    multi_response = await item_crud.get_multi(db=db, offset=offset, limit=limit)
    items_list = multi_response['data']
    total_items = multi_response['total_count']

    total_pages = math.ceil(total_items / limit) if limit > 0 else 0
    current_page = (offset // limit) + 1 if limit > 0 else 1

    pagination_meta = {
        "pagination": PaginationMeta(
            total_items=total_items,
            total_pages=total_pages,
            current_page=current_page,
            page_size=limit
        ).model_dump()
    }

    # 现在 response_data 的构建是正确的
    response_data = ItemsResponse(data=items_list, total_count=total_items)

    return Success(data=response_data, meta=pagination_meta)


@router.post("/", response_model=StandardResponse[ItemRead])
async def create_item(
        item_create: ItemCreate,
        db: AsyncSession = Depends(get_db)
):
    """创建一个新物品 (create)。"""
    new_item = await item_crud.create(db=db, object=item_create)
    return Success(data=new_item)


@router.patch("/{iditems}", response_model=StandardResponse[ItemRead])
async def update_item(
        iditems: int,
        item_update: ItemUpdate,
        db: AsyncSession = Depends(get_db)
):
    """更新单个物品 (update)。"""
    updated_item = await item_crud.update(db=db, object=item_update, iditems=iditems)
    return Success(data=updated_item)


@router.delete("/{iditems}", response_model=StandardResponse[dict])
async def delete_item(
        iditems: int,
        db: AsyncSession = Depends(get_db)
):
    """删除单个物品 (delete)。"""
    await item_crud.delete(db=db, iditems=iditems)
    return Success(data={"message": f"Successfully deleted item with id {iditems}"})

