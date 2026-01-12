from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field

from schemas.business import Country, val_email, val_httpurl, val_password


class Token(BaseModel):
    token: str


class UserTargetSettings(BaseModel):
    age: Annotated[int, Field(ge=0, le=100)]
    country: Country


class User(BaseModel):
    name: Annotated[str, Field(..., min_length=1, max_length=100)]
    surname: Annotated[
        str,
        Field(..., min_length=1, max_length=120),
    ]
    email: Annotated[str, AfterValidator(val_email)]
    avatar_url: Annotated[str | None, AfterValidator(val_httpurl)] = None
    other: Annotated[UserTargetSettings, Field(...)]


class UserRegister(User):
    password: Annotated[str, AfterValidator(val_password)]


class UserSignIn(BaseModel):
    email: Annotated[str, AfterValidator(val_email)]
    password: Annotated[str, AfterValidator(val_password)]


class UserPatch(BaseModel):
    name: Annotated[str | None, Field(None, min_length=1, max_length=100)]
    surname: Annotated[
        str | None,
        Field(None, min_length=1, max_length=120),
    ]
    avatar_url: Annotated[str | None, AfterValidator(val_httpurl)] = None
    password: Annotated[str | None, AfterValidator(val_password)] = None


class PromoFilterQueryParams(BaseModel):
    limit: Annotated[int, Field(10)]
    offset: Annotated[int, Field(0)]
    category: str | None = None
    active: bool | None = None


class PromoForUser(BaseModel):
    promo_id: Annotated[str, Field(...)]
    company_id: Annotated[str, Field(...)]
    company_name: Annotated[str, Field(...)]
    description: Annotated[str, Field(...)]
    image_url: Annotated[str | None, Field(None)]
    active: Annotated[bool, Field(...)]
    is_activated_by_user: Annotated[bool, Field(...)]
    like_count: Annotated[int, Field(...)]
    is_liked_by_user: Annotated[bool, Field(...)]
    comment_count: Annotated[int, Field(...)]


class CommentAuthor(BaseModel):
    name: str
    surname: str
    avatar_url: str | None = None


class CommentGet(BaseModel):
    id: str
    text: Annotated[str, Field(min_length=10, max_length=1000)]
    date: datetime
    author: CommentAuthor
