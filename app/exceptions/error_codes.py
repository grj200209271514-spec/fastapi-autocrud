class SuccessCode:
    """
    一个用于集中管理 API 成功响应码和描述的类。
    """
    OK = {
        # 'code' 字段可以用于前后端约定，但HTTP状态码是主要的成功标识
        "code": "OK",
        "message": "操作成功",
        # 关键修改：使用标准的 HTTP 状态码 200 表示成功
        "status_code": 200
    }
    CREATED = {
        "code": "CREATED",
        "message": "资源创建成功",
        "status_code": 201
    }
    ACCEPTED = {
        "code": "ACCEPTED",
        "message": "请求已被接受，正在处理中",
        "status_code": 202
    }


class ErrorCode:
    """
    一个用于集中管理 API 错误码和描述的类 (重构版)。
    """
    # =================================================================
    # 1. 通用和请求错误 (Generic & Request Errors) - 4xx
    # =================================================================
    BAD_REQUEST = {
        "code": "BAD_REQUEST",
        "message": "请求格式错误或无效。",
        "status_code": 400
    }
    VALIDATION_ERROR = {
        "code": "VALIDATION_ERROR",
        "message": "一个或多个字段未能通过验证。", # 通常配合details字段返回具体错误
        "status_code": 400
    }
    # 关键修改：统一了占位符为 '{name}'，更通用
    MISSING_REQUIRED_FIELD = {
        "code": "MISSING_REQUIRED_FIELD",
        "message": "请求体中缺少必需的字段：'{name}'。",
        "status_code": 400
    }
    MISSING_REQUIRED_HEADER = {
        "code": "MISSING_REQUIRED_HEADER",
        "message": "请求中缺少必需的请求头：'{name}'。",
        "status_code": 400
    }
    FIELD_NAMING_INVALID = {
        "code": "FIELD_NAMING_INVALID",
        "message": "字段'{name}'的命名不规范或包含非法字符。",
        "status_code": 400
    }
    FIELD_TOO_LONG = {
        "code": "FIELD_TOO_LONG",
        "message": "字段'{name}'的长度超过了最大限制。",
        "status_code": 400
    }
    INVALID_INPUT_FORMAT = {
        "code": "INVALID_INPUT_FORMAT",
        "message": "输入数据的格式无效。(例如：无效的JSON)",
        "status_code": 400
    }
    INVALID_EMAIL = {
        "code": "INVALID_EMAIL",
        "message": "电子邮件地址格式无效。",
        "status_code": 400
    }
    INVALID_PASSWORD = {
        "code": "INVALID_PASSWORD",
        "message": "密码不符合要求（例如：长度、复杂度）。",
        "status_code": 400
    }
    UNSUPPORTED_MEDIA_TYPE = {
        "code": "UNSUPPORTED_MEDIA_TYPE",
        "message": "不支持所提供的媒体类型。",
        "status_code": 415
    }

    # =================================================================
    # 2. 认证与授权错误 (Authentication & Authorization Errors) - 401, 403
    # =================================================================
    AUTHENTICATION_REQUIRED = {
        "code": "AUTHENTICATION_REQUIRED",
        "message": "访问此资源需要提供认证凭据。",
        "status_code": 401
    }
    INVALID_CREDENTIALS = {
        "code": "INVALID_CREDENTIALS",
        "message": "提供的凭据无效（例如：用户名或密码错误）。",
        "status_code": 401
    }
    INVALID_TOKEN = {
        "code": "INVALID_TOKEN",
        "message": "提供的认证令牌无效、格式错误或已过期。",
        "status_code": 401
    }
    TOKEN_EXPIRED = {
        "code": "TOKEN_EXPIRED",
        "message": "认证令牌已过期。",
        "status_code": 401
    }
    ACCOUNT_INACTIVE = {
        "code": "ACCOUNT_INACTIVE",
        "message": "用户账户未激活或已被禁用。",
        "status_code": 401
    }
    PERMISSION_DENIED = {
        "code": "PERMISSION_DENIED",
        "message": "您没有权限执行此操作。",
        "status_code": 403
    }
    INSUFFICIENT_SCOPE = {
        "code": "INSUFFICIENT_SCOPE",
        "message": "令牌的权限范围不足以执行此操作。",
        "status_code": 403
    }

    # =================================================================
    # 4. 资源相关错误 (Resource Errors) - 404, 409
    # =================================================================
    RESOURCE_NOT_FOUND = {
        "code": "RESOURCE_NOT_FOUND",
        "message": "请求的资源未找到。",
        "status_code": 404
    }
    USER_NOT_FOUND = {
        "code": "USER_NOT_FOUND",
        "message": "未找到具有指定标识符的用户。",
        "status_code": 404
    }
    DUPLICATE_RESOURCE = {
        "code": "DUPLICATE_RESOURCE",
        "message": "具有相同标识符的资源已存在。",
        "status_code": 409
    }
    EMAIL_ALREADY_EXISTS = {
        "code": "EMAIL_ALREADY_EXISTS",
        "message": "使用此电子邮件地址的用户已存在。",
        "status_code": 409
    }
    INVALID_STATE_TRANSITION = {
        "code": "INVALID_STATE_TRANSITION",
        "message": "不允许对处于当前状态的资源执行所请求的操作。",
        "status_code": 409
    }

    # =================================================================
    # 5. 服务端错误 (Server Errors) - 5xx
    # =================================================================
    UNEXPECTED_ERROR = {
        "code": "UNEXPECTED_ERROR",
        "message": "服务器发生意外错误。",
        "status_code": 500
    }
    DATABASE_ERROR = {
        "code": "DATABASE_ERROR",
        "message": "处理请求时发生数据库错误。",
        "status_code": 500
    }
    EXTERNAL_SERVICE_UNAVAILABLE = {
        "code": "EXTERNAL_SERVICE_UNAVAILABLE",
        "message": "此操作所需的外部服务当前不可用。",
        "status_code": 503
    }

    # =================================================================
    # 6. 速率限制错误 (Rate Limiting Errors) - 429
    # =================================================================
    RATE_LIMIT_EXCEEDED = {
        "code": "RATE_LIMIT_EXCEEDED",
        "message": "您已超出请求速率限制。",
        "status_code": 429
    }