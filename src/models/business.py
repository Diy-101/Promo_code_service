import enum
from datetime import date

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    Enum,
    ForeignKey,
    Integer,
    String,
    Table,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from models.user import CommentORM, UserORM

promotion_category_m2m = Table(
    "promotion_category",
    Base.metadata,
    Column("promo_id", ForeignKey("promos.id"), primary_key=True),
    Column("category_id", ForeignKey("categories.id"), primary_key=True),
)

promotion_country_m2m = Table(
    "promotion_countries",
    Base.metadata,
    Column("promo_id", ForeignKey("promos.id"), primary_key=True),
    Column("country_id", ForeignKey("countries.id"), primary_key=True),
)


class PromoUserORM(Base):
    __tablename__ = "users_promos"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    promo_id: Mapped[str] = mapped_column(
        ForeignKey("promos.id", ondelete="CASCADE"),
        primary_key=True,
    )

    activated: Mapped[bool] = mapped_column(server_default="false", nullable=False)
    liked: Mapped[bool] = mapped_column(server_default="false", nullable=False)

    user: Mapped["UserORM"] = relationship(back_populates="user_promos")
    promo: Mapped["PromocodeORM"] = relationship(back_populates="user_promos")


class PromoMode(str, enum.Enum):
    COMMON = "COMMON"
    UNIQUE = "UNIQUE"


class CompanyORM(Base):
    __tablename__ = "companies"

    # SQL
    id: Mapped[str] = mapped_column(
        primary_key=True, index=True, server_default=func.gen_random_uuid()
    )
    name: Mapped[str] = mapped_column(String(50))
    email: Mapped[str] = mapped_column(String(50), index=True, unique=True)
    password: Mapped[str]

    # Связи
    promos: Mapped[list["PromocodeORM"]] = relationship(back_populates="company")


class PromocodeORM(Base):
    __tablename__ = "promos"

    # Основные поля
    id: Mapped[str] = mapped_column(
        primary_key=True, index=True, server_default=func.gen_random_uuid()
    )
    company_id: Mapped[str] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE")
    )
    description: Mapped[str] = mapped_column(String(200))
    image_url: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Таргет
    age_from: Mapped[int | None] = mapped_column(Integer, nullable=True)
    age_until: Mapped[int | None] = mapped_column(Integer, nullable=True)
    country: Mapped[str] = mapped_column(String(2))

    # Даты и лимиты
    active_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    active_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    max_count: Mapped[int] = mapped_column(Integer, default=1)

    # Мод, активность и лайки
    mode: Mapped[PromoMode] = mapped_column(Enum(PromoMode))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    like_count: Mapped[int] = mapped_column(default=0)
    used_count: Mapped[int] = mapped_column(default=0)

    # Общий промокод
    promo_common: Mapped[str] = mapped_column(String, nullable=True)

    # Связи
    unique_promos: Mapped[list["UniquePromocodeORM"]] = relationship(
        back_populates="main_promo", cascade="all, delete-orphan"
    )
    categories: Mapped[list["CategoryORM"]] = relationship(
        back_populates="promos", secondary=promotion_category_m2m
    )
    company: Mapped["CompanyORM"] = relationship(back_populates="promos", cascade="all")
    countries: Mapped[list["CountryActivation"]] = relationship(
        back_populates="promos", secondary=promotion_country_m2m
    )
    user_promos: Mapped[list["PromoUserORM"]] = relationship(back_populates="promo")
    comments: Mapped[list["CommentORM"]] = relationship(back_populates="promo")


class CategoryORM(Base):
    __tablename__ = "categories"

    # SQL
    id: Mapped[str] = mapped_column(
        primary_key=True, index=True, server_default=func.gen_random_uuid()
    )
    name: Mapped[str] = mapped_column(String(100))

    # Связи
    promos: Mapped[list["PromocodeORM"]] = relationship(
        back_populates="categories", secondary=promotion_category_m2m
    )


class UniquePromocodeORM(Base):
    __tablename__ = "unique_promos"

    id: Mapped[str] = mapped_column(
        primary_key=True, index=True, server_default=func.gen_random_uuid()
    )
    promocode: Mapped[str]
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    code_id: Mapped[str] = mapped_column(ForeignKey("promos.id", ondelete="CASCADE"))

    # Связи
    main_promo: Mapped["PromocodeORM"] = relationship(back_populates="unique_promos")


class CountryActivation(Base):
    __tablename__ = "countries"

    id: Mapped[str] = mapped_column(
        primary_key=True, index=True, server_default=func.gen_random_uuid()
    )
    name: Mapped[str] = mapped_column(unique=True)
    activation: Mapped[int]

    # Связи
    promos: Mapped[list["PromocodeORM"]] = relationship(
        back_populates="countries", secondary=promotion_country_m2m
    )
