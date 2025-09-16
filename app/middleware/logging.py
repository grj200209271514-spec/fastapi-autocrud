import logging
import time
import uuid
from fastapi import Request
from fastapi.responses import JSONResponse

# (关键修改 1) 导入 AppException 基类
from app.exceptions.exceptions import AppException, MissingHeaderException
from app.exceptions.error_codes import ErrorCode

from app.core.logging_config import request_id_var, user_id_var

logger = logging.getLogger(__name__)
api_traffic_logger = logging.getLogger("api_traffic")

PUBLIC_PATHS = {"/docs", "/openapi.json", "/favicon.ico"}

async def log_and_validate_requests(request: Request, call_next):
    """
    一个健壮的中间件，现在统一处理所有 AppException。
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())
    request_id_var.set(request_id)
    user_id_var.set("anonymous")

    response = None
    try:
        if request.url.path not in PUBLIC_PATHS:
            user_id = request.headers.get("x-user-id")
            if not user_id:
                # 抛出我们自定义的、结构化的异常
                raise MissingHeaderException(name='x-user-id')
            user_id_var.set(user_id)

        response = await call_next(request)

    # (关键修改 2) 捕获所有自定义的业务异常
    except AppException as exc:
        logger.warning(
            f"请求被业务异常拒绝: {exc.detail}",
            extra={'error_code': exc.to_dict().get('code')}
        )
        # 使用异常自带的 to_dict() 方法来生成标准化的错误响应
        response = JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.to_dict()}
        )
    except Exception as exc:
        # 这个块保持不变，用于捕获所有未预料到的服务器错误
        error_code_info = ErrorCode.UNEXPECTED_ERROR
        logger.error(
            f"中间件中未处理的异常 (路径: {request.url.path}): {exc}",
            extra={'error_code': error_code_info.get('code')},
            exc_info=True
        )
        response = JSONResponse(
            status_code=500,
            content={"error": error_code_info}
        )
    finally:
        # 这个块保持不变，确保所有请求都被记录
        process_time = (time.time() - start_time) * 1000
        status_code = response.status_code if response else 500
        client_ip = request.client.host if request.client else "unknown"
        log_message = (
            f'"{request.method} {request.url.path}" '
            f'{status_code} {process_time:.2f}ms "{client_ip}"'
        )
        api_traffic_logger.info(log_message)

    return response
