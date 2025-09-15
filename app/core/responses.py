from pydantic import BaseModel, Field
from typing import TypeVar, Generic, Optional, Any
from fastapi.responses import JSONResponse

# 使用 TypeVar 来定义一个泛型数据类型
T = TypeVar('T')


class PaginationMeta(BaseModel):
    """
    用于分页的元数据模型。
    """
    total_items: int = Field(..., description="可用条目的总数。")
    total_pages: int = Field(..., description="总页数。")
    current_page: int = Field(..., description="当前页码 (从1开始)。")
    page_size: int = Field(..., description="每页的条目数。")


class StandardResponse(BaseModel, Generic[T]):
    """
    标准的 API 响应模型，现在支持可选的分页元数据。
    """
    code: str = Field("OK", description="业务状态码。")
    message: str = Field("操作成功。", description="人类可读的消息。")
    data: Optional[T] = Field(None, description="业务数据负载。")
    meta: Optional[dict] = Field(None, description="额外的元数据，例如用于分页。")


def Success(
        data: Any = None,
        message: str = "操作成功。",
        meta: Optional[dict] = None
) -> StandardResponse:
    """
    创建一个标准的成功响应。
    返回的是一个 Pydantic 模型实例，FastAPI 会默认用 200 OK 状态码包装它。
    """
    return StandardResponse(
        code="OK",
        message=message,
        data=data,
        meta=meta
    )


# --- (新增) Fail 辅助函数 ---
def Fail(
        message: str = "操作失败。",
        code: str = "FAIL",
        status_code: int = 400  # 默认使用 400 Bad Request
) -> JSONResponse:
    """
    创建一个标准的失败响应。
    重要的是，它直接返回一个 FastAPI 的 JSONResponse 对象，
    这允许我们自定义 HTTP 状态码 (如 400, 404, 500)。
    """
    # 构造响应体，确保其结构与 StandardResponse 一致
    response_body = StandardResponse(
        code=code,
        message=message,
        data=None,  # 失败响应通常不包含 data
        meta=None
    )

    # 使用 model_dump 转换为字典，并排除值为 None 的字段
    content = response_body.model_dump(exclude_none=True)

    return JSONResponse(
        status_code=status_code,
        content=content
    )
