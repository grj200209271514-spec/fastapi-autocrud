from fastapi import APIRouter

# (更新 1) 从每个路由模块中只导入那个唯一的 'router'
# 我们使用 'as' 来给它们起别名，避免命名冲突
# from app.routes.users import router as users_router
from app.routes.items import router as items_router
from app.routes.user import router as user_router
from app.routes.useritems import router as useritems_router

api_router = APIRouter()

# --- (更新 2) 现在每个模块只需要注册一次路由器 ---
# api_router.include_router(
#     users_router,
#     prefix="/users",
#     tags=["Users"]
# )

api_router.include_router(
    items_router,
    prefix="/items",
    tags=["Items"]
)

# 如果你将来添加了新的路由模块（比如 products），也在这里用同样的方式注册
# (新) 2. 注册新的 User-Item 关联路由
# 这个路由将处理所有与用户和物品之间关系相关的操作
api_router.include_router(
    user_router,
    prefix="/users",
    tags=["Users"]
)

api_router.include_router(
    useritems_router,
    prefix="/useritems",
    tags=["Useritems"]
)
