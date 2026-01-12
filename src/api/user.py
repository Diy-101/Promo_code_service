from typing import Annotated

from fastapi import (
    APIRouter,
    Body,
    Depends,
    HTTPException,
    Path,
    Query,
    Response,
    status,
)
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from schemas.user import (
    CommentGet,
    PromoFilterQueryParams,
    PromoForUser,
    Token,
    User,
    UserPatch,
    UserRegister,
    UserSignIn,
)
from services.user_service import UserService
from utils.auth import AccessTokenUserBearer

user_router = APIRouter(prefix="/user")
user_service = UserService()


@user_router.post("/auth/sign-up")
async def sign_up_user(data: UserRegister, db: AsyncSession = Depends(get_db)) -> Token:
    return await user_service.user_sign_up(user=data, db=db)


@user_router.post("/auth/sign-in")
async def sign_in_user(data: UserSignIn, db: AsyncSession = Depends(get_db)):
    return await user_service.user_sign_in(data=data, db=db)


@user_router.get("/profile")
async def get_user_profile(
    credentials: HTTPAuthorizationCredentials = Depends(
        AccessTokenUserBearer(auto_error=True)
    ),
    db: AsyncSession = Depends(get_db),
) -> User:
    user_id = user_service.get_user_uuid_from_token(credentials.credentials)
    return await user_service.get_user_profile(user_id=user_id, session=db)


@user_router.patch("/profile")
async def patch_user_profile(
    data: UserPatch,
    credentials: HTTPAuthorizationCredentials = Depends(
        AccessTokenUserBearer(auto_error=True)
    ),
    db: AsyncSession = Depends(get_db),
) -> User:
    user_id = user_service.get_user_uuid_from_token(credentials.credentials)
    return await user_service.patch_user_profile(data=data, user_id=user_id, session=db)


@user_router.get("/feed")
async def get_promos(
    response: Response,
    filters: Annotated[PromoFilterQueryParams, Query()],
    credentials: HTTPAuthorizationCredentials = Depends(
        AccessTokenUserBearer(auto_error=True)
    ),
    db: AsyncSession = Depends(get_db),
):
    user_id = user_service.get_user_uuid_from_token(credentials.credentials)

    if await user_service.is_exist_in_db(user_id, db):
        list_promos_dto, n_promos = await user_service.get_promos(
            filters=filters, session=db
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "status": "error",
                "message": "Пользователь не авторизован.",
            },
        )


@user_router.get("/promo/{id}")
async def get_promo(
    id: str = Path(...),
    credentials: HTTPAuthorizationCredentials = Depends(
        AccessTokenUserBearer(auto_error=True)
    ),
    db: AsyncSession = Depends(get_db),
) -> PromoForUser:
    user_id = user_service.get_user_uuid_from_token(credentials.credentials)

    if await user_service.is_exist_in_db(user_id, db):
        return await user_service.get_promo(user_id=user_id, promo_id=id, session=db)
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "status": "error",
                "message": "Пользователь не авторизован.",
            },
        )


@user_router.post("/promo/{id}/like")
async def like_promo(
    id: str = Path(...),
    credentials: HTTPAuthorizationCredentials = Depends(
        AccessTokenUserBearer(auto_error=True)
    ),
    db: AsyncSession = Depends(get_db),
):
    user_id = user_service.get_user_uuid_from_token(credentials.credentials)
    if await user_service.is_exist_in_db(user_id, db=db):
        await user_service.like_promo(user_id=user_id, promo_id=id, session=db)
        return {"status": "ok"}
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "status": "error",
                "message": "Пользователь не авторизован.",
            },
        )


@user_router.delete("/promo/{id}/like")
async def unlike_promo(
    id: str = Path(...),
    credentials: HTTPAuthorizationCredentials = Depends(
        AccessTokenUserBearer(auto_error=True)
    ),
    db: AsyncSession = Depends(get_db),
):
    user_id = user_service.get_user_uuid_from_token(credentials.credentials)
    if await user_service.is_exist_in_db(user_id, db=db):
        await user_service.unlike_promo(user_id=user_id, promo_id=id, session=db)
        return {"status": "ok"}
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "status": "error",
                "message": "Пользователь не авторизован.",
            },
        )


@user_router.post("/promo/{id}/comments")
async def add_comment(
    text: str = Body(..., embed=True),
    id: str = Path(...),
    credentials: HTTPAuthorizationCredentials = Depends(
        AccessTokenUserBearer(auto_error=True)
    ),
    db: AsyncSession = Depends(get_db),
) -> CommentGet:
    user_id = user_service.get_user_uuid_from_token(credentials.credentials)
    if await user_service.is_exist_in_db(user_id, db=db):
        return await user_service.add_comment(
            text=text, user_id=user_id, promo_id=id, session=db
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "status": "error",
                "message": "Пользователь не авторизован.",
            },
        )


@user_router.get("/promo/{id}/comments")
async def get_comments(
    id: str = Path(...),
    limit: int = Query(default=10),
    offset: int = Query(default=0),
    credentials: HTTPAuthorizationCredentials = Depends(
        AccessTokenUserBearer(auto_error=True)
    ),
    db: AsyncSession = Depends(get_db),
) -> list[CommentGet]:
    user_id = user_service.get_user_uuid_from_token(credentials.credentials)
    if await user_service.is_exist_in_db(user_id, db=db):
        return await user_service.get_comments_for_promo(
            promo_id=id, session=db, limit=limit, offset=offset
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "status": "error",
                "message": "Пользователь не авторизован.",
            },
        )


@user_router.get("/promo/{id}/comments/{comment_id}")
async def get_comment(
    id: str = Path(...),
    comment_id: str = Path(...),
    credentials: HTTPAuthorizationCredentials = Depends(
        AccessTokenUserBearer(auto_error=True)
    ),
    db: AsyncSession = Depends(get_db),
) -> CommentGet:
    user_id = user_service.get_user_uuid_from_token(credentials.credentials)
    if await user_service.is_exist_in_db(user_id, db=db):
        return await user_service.get_comment_for_promo(
            comment_id=comment_id,
            promo_id=id,
            session=db,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "status": "error",
                "message": "Пользователь не авторизован.",
            },
        )


@user_router.put("/promo/{id}/comments/{comment_id}")
async def put_comment(
    id: str = Path(...),
    text: str = Body(..., embed=True),
    comment_id: str = Path(...),
    credentials: HTTPAuthorizationCredentials = Depends(
        AccessTokenUserBearer(auto_error=True)
    ),
    db: AsyncSession = Depends(get_db),
) -> CommentGet:
    user_id = user_service.get_user_uuid_from_token(credentials.credentials)
    if await user_service.is_exist_in_db(user_id, db=db):
        return await user_service.put_comment(
            text=text,
            comment_id=comment_id,
            promo_id=id,
            session=db,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "status": "error",
                "message": "Пользователь не авторизован.",
            },
        )


@user_router.delete("/promo/{id}/comments/{comment_id}")
async def delete_comment(
    id: str = Path(...),
    comment_id: str = Path(...),
    credentials: HTTPAuthorizationCredentials = Depends(
        AccessTokenUserBearer(auto_error=True)
    ),
    db: AsyncSession = Depends(get_db),
):
    user_id = user_service.get_user_uuid_from_token(credentials.credentials)
    if await user_service.is_exist_in_db(user_id, db=db):
        return await user_service.delete_comment(
            user_id=user_id,
            comment_id=comment_id,
            promo_id=id,
            session=db,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "status": "error",
                "message": "Пользователь не авторизован.",
            },
        )
