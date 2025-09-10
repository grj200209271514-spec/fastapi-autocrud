# 导入你的 ErrorCode，确保路径正确
# 假设它在 app/common/error_codes.py
from app.exceptions.error_codes import ErrorCode


class AppException(Exception):
    """所有自定义业务异常的基类。"""

    def __init__(self, error_code: dict, detail: str | None = None, **kwargs):
        self.error_code = error_code
        self.status_code = error_code.get("status_code", 400)
        message_template = error_code.get("message", "服务器发生未知错误。")
        self.detail = detail or message_template.format(**kwargs)
        super().__init__(self.detail)

    def to_dict(self) -> dict:
        """将异常安全地转换为一个字典，用于JSON响应。"""
        return {
            "code": self.error_code.get("code", "UNKNOWN_CODE"),
            "message": self.detail
        }


class MissingHeaderException(AppException):
    """当请求中缺少必要的头信息时抛出。"""

    def __init__(self, name: str, detail: str | None = None):
        # 关键修改：统一使用 'name' 作为关键字参数，与 response_codes.py 中的 '{name}' 占位符对应
        super().__init__(
            error_code=ErrorCode.MISSING_REQUIRED_HEADER,
            detail=detail,
            name=name  # 传递 'name' 关键字参数
        )


# 新增：一个具体的示例，展示了 'name' 参数的可重用性
class MissingFieldException(AppException):
    """当请求体中缺少必要的字段时抛出。"""

    def __init__(self, name: str, detail: str | None = None):
        super().__init__(
            error_code=ErrorCode.MISSING_REQUIRED_FIELD,
            detail=detail,
            name=name  # 同样使用 'name' 关键字参数
        )


# --- 其他异常类保持不变，因为它们不需要动态参数 ---
class ResourceNotFoundException(AppException):
    """当在数据库中找不到特定资源时抛出。"""
    def __init__(self, detail: str | None = None):
        super().__init__(
            error_code=ErrorCode.RESOURCE_NOT_FOUND,
            detail=detail
        )


class DuplicateResourceException(AppException):
    """当尝试创建已存在的资源时抛出 (例如，邮箱已注册)。"""
    def __init__(self, detail: str | None = None):
        super().__init__(
            error_code=ErrorCode.DUPLICATE_RESOURCE,
            detail=detail
        )


class InvalidCredentialsException(AppException):
    """当提供的认证信息无效时抛出 (例如，密码错误)。"""
    def __init__(self, detail: str | None = None):
        super().__init__(
            error_code=ErrorCode.INVALID_CREDENTIALS,
            detail=detail
        )


class PermissionDeniedException(AppException):
    """当用户认证成功但权限不足以执行操作时抛出。"""
    def __init__(self, detail: str | None = None):
        super().__init__(
            error_code=ErrorCode.PERMISSION_DENIED,
            detail=detail
        )

# 你可以根据需要添加更多具体的异常类
# class ValidationErrorException(AppException):
#     def __init__(self, detail: str | None = None):
#         super().__init__(
#             error_code=ErrorCode.VALIDATION_ERROR,
#             detail=detail
#         )