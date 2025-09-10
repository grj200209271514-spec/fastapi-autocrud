import logging
from fastapi import Request
from fastapi.responses import JSONResponse

from app.exceptions.exceptions import AppException
from app.exceptions.error_codes import ErrorCode

error_logger = logging.getLogger("error")  # 建议为错误使用专门的logger


async def app_exception_handler(request: Request, exc: AppException):
    """
    处理所有继承自 AppException 的业务异常。
    这个版本是简化的、健壮的，不会再自我崩溃。
    """

    # 使用 .to_dict() 方法安全地获取错误内容
    error_content = exc.to_dict()

    # 记录一条警告级别的业务异常日志
    error_logger.warning(
        f"Business exception occurred on request {request.method} {request.url.path}: "
        f"Code={error_content['code']}, Message={error_content['message']}"
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": error_content.get("code"),
            "message": error_content.get("message"),
            "details": getattr(exc, 'details', None)
        }
    )


async def generic_exception_handler(request: Request, exc: Exception):
    """处理所有未捕获的服务器内部错误。"""
    error_logger.error(
        f"Unhandled exception on request {request.method} {request.url.path}:",
        exc_info=True
    )

    # 获取通用错误码信息
    error_code_info = ErrorCode.UNEXPECTED_ERROR

    # 返回与 app_exception_handler 完全一致的扁平化结构
    return JSONResponse(
        status_code=500,
        content={
            "code": error_code_info.get("code"),
            "message": error_code_info.get("message"),
            "details": None
        }
    )