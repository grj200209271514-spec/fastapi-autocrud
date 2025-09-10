import logging
import time
import uuid
from fastapi import Request, Response
from fastapi.responses import JSONResponse

# 导入你的自定义异常和响应码
from app.exceptions.exceptions import MissingHeaderException
from app.exceptions.error_codes import ErrorCode

# 导入 context variables 和 logger
from logging_config import request_id_var, user_id_var

# 为不同的日志目的获取不同的记录器
api_traffic_logger = logging.getLogger("api_traffic")
error_logger = logging.getLogger("error")

# 定义不需要进行用户ID检查的公共路径
PUBLIC_PATHS = {"/docs", "/openapi.json", "/favicon.ico"}


async def log_and_validate_requests(request: Request, call_next):
    """
    一个健壮的中间件，它:
    1. 生成 request_id。
    2. 在中间件内部通过 try...except 优雅地处理缺失请求头的错误。
    3. 记录带有完整上下文和状态码的请求日志。
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())
    request_id_var.set(request_id)
    user_id_var.set("anonymous")

    response = None # 在 try...except 外定义 response
    try:
        # --- 核心验证逻辑 ---
        if request.url.path not in PUBLIC_PATHS:
            user_id = request.headers.get("x-user-id")
            if not user_id:
                raise MissingHeaderException(name='X-User-ID')
            user_id_var.set(user_id)

        # --- 请求处理 ---
        response = await call_next(request)

    except MissingHeaderException as exc:
        # --- 捕获业务异常 ---
        log_message = f"Request rejected: {exc.detail}"
        error_logger.warning(
            log_message,
            extra={'error_code': exc.error_code.get('code')}
        )
        # 创建错误响应
        response = JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.to_dict()}
        )
    except Exception as exc:
        # --- (新增) 捕获所有其他意外错误 ---
        error_logger.error(
            f"Unhandled exception in middleware for path {request.url.path}: {exc}",
            extra={'error_code': 'UNHANDLED_MIDDLEWARE_ERROR'},
            exc_info=True
        )
        # 创建一个通用的500错误响应
        response = JSONResponse(
            status_code=500,
            content={"error": ErrorCode.UNEXPECTED_ERROR}
        )
    finally:
        # --- 无论成功或失败，都记录API流量 ---
        process_time = (time.time() - start_time) * 1000
        # 关键修改：从 response 对象中获取 status_code
        status_code = response.status_code if response else 500
        api_traffic_logger.info(
            f"Request Finished: {request.method} {request.url.path} "
            f"completed in {process_time:.2f}ms with status code {status_code}"
        )

    return response

