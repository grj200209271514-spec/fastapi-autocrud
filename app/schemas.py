from pydantic import BaseModel, ConfigDict
from typing import Optional, List

# --- User Schemas ---
class UserCreate(BaseModel):
    name: str
    email: str
    password: str

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None

class UserRead(BaseModel):
    # (关键修复 2) 使用 model_config 替代 class Config
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: str

class UserResponse(BaseModel):
    data: List[UserRead]
    total_count: int

# --- Item Schemas ---
class ItemBase(BaseModel):
    name: Optional[str] = '菜鸟'
    description: Optional[str] = None
    level: Optional[int] = 0

class ItemCreate(ItemBase):
    pass

class ItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    level: Optional[int] = None

class ItemRead(ItemBase):
    iditems: int
    model_config = ConfigDict(from_attributes=True)

class ItemsResponse(BaseModel):
    data: List[ItemRead]
    total_count: int

# --- Useritems Schemas ---
class UseritemsBase(BaseModel):
    user_id: int
    item_id: int
    quantity: int = 1

class UseritemsCreate(UseritemsBase):
    pass

class UseritemsUpdate(BaseModel):
    user_id: Optional[int] = None
    item_id: Optional[int] = None
    quantity: Optional[int] = None

class UseritemsRead(UseritemsBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class UseritemssResponse(BaseModel):
    data: List[UseritemsRead]
    total_count: int