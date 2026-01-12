# api/business

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_config
from database import get_db
from schemas.business import (
    CompanySignInRequest,
    CompanySignInResponse,
    CompanySignUpRequest,
    CompanySignUpResponse,
    PromoCreateRequest,
    PromoCreateResponse,
    PromoDTO,
    PromoFilterQueryParams,
    PromoPatch,
)
from services.company_service import CompanyService
from services.promo_service import PromoService
from utils.auth import AccessTokenCompanyBearer

cfg = get_config()

business_router = APIRouter(prefix="/business", tags=["B2B"])

company_service = CompanyService()
promo_service = PromoService()


@business_router.post("/auth/sign-up")
async def business_sign_up(
    company: CompanySignUpRequest,
    db: AsyncSession = Depends(get_db),
) -> CompanySignUpResponse:
    return await company_service.company_sign_up(company, db)


@business_router.post("/auth/sign-in")
async def business_sign_in(
    data: CompanySignInRequest,
    db: AsyncSession = Depends(get_db),
) -> CompanySignInResponse:
    return await company_service.company_sign_in(data, db)


@business_router.post("/promo")
async def business_create_promo(
    data: PromoCreateRequest,
    db: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(
        AccessTokenCompanyBearer(auto_error=True)
    ),
) -> PromoCreateResponse:
    company_id = company_service.get_company_uuid_from_token(credentials.credentials)
    if await company_service.is_exist_in_db(id=company_id, db=db):
        return await promo_service.create_promocode(data, db=db, company_id=company_id)
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"status": "error", "message": "Пользователь не авторизован."},
        )


@business_router.get("/promo")
async def business_get_promos(
    response: Response,
    filter_query: Annotated[PromoFilterQueryParams, Query()],
    db: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(
        AccessTokenCompanyBearer(auto_error=True)
    ),
) -> list[PromoDTO]:
    company_id = company_service.get_company_uuid_from_token(credentials.credentials)
    total, result_dto = await promo_service.get_company_promos(
        company_id=company_id, session=db, filter_query=filter_query
    )
    response.headers["X-Total-Count"] = str(total)
    return result_dto


@business_router.get("/promo/{id}")
async def business_get_promo(
    id: str = Path(...),
    db: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(
        AccessTokenCompanyBearer(auto_error=True)
    ),
) -> PromoDTO:
    company_id = company_service.get_company_uuid_from_token(credentials.credentials)
    if await company_service.is_exist_in_db(company_id, db=db):
        return await promo_service.get_company_promo_by_id(
            company_id=company_id, promo_id=id, db=db
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"status": "error", "message": "Пользователь не авторизован."},
        )


@business_router.patch("/promo/{id}")
async def business_update_promo(
    data: PromoPatch,
    id: str = Path(...),
    db: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(
        AccessTokenCompanyBearer(auto_error=True)
    ),
) -> PromoDTO | None:
    company_id = company_service.get_company_uuid_from_token(credentials.credentials)
    if await company_service.is_exist_in_db(company_id, db=db):
        return await promo_service.update_company_promo(
            data=data, company_id=company_id, promo_id=id, session=db
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"status": "error", "message": "Пользователь не авторизован."},
        )


# @business_router.get("/promo/{id}/stat")
# async def business_get_promo_stat(
#     id: str = Path(...),
#     credentials: HTTPAuthorizationCredentials = Depends(
#         AccessTokenCompanyBearer(auto_error=True)
#     ),
#     db: AsyncSession = Depends(get_db),
# ):
#     company_id = company_service.get_company_uuid_from_token(credentials.credentials)
#     if await company_service.is_exist_in_db(company_id, db=db):
#         return await promo_service.get_promo_stat(
#             promo_id=id, company_id=company_id, session=db
#         )
#     else:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail={"status": "error", "message": "Пользователь не авторизован."},
#         )
