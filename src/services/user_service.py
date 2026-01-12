from datetime import datetime, timedelta
from uuid import uuid4

import jwt
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config import get_config
from models.business import PromocodeORM, PromoUserORM
from models.user import CommentORM, UserORM, UserTargetORM
from schemas.user import (
    CommentAuthor,
    CommentGet,
    PromoFilterQueryParams,
    PromoForUser,
    Token,
    User,
    UserPatch,
    UserRegister,
    UserSignIn,
)
from utils.general import hash_password, verify_password
from utils.logger import logger
from utils.whitelist import TokenWhiteList

cfg = get_config()
whitelist = TokenWhiteList()


class UserService:
    def __call__(self):
        return self

    def create_access_token(self, id: str, is_refresh: bool = False) -> tuple:
        """
        Создание access token
        """
        token_uuid = str(uuid4())
        payload = {
            "id": id,
            "jti": token_uuid,
            "exp": datetime.now() + timedelta(hours=24),
            "refresh": is_refresh,
        }

        try:
            token = jwt.encode(
                payload=payload, key=cfg.JWT_SECRET, algorithm=cfg.JWT_ALGORITHM
            )
            return (token_uuid, token)
        except jwt.PyJWKError as error:
            logger.error(f"Error during creating JWT token: {error}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error during creating JWT token: {error}",
            )

    def get_user_uuid_from_token(self, token: str) -> str:
        """
        Получение компании из Токена
        """
        try:
            token_data = jwt.decode(
                jwt=token, key=cfg.JWT_SECRET, algorithms=[cfg.JWT_ALGORITHM]
            )
            return token_data["id"]
        except jwt.PyJWTError as e:
            logger.error(f"Error during decode token {e}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

    async def is_exist_in_db(self, id: str, db: AsyncSession) -> bool:
        async with db as session:
            result = (
                await session.execute(select(UserORM).where(UserORM.id == id))
            ).scalar_one_or_none()
        return False if result is None else True

    async def user_sign_up(self, user: UserRegister, db: AsyncSession):
        async with db as session:
            query = select(UserORM).where(UserORM.email == user.email)
            result_orm = (await session.execute(query)).scalar_one_or_none()
            if result_orm is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "status": "error",
                        "message": "Такой email уже зарегистрирован.",
                    },
                )

            hashed_password = await hash_password(user.password)

            other_orm = UserTargetORM(**user.other.model_dump())

            model = UserORM(
                **user.model_dump(mode="json", exclude=("password", "other")),  # type: ignore
                password=hashed_password,
            )

            model.other = other_orm

            session.add(model)
            await session.commit()
            await session.refresh(model)
        token_id, token = self.create_access_token(model.id)
        await whitelist.add_jti_to_whitelist(model.id, token_id, entity="user")
        return Token(token=token)

    async def user_sign_in(self, data: UserSignIn, db: AsyncSession):
        async with db as session:
            query = select(UserORM).where(UserORM.email == data.email)
            result_orm = (await session.execute(query)).scalar_one_or_none()
            if result_orm is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={"status": "error", "message": "Неверный email или пароль."},
                )

            password_verivied = await verify_password(
                data.password, result_orm.password
            )

            if not password_verivied:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={"status": "error", "message": "Неверный email или пароль."},
                )

            new_token_jti, new_token = self.create_access_token(result_orm.id)
            await whitelist.flush_all_jti_from_whitelist(result_orm.id, entity="user")
            await whitelist.add_jti_to_whitelist(
                result_orm.id, new_token_jti, entity="user"
            )
            return Token(token=new_token)

    async def get_user_profile(self, user_id: str, session: AsyncSession) -> User:
        async with session as session:
            query = (
                select(UserORM)
                .where(UserORM.id == user_id)
                .options(selectinload(UserORM.other))
            )
            user_orm = (await session.execute(query)).scalar_one_or_none()
            if user_orm is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={
                        "status": "error",
                        "message": "Пользователь не авторизован.",
                    },
                )

            user_dto = User.model_validate(
                user_orm, from_attributes=True, extra="ignore"
            )

            return user_dto

    async def patch_user_profile(
        self, data: UserPatch, user_id: str, session: AsyncSession
    ) -> User:
        async with session as session:
            query = (
                select(UserORM)
                .where(UserORM.id == user_id)
                .options(selectinload(UserORM.other))
            )

            user_orm = (await session.execute(query)).scalar_one_or_none()
            if user_orm is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={
                        "status": "error",
                        "message": "Пользователь не авторизован.",
                    },
                )

            for key, value in data.model_dump(exclude_none=True).items():
                if key == "password":
                    new_hashed_password = await hash_password(value)
                    setattr(user_orm, key, new_hashed_password)
                else:
                    setattr(user_orm, key, value)

            session.add(user_orm)
            await session.commit()
            await session.refresh(user_orm)

            user_dto = User.model_validate(
                user_orm, from_attributes=True, extra="ignore"
            )

            return user_dto

    async def get_promos(self, filters: PromoFilterQueryParams, session: AsyncSession):
        async with session as session:
            query = select
            # TODO дописать функцию
        return 2, 2

    async def get_promo(
        self, user_id: str, promo_id: str, session: AsyncSession
    ) -> PromoForUser:
        async with session as session:
            query = (
                select(
                    PromocodeORM, func.count(CommentORM.id).label("comments_count")
                )  # [(model_1, comments_count_1), (model_2, comments_count_2)]
                .outerjoin(
                    CommentORM,
                    CommentORM.promo_id == PromocodeORM.id,
                )
                .options(selectinload(PromocodeORM.comments))
                .options(selectinload(PromocodeORM.company))
                .where(PromocodeORM.id == promo_id)
                .group_by(PromocodeORM.id)
            )
            row = (await session.execute(query)).one_or_none()

            if row is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"status": "error", "message": "Промокод не найден."},
                )

            promo_orm, comments_count = row
            query = select(PromoUserORM).where(
                PromoUserORM.user_id == user_id, PromoUserORM.promo_id == promo_id
            )
            result_orm = (await session.execute(query)).scalar_one_or_none()
            if result_orm is None:
                is_activated = False
                is_liked = False
            else:
                is_activated = result_orm.activated
                is_liked = result_orm.liked

            result_dto = PromoForUser(
                promo_id=promo_orm.id,
                company_id=promo_orm.company_id,
                company_name=promo_orm.company.name,
                description=promo_orm.description,
                image_url=promo_orm.image_url,
                active=promo_orm.active,
                is_activated_by_user=is_activated,
                like_count=promo_orm.like_count,
                is_liked_by_user=is_liked,
                comment_count=comments_count,
            )

            return result_dto

    async def like_promo(self, user_id: str, promo_id: str, session: AsyncSession):
        async with session as session:
            query = select(PromoUserORM).where(
                PromoUserORM.user_id == user_id, PromoUserORM.promo_id == promo_id
            )

            result_orm = (await session.execute(query)).scalar_one_or_none()
            promo_orm = await session.get(PromocodeORM, promo_id)

            if promo_orm is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"status": "error", "message": "Промокод не найден."},
                )

            if result_orm is None:
                session.add(
                    PromoUserORM(
                        user_id=user_id,
                        promo_id=promo_id,
                        liked=True,
                    )
                )
                promo_orm.like_count += 1
            else:
                if not result_orm.liked:
                    result_orm.liked = True
                    promo_orm.like_count += 1

            await session.commit()

    async def unlike_promo(self, user_id: str, promo_id: str, session: AsyncSession):
        async with session as session:
            query = select(PromoUserORM).where(
                PromoUserORM.user_id == user_id, PromoUserORM.promo_id == promo_id
            )

            result_orm = (await session.execute(query)).scalar_one_or_none()
            promo_orm = await session.get(PromocodeORM, promo_id)

            if promo_orm is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"status": "error", "message": "Промокод не найден."},
                )

            if result_orm is None:
                return
            elif result_orm.liked:
                result_orm.liked = False
                promo_orm.like_count -= 1

            await session.commit()
            return

    async def add_comment(
        self, text: str, user_id: str, promo_id: str, session: AsyncSession
    ) -> CommentGet:
        async with session as session:
            query = (
                select(PromocodeORM)
                .options(selectinload(PromocodeORM.comments))
                .where(PromocodeORM.id == promo_id)
            )
            promo_orm = (await session.execute(query)).scalar_one_or_none()
            if promo_orm is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"status": "error", "message": "Промокод не найден."},
                )
            query = select(UserORM).where(UserORM.id == user_id)
            user_orm = (await session.execute(query)).scalar_one()

            new_comment_orm = CommentORM(text=text, author=user_id, promo_id=promo_id)
            promo_orm.comments.append(new_comment_orm)

            await session.commit()
            await session.refresh(new_comment_orm)

            return CommentGet(
                id=new_comment_orm.id,
                text=text,
                date=new_comment_orm.date,
                author=CommentAuthor(
                    name=user_orm.name,
                    surname=user_orm.surname,
                    avatar_url=user_orm.avatar_url,
                ),
            )

    async def get_comments_for_promo(
        self,
        promo_id: str,
        session: AsyncSession,
        limit: int,
        offset: int,
    ) -> list[CommentGet]:
        async with session as session:
            if await session.get(PromocodeORM, promo_id) is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"status": "error", "message": "Промокод не найден."},
                )

            query = (
                select(CommentORM)
                .options(selectinload(CommentORM.user))
                .where(CommentORM.promo_id == promo_id)
                .order_by(CommentORM.date.desc())
                .limit(limit)
                .offset(offset)
            )

            result_orm = (await session.execute(query)).scalars().all()

            result_dto = []
            for model in result_orm:
                comment = CommentGet(
                    id=model.id,
                    text=model.text,
                    date=model.date,
                    author=CommentAuthor(
                        name=model.user.name,
                        surname=model.user.surname,
                        avatar_url=model.user.avatar_url,
                    ),
                )
                result_dto.append(comment)
            return result_dto

    async def get_comment_for_promo(
        self,
        comment_id: str,
        promo_id: str,
        session: AsyncSession,
    ) -> CommentGet:
        query = (
            select(CommentORM)
            .options(selectinload(CommentORM.user))
            .join(PromocodeORM, CommentORM.promo_id == PromocodeORM.id)
            .where(PromocodeORM.id == promo_id, CommentORM.id == comment_id)
        )

        result_orm = (await session.execute(query)).scalar_one_or_none()
        if result_orm is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "status": "error",
                    "message": "Такого промокода или комментария не существует.",
                },
            )

        return CommentGet(
            id=result_orm.id,
            text=result_orm.text,
            date=result_orm.date,
            author=CommentAuthor(
                name=result_orm.user.name,
                surname=result_orm.user.surname,
                avatar_url=result_orm.user.avatar_url,
            ),
        )

    async def put_comment(
        self,
        text: str,
        comment_id: str,
        promo_id: str,
        session: AsyncSession,
    ) -> CommentGet:
        query = (
            select(CommentORM)
            .options(selectinload(CommentORM.user))
            .join(PromocodeORM, CommentORM.promo_id == PromocodeORM.id)
            .where(PromocodeORM.id == promo_id, CommentORM.id == comment_id)
        )

        result_orm = (await session.execute(query)).scalar_one_or_none()
        if result_orm is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "status": "error",
                    "message": "Такого промокода или комментария не существует.",
                },
            )

        result_orm.text = text
        await session.commit()
        await session.refresh(result_orm)

        return CommentGet(
            id=result_orm.id,
            text=result_orm.text,
            date=result_orm.date,
            author=CommentAuthor(
                name=result_orm.user.name,
                surname=result_orm.user.surname,
                avatar_url=result_orm.user.avatar_url,
            ),
        )
