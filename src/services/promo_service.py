from sqlalchemy.ext.asyncio import AsyncSession

from schemas.business import (
    PromoCreateRequest,
    PromoCreateResponse,
    PromoDTO,
    PromoFilterQueryParams,
    PromoPatch,
)
from utils.repository import PromoRepository

promo_repository = PromoRepository()


class PromoService:
    async def create_promocode(
        self, data: PromoCreateRequest, db: AsyncSession, company_id: str
    ) -> PromoCreateResponse:
        promo_id = await promo_repository.create_promo(
            data=data, db=db, company_id=company_id
        )

        return PromoCreateResponse(id=promo_id)

    async def get_company_promos(
        self,
        company_id: str,
        session: AsyncSession,
        filter_query: PromoFilterQueryParams,
    ) -> tuple[int, list[PromoDTO]]:
        total, result_dto = await promo_repository.get_company_promos(
            company_id, session, filter_query
        )
        return total, result_dto

    async def get_company_promo_by_id(
        self, company_id: str, promo_id: str, db: AsyncSession
    ) -> PromoDTO:
        return await promo_repository.get_company_promo_by_id(
            company_id=company_id, promo_id=promo_id, session=db
        )

    async def update_company_promo(
        self, data: PromoPatch, company_id: str, promo_id: str, session: AsyncSession
    ):
        return await promo_repository.update_company_promo(
            data=data, company_id=company_id, promo_id=promo_id, session=session
        )

    # async def get_promo_stat(
    #     self, promo_id: str, company_id: str, session: AsyncSession
    # ) -> PromoStat:
    #     return await promo_repository.get_promo_stat(
    #         promo_id=promo_id, company_id=company_id, session=session
    #     )
