# schemas.py (已更正)
from pydantic import BaseModel, ConfigDict
from typing import Optional,List
# 用于创建的 Schema
# 必须包含所有数据库中 "nullable=False" 且没有默认值的字段
# 专门用于创建新用户的场景
class UserCreate(BaseModel):
    name: str
    email: str  # 必须改为必填项 (移除 | None)
    password: str # 必须添加 password 字段

# 用于更新的 Schema (所有字段可选)
# 这个模式是 OK 的，它只允许更新 name 和 email
# | None = None 意味着 name 字段是可选的
class UserUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    # 注意：这里没有包含 password，意味着您的 /users/{id} PATCH 路由
    # 不会用于修改密码，这通常是好的安全实践（密码重置应走单独的路由）

# 用于读取/返回的 Schema (这个是正确的，无需修改)
class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str

class UserResponse(BaseModel):
    data: List[UserRead]
    total_count: int

# --- (新) 添加 Items 相关的 Pydantic 模式 ---
class ItemBase(BaseModel):
    """Items 共享的基础字段"""
    # 我们遵循你 model 的定义：所有字段都是可选的
    # 并使用 model 中的 server_default 值作为 Pydantic 的默认值
    name: Optional[str] = '菜鸟'
    discription: Optional[str] = None  # 必须匹配你数据库中的拼写错误
    level: Optional[int] = 0


class ItemCreate(ItemBase):
    """用于创建 Item"""
    # 因为所有字段都有默认值或是可选的，所以 create 模式不需要额外字段
    pass


class ItemUpdate(BaseModel):
    """用于更新 Item (所有字段都必须是 Optional)"""
    name: Optional[str] = None
    discription: Optional[str] = None
    level: Optional[int] = None


class ItemRead(ItemBase):
    """用于从 API 读取/返回 Item"""
    # 必须匹配你的主键名 'iditems'
    iditems: int

    # 保持不变：允许从 SQLAlchemy 对象模型转换
    model_config = ConfigDict(from_attributes=True)

class ItemsResponse(BaseModel):
    data: List[ItemRead]
    total_count: int