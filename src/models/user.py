from datetime import datetime

from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class UserORM(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        primary_key=True, index=True, server_default=func.gen_random_uuid()
    )
    name: Mapped[str]
    surname: Mapped[str]
    email: Mapped[str]
    password: Mapped[str]
    avatar_url: Mapped[str]

    other: Mapped["UserTargetORM"] = relationship(back_populates="user")
    user_promos: Mapped[list["PromoUserORM"]] = relationship(back_populates="user")
    comments: Mapped[list["CommentORM"]] = relationship(back_populates="user")


class UserTargetORM(Base):
    __tablename__ = "users_targets"

    id: Mapped[str] = mapped_column(
        primary_key=True, index=True, server_default=func.gen_random_uuid()
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    age: Mapped[int | None] = mapped_column(nullable=True)
    country: Mapped[str | None] = mapped_column(nullable=True)

    user: Mapped["UserORM"] = relationship(back_populates="other")


class CommentORM(Base):
    __tablename__ = "comments"

    id: Mapped[str] = mapped_column(
        primary_key=True, index=True, server_default=func.gen_random_uuid()
    )
    text: Mapped[str]
    date: Mapped[datetime] = mapped_column(server_default=func.current_timestamp())
    author: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    promo_id: Mapped[str] = mapped_column(ForeignKey("promos.id", ondelete="CASCADE"))

    user: Mapped["UserORM"] = relationship(back_populates="comments")
    promo: Mapped["PromocodeORM"] = relationship(back_populates="comments")
