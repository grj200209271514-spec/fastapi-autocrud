from pydantic import BaseModel, Field
from typing import TypeVar, Generic, Optional, Any

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

    # 关键修改：新增一个可选的 meta 字段，用于存放分页等元数据
    meta: Optional[dict] = Field(None, description="额外的元数据，例如用于分页。")


def Success(
        data: Any = None,
        message: str = "操作成功。",
        # 关键修改：为 Success 辅助函数增加 meta 参数
        meta: Optional[dict] = None
) -> StandardResponse:
    """
    创建一个标准的成功响应。
    """
    return StandardResponse(
        code="OK",
        message=message,
        data=data,
        meta=meta
    )