import re
from datetime import date
from typing import Annotated, Literal, Self

from email_validator import EmailNotValidError, validate_email
from fastapi import HTTPException, status
from pydantic import (
    AfterValidator,
    BaseModel,
    Field,
    field_validator,
    model_validator,
)
from pydantic_extra_types.country import CountryAlpha2

# Validators
password_pattern = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"
)
httpurl_pattern = re.compile(r"^https?://[^\s/$.?#].[^\s]*$")


def val_email(v: str) -> str:
    try:
        info = validate_email(v, check_deliverability=True)
    except EmailNotValidError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"status": "error", "message": "Ошибка в данных запроса."},
        )

    email = info.normalized

    if not 5 <= len(email) <= 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"status": "error", "message": "Ошибка в данных запроса."},
        )

    return email


def val_password(v: str) -> str:
    if not (password_pattern.match(v) and len(v) <= 60 and len(v) >= 8):
        HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"status": "error", "message": "Ошибка в данных запроса."},
        )
    return v


def val_httpurl(v: str) -> str:
    if not httpurl_pattern.match(v) and len(v) > 350:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"status": "error", "message": "Ошибка в данных запроса."},
        )
    return v


# Base models and types
Category = Annotated[str, Field(min_length=2, max_length=20)]
UniquePromoCode = Annotated[str, Field(min_length=3, max_length=30)]
Country = Annotated[CountryAlpha2, Field(description="ISO 3166-1 alpha-2 country code")]
HttpUrlRegex = Annotated[str, AfterValidator(val_httpurl)]


class Target(BaseModel):
    age_from: int | None = Field(
        default=None,
        ge=0,
        le=100,
        examples=["14"],
        description="Минимальный возраст целевой аудитории (включительно). Не должен превышать age_until.",
    )
    age_until: int | None = Field(
        default=None,
        ge=0,
        le=100,
        examples=["35"],
        description="Максимальный возраст целевой аудитории (включительно).",
    )
    country: Country | None = Field(
        default=None,
        examples=["ru"],
        description="Страна пользователя в формате ISO 3166-1 alpha-2, регистр может быть разным. Страна с данным кодом должна обязательно существовать.",
    )
    categories: list[Category] | None = Field(
        default=None, max_length=20, description="Список категорий интересов."
    )

    @field_validator("country", mode="before")
    def convert_country(cls, v: str) -> str:
        if isinstance(v, str):
            return v.upper()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Country code must be a string",
        )


# Request and Response Models
class CompanySignUpRequest(BaseModel):
    name: Annotated[str, Field(min_length=5, max_length=50)]
    email: Annotated[str, AfterValidator(val_email)]
    password: Annotated[str, AfterValidator(val_password)]


class CompanySignUpResponse(BaseModel):
    token: str
    company_id: str  # UUID


class CompanyDTO(CompanySignUpRequest):
    id: str
    password: str


class CompanySignInRequest(BaseModel):
    email: Annotated[str, AfterValidator(val_email)]
    password: Annotated[str, AfterValidator(val_password)]


class CompanySignInResponse(BaseModel):
    token: str


class PromoCreateRequest(BaseModel):
    description: Annotated[str, Field(min_length=10, max_length=300)]
    image_url: Annotated[HttpUrlRegex | None, Field(max_length=350)] = None
    target: Target | None = None
    max_count: Annotated[int, Field(gt=0, le=100000000)]
    active_from: date | None = None
    active_until: date | None = None
    mode: Literal["COMMON", "UNIQUE"]
    promo_common: Annotated[
        str | None, Field(min_length=5, max_length=30, examples=["sale-10"])
    ] = None
    promo_unique: Annotated[
        list[UniquePromoCode] | None,
        Field(
            min_length=1,
            max_length=5000,
            examples=[
                'List [ "winter-sale-30-abc28f99qa", "winter-sale-30-299faab2c", "sale-100-winner" ]'
            ],
        ),
    ] = None

    @model_validator(mode="after")
    def check_promo_codes(self) -> Self:
        if self.mode == "COMMON":
            if not self.promo_common:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="promo_common must be provided for COMMON mode",
                )
            if self.promo_unique:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "status": "error",
                        "message": "Некорректные данные запроса",
                    },
                )
        elif self.mode == "UNIQUE":
            if not self.max_count != 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Некорректные данные запроса",
                )
            if not self.promo_unique:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "status": "error",
                        "message": "Некорректные данные запроса",
                    },
                )
            if self.promo_common:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "status": "error",
                        "message": "Некорректные данные запроса",
                    },
                )
        if self.active_from is not None and self.active_until is not None:
            if self.active_from >= self.active_until:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "status": "error",
                        "message": "active_from should be less then active_until",
                    },
                )
        return self


class PromoCreateResponse(BaseModel):
    id: str


class PromoFilterQueryParams(BaseModel):
    limit: Annotated[int, Field(10)]
    offset: Annotated[int, Field(0)]
    sort_by: Literal["active_from", "active_until"] | None = None
    country: list[Country] | None = None


class PromoPatch(BaseModel):
    description: Annotated[str | None, Field(None, min_length=10, max_length=300)]
    image_url: Annotated[HttpUrlRegex | None, Field(None, max_length=350)] = None
    target: Target | None = None
    max_count: Annotated[int, Field(None, gt=0, le=100000000)]
    active_from: date | None = None
    active_until: date | None = None

    @model_validator(mode="after")
    def check_data(self) -> Self:
        if self.active_from is not None and self.active_until is not None:
            if self.active_from > self.active_until:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "status": "error",
                        "message": "active_from should be less then active_until",
                    },
                )
        return self


class PromoDTO(BaseModel):
    id: str
    company_id: str
    description: Annotated[str, Field(min_length=10, max_length=300)]
    image_url: Annotated[HttpUrlRegex | None, Field(max_length=350)] = None
    target: Target | None = None
    max_count: Annotated[int, Field(gt=0, le=100000000)]
    active_from: date | None = None
    active_until: date | None = None
    mode: Literal["COMMON", "UNIQUE"]
    active: bool
    like_count: int
    used_count: int

    promo_common: Annotated[
        str | None, Field(min_length=5, max_length=30, examples=["sale-10"])
    ] = None
    promo_unique: Annotated[
        list[UniquePromoCode] | None,
        Field(
            min_length=1,
            max_length=5000,
            examples=[
                'List [ "winter-sale-30-abc28f99qa", "winter-sale-30-299faab2c", "sale-100-winner" ]'
            ],
        ),
    ] = None


class CountryStat(BaseModel):
    country: Country
    activations_count: Annotated[int, Field(..., ge=1)]


class PromoStat(BaseModel):
    activations_count: Annotated[
        int,
        Field(..., ge=0),
    ]
    countries: list[CountryStat]
