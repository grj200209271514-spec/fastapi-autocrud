from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware

# 1. 导入配置和日志设置
from app.core.config import settings
from logging_config import setup_logging

# 2. 导入我们的各个模块
from app.core.lifespan import lifespan  # 生命周期管理器
from app.api import api_router              # 主路由器
from app.middleware.logging import log_and_validate_requests  # 中间件函数
from app.exceptions.handlers import app_exception_handler, generic_exception_handler  # 异常处理器
from app.exceptions.exceptions import AppException # 导入自定义异常基类，使用完整路径

def create_app() -> FastAPI:
    # 1. 首先设置日志
    setup_logging()

    # 2. 创建 FastAPI 实例，并传入 lifespan 管理器
    app = FastAPI(
        title=settings.PROJECT_NAME,
        lifespan=lifespan
    )

    # 3. 注册中间件
    # (我们使用 BaseHTTPMiddleware 来包装我们的异步函数)
    app.add_middleware(BaseHTTPMiddleware, dispatch=log_and_validate_requests)

    # 4. 注册全局异常处理器
    # 将 app_exception_handler 函数与 AppException 异常类型关联起来。
    # 如果raise了AppException，就调用app_exception_handler 来处理它
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)


    # 5. 包含我们的主 API 路由器
    app.include_router(api_router)  # api_router = APIRouter()

    return app

# 创建应用实例，以便 run.py 可以导入它
app = create_app()
