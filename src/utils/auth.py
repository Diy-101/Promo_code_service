# src/utils/auth.py


import jwt
from fastapi import HTTPException, Request, status
from fastapi.security import HTTPBearer
from fastapi.security.http import HTTPAuthorizationCredentials

from config import get_config
from utils.logger import logger
from utils.whitelist import TokenWhiteList

cfg = get_config()
token_blacklist = TokenWhiteList()


class TokenBearer(HTTPBearer):
    """
    Базовый класс для Токенов JWT
    """

    def __init__(
        self,
        auto_error: bool = True,
    ):
        super().__init__(auto_error=auto_error)

    async def __call__(self, request: Request) -> HTTPAuthorizationCredentials | None:
        auth_data = await super().__call__(request)
        credentials = getattr(auth_data, "credentials", None)

        # Наличие данных
        if not auth_data or not credentials:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"status": "error", "message": "Пользователь не авторизован"},
            )

        # Валидность токена
        try:
            token_data = jwt.decode(
                credentials, key=cfg.JWT_SECRET, algorithms=cfg.JWT_ALGORITHM
            )
        except jwt.PyJWTError as error:
            logger.error(f"Token is invalid or expired: {error}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"status": "error", "message": "Token is invalid or expired"},
            )

        await self.verify_token_data(token_data=token_data)

        return auth_data

    async def verify_token_data(self, token_data: dict) -> None:
        raise NotImplementedError("Please override this method in child classes")


class AccessTokenBearer(TokenBearer):
    """
    Сущность access токена
    """

    def __init__(
        self,
        auto_error: bool = False,
    ):
        super().__init__(auto_error=auto_error)

    async def verify_token_data(self, token_data: dict) -> None:
        if token_data.get("refresh"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"status": "error", "message": "Please provide an access token"},
            )


class AccessTokenCompanyBearer(AccessTokenBearer):
    def __init__(
        self,
        auto_error: bool = False,
    ):
        super().__init__(auto_error=auto_error)

    async def verify_token_data(self, token_data: dict) -> None:
        if token_data.get("refresh"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"status": "error", "message": "Please provide an access token"},
            )
        if not await token_blacklist.check_jti_in_whitelist(
            token_data["id"], token_data["jti"], entity="company"
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"status": "error", "message": "Please provide an access token"},
            )


class AccessTokenUserBearer(AccessTokenBearer):
    def __init__(
        self,
        auto_error: bool = False,
    ):
        super().__init__(auto_error=auto_error)

    async def verify_token_data(self, token_data: dict) -> None:
        if token_data.get("refresh"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"status": "error", "message": "Please provide an access token"},
            )
        if not await token_blacklist.check_jti_in_whitelist(
            token_data["id"], token_data["jti"], entity="user"
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"status": "error", "message": "Please provide an access token"},
            )
