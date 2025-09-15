from typing import Optional, List
from sqlalchemy import Integer, String, text, Index, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# --- (修正 1) Base 类只应被定义一次 ---
# 所有的模型都将继承自这一个 Base 类。
class Base(DeclarativeBase):
    pass


class Users(Base):
    __tablename__ = 'users'
    __table_args__ = (
        Index('email', 'email', unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)

    # (建议) 添加反向关联，方便通过 user.items 访问其拥有的所有物品记录
    user_items: Mapped[List["Useritems"]] = relationship(back_populates="user")


class Items(Base):
    __tablename__ = 'items'

    iditems: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(String(45), server_default=text("'菜鸟'"))
    description: Mapped[Optional[str]] = mapped_column(String(45))
    level: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("'0'"))

    # (建议) 添加反向关联
    user_items: Mapped[List["Useritems"]] = relationship(back_populates="item")


# --- (新增) User-Item 关联表的模型 ---
class Useritems(Base):
    __tablename__ = 'user_items'

    # 路由文件中使用的 CRUD 方法依赖主键名为 'id'
    id: Mapped[int] = mapped_column(primary_key=True)

    # 外键，关联到 users 表的 id 字段
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    # 外键，关联到 items 表的 iditems 字段
    item_id: Mapped[int] = mapped_column(ForeignKey("items.iditems"))

    # 附加信息，例如用户拥有该物品的数量
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # (建议) 定义与 Users 和 Items 模型的直接关联
    # 方便通过 orm 对象 user_item.user 或 user_item.item 直接访问关联的 User 和 Item
    user: Mapped["Users"] = relationship(back_populates="user_items")
    item: Mapped["Items"] = relationship(back_populates="user_items")
