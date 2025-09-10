import logging
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError
from redis.asyncio import Redis as AsyncRedis

from app.core.logging_crud import LoggingFastCRUD
# 关键修改 1: 导入我们最终确定的标准响应模型和辅助函数
from app.core.responses import StandardResponse, Success

from models import Users
from schemas import UserCreate, UserUpdate, UserRead, UserResponse
from app.exceptions.exceptions import ResourceNotFoundException, DuplicateResourceException
from app.db.session import get_db
from app.db.cache import get_redis

user_activity_logger = logging.getLogger("user_activity")

router = APIRouter()
crud = LoggingFastCRUD(Users)

CACHE_TTL_SECONDS = 300  # 缓存 5 分钟


@router.get("/{id}", response_model=StandardResponse[UserRead])
async def get_user_by_id_cached(
        id: int,
        db: AsyncSession = Depends(get_db),
        redis: AsyncRedis = Depends(get_redis)
):
    """
    通过 ID 获取单个 User，采用旁路缓存策略。
    """
    cache_key = crud._get_cache_key(id)

    try:
        cached_data_json = await redis.get(cache_key)
        if cached_data_json:
            user_activity_logger.debug(f"CACHE: Hit for key {cache_key}")
            item_data = UserRead.model_validate_json(cached_data_json)
            # 关键修改 2: 使用新的 Success() 辅助函数
            return Success(data=item_data)
    except Exception as e:
        user_activity_logger.error(f"CACHE_ERROR: Failed to READ from cache key {cache_key}: {e}", exc_info=True)

    user_activity_logger.debug(f"CACHE: Miss for key {cache_key}. Fetching from DB.")
    pk_name = crud._primary_keys[0].name
    db_item = await crud.get(db=db, **{pk_name: id})

    if db_item is None:
        raise ResourceNotFoundException(detail=f"未能找到 ID 为 '{id}' 的用户。")

    try:
        item_to_cache = UserRead.model_validate(db_item)
        await redis.setex(
            cache_key,
            CACHE_TTL_SECONDS,
            item_to_cache.model_dump_json()
        )
    except Exception as e:
        user_activity_logger.error(f"CACHE_ERROR: Failed to WRITE to cache key {cache_key}: {e}", exc_info=True)

    # 关键修改 3: 使用新的 Success() 辅助函数
    return Success(data=db_item)


@router.get("/search/{name}", response_model=StandardResponse[list[UserRead]])
async def search_users_by_name(name: str, db: AsyncSession = Depends(get_db)):
    """按名称模糊搜索用户。"""
    user_activity_logger.info(f"Searching for users with name like '{name}'.")
    query = select(Users).where(Users.name.like(f"%{name}%"))
    result = await db.execute(query)
    users = result.scalars().all()
    if not users:
        raise ResourceNotFoundException(detail=f"没有找到名称类似于 '{name}' 的用户。")

    return Success(data=users)


@router.post("/", response_model=StandardResponse[UserRead])
async def create_user_custom(user: UserCreate, db: AsyncSession = Depends(get_db)):
    """创建一个新用户，并处理邮箱重复的场景。"""
    user_activity_logger.info(f"Attempting to create user with email '{user.email}'.")
    new_user = Users(name=user.name, email=user.email, password=user.password)
    db.add(new_user)
    try:
        await db.commit()
        await db.refresh(new_user)
        return Success(data=new_user)
    except IntegrityError:
        await db.rollback()
        raise DuplicateResourceException(detail=f"邮箱为 '{user.email}' 的用户已存在。")


@router.delete("/by_name/{name}", response_model=StandardResponse[dict])
async def delete_users_by_name(name: str, db: AsyncSession = Depends(get_db)):
    """按名称删除一个或多个用户。"""
    user_activity_logger.info(f"Attempting to delete users with name '{name}'.")
    stmt = delete(Users).where(Users.name == name)
    result = await db.execute(stmt)
    if result.rowcount == 0:
        raise ResourceNotFoundException(detail=f"名称为 '{name}' 的用户不存在，无法删除。")
    await db.commit()
    response_data = {"message": f"成功删除名称为 '{name}' 的用户。", "deleted_count": result.rowcount}
    return Success(data=response_data)


# --- 标准 CRUD 端点 ---

@router.get("/", response_model=StandardResponse[UserResponse])
async def get_all_users(
    db: AsyncSession = Depends(get_db),
    offset: int = 0,
    limit: int = 100
):
    """获取用户列表 (get_multi)。"""
    users = await crud.get_multi(db=db, offset=offset, limit=limit)
    return Success(data=users)


@router.patch("/{id}", response_model=StandardResponse[UserRead])
async def update_user(
        id: int,
        user_update: UserUpdate,
        db: AsyncSession = Depends(get_db)
):
    """更新单个用户 (update)。"""
    updated_user = await crud.update(db=db, object=user_update, id=id)
    return Success(data=updated_user)


@router.delete("/{id}", response_model=StandardResponse[dict])
async def delete_user(
        id: int,
        db: AsyncSession = Depends(get_db)
):
    """删除单个用户 (delete)。"""
    await crud.delete(db=db, id=id)
    return Success(data={"message": f"成功删除 ID 为 {id} 的用户。"})

