from typing import Optional, List
from sqlalchemy import Integer, String, text, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass


class Users(Base):
    __tablename__ = 'users'
    __table_args__ = (
        Index('email', 'email', unique=True),
        Index('ix_users_id', 'id')
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)

class Base(DeclarativeBase):
    pass


class Items(Base):
    __tablename__ = 'items'

    iditems: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(String(45), server_default=text("'菜鸟'"))
    discription: Mapped[Optional[str]] = mapped_column(String(45))
    level: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("'0'"))

