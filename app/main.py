from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.logging_config import LOG_DIR
# 1. 导入配置和日志设置
from app.core.config import settings
from app.core.logging_config import setup_logging
from pathlib import Path
# 2. 导入我们的各个模块
from app.core.lifespan import lifespan  # 生命周期管理器
from app.api import api_router              # 主路由器
from app.middleware.logging import log_and_validate_requests  # 中间件函数
from app.exceptions.handlers import app_exception_handler, generic_exception_handler  # 异常处理器
from app.exceptions.exceptions import AppException # 导入自定义异常基类，使用完整路径




def create_app() -> FastAPI:
    """
    使用应用工厂模式创建并配置 FastAPI 应用实例。
    """
    # 1. 设置日志
    setup_logging(log_dir=LOG_DIR)

    # 2. 创建 FastAPI 实例
    _app = FastAPI(
        title=settings.PROJECT_NAME,
        lifespan=lifespan,
    )

    # 3. 注册中间件
    _app.add_middleware(BaseHTTPMiddleware, dispatch=log_and_validate_requests)

    # 4. 注册全局异常处理器
    _app.add_exception_handler(AppException, app_exception_handler)
    _app.add_exception_handler(Exception, generic_exception_handler)

    # 5. 包含我们的主 API 路由器
    _app.include_router(api_router)

    @_app.get("/")
    def read_root():
        return {"message": f"欢迎使用 {settings.PROJECT_NAME}"}

    return _app


# 全局的应用实例
app = create_app()