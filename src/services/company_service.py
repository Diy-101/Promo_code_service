from datetime import datetime, timedelta
from uuid import uuid4

import jwt
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_config
from schemas.business import (
    CompanySignInRequest,
    CompanySignInResponse,
    CompanySignUpRequest,
    CompanySignUpResponse,
)
from utils.general import verify_password
from utils.logger import logger
from utils.repository import CompanyRepository
from utils.whitelist import TokenWhiteList

cfg = get_config()
token_whitelist = TokenWhiteList()
company_repository = CompanyRepository()


class CompanyService:
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

    def get_company_uuid_from_token(self, token: str) -> str:
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
        result = await company_repository.get_company_by_id(id=id, db=db)
        return True if result is not None else False

    async def company_sign_up(self, company: CompanySignUpRequest, db: AsyncSession):
        company_dto = await company_repository.get_company_by_email(
            company.email, db=db
        )

        if company_dto is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "status": "error",
                    "message": "Такой email уже зарегистрирован",
                },
            )

        company_dto = await company_repository.create_company(company=company, db=db)
        token_id, token = self.create_access_token(id=company_dto.id)

        await token_whitelist.add_jti_to_whitelist(
            id=company_dto.id, jti=token_id, entity="company"
        )

        return CompanySignUpResponse(token=token, company_id=company_dto.id)

    async def company_sign_in(self, company: CompanySignInRequest, db: AsyncSession):
        # Проверка email
        model = await company_repository.get_company_by_email(company.email, db=db)

        if model is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"status": "error", "message": "Неверный email или пароль."},
            )

        # Проверка password
        if not await verify_password(company.password, model.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"status": "error", "message": "Неверный email или пароль."},
            )

        # Создание нового токена
        await token_whitelist.flush_all_jti_from_whitelist(model.id, entity="company")
        token_id, new_token = self.create_access_token(id=model.id)
        await token_whitelist.add_jti_to_whitelist(model.id, token_id, "company")
        return CompanySignInResponse(token=new_token)
