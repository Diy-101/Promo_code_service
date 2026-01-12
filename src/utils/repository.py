from fastapi import HTTPException, status
from sqlalchemy import and_, func, inspect, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config import get_config
from database import Base
from models.business import CategoryORM, CompanyORM, PromocodeORM, UniquePromocodeORM
from schemas.business import (
    CompanyDTO,
    CompanySignUpRequest,
    PromoCreateRequest,
    PromoDTO,
    PromoFilterQueryParams,
    PromoPatch,
    PromoStat,
    Target,
)
from utils.general import hash_password

cfg = get_config()


class SQLAlchemyRepository:
    """
    Универсальный репозиторий предоставляющий интерфейс SQLAlchemy
    """

    def __call__(self):
        return self

    @staticmethod
    async def model_as_dict(model) -> dict:
        data_dict = {
            c.name: getattr(model, c.name)
            for c in inspect(model).mapper.columns  # type: ignore
        }

        return data_dict

    async def is_exist(
        self, model: type[Base], field: str, filter_field: str, db: AsyncSession
    ) -> bool:
        async with db as session:
            query = select(model).where(getattr(model, field) == filter_field)
            result = await session.execute(query)

            result_orm = result.scalar_one_or_none()
            return True if result_orm is not None else False


class CompanyRepository(SQLAlchemyRepository):
    """
    Репозиторий для работы с компаниями
    """

    async def get_company_by_id(self, id: str, db: AsyncSession) -> CompanyDTO | None:
        async with db as session:
            query = select(CompanyORM).where(CompanyORM.id == id)
            result = await session.execute(query)
            result_orm = result.scalar_one_or_none()

            if result_orm is None:
                return None

            result_dto = CompanyDTO.model_validate(result_orm, from_attributes=True)
            return result_dto

    async def get_company_by_email(
        self, email: str, db: AsyncSession
    ) -> CompanyDTO | None:
        async with db as session:
            query = select(CompanyORM).where(CompanyORM.email == email)
            result = await session.execute(query)
            result_orm = result.scalar_one_or_none()

            if result_orm is None:
                return None

            result_dto = CompanyDTO.model_validate(result_orm, from_attributes=True)
            return result_dto

    async def create_company(
        self, company: CompanySignUpRequest, db: AsyncSession
    ) -> CompanyDTO:
        async with db as session:
            model = CompanyORM(
                name=company.name,
                email=company.email,
                password=await hash_password(company.password),
            )
            session.add(model)
            await session.commit()
            await session.refresh(model)
            return CompanyDTO.model_validate(model, from_attributes=True)


class PromoRepository(SQLAlchemyRepository):
    """
    Репозиторий для работы с промокодами
    """

    async def create_promo(
        self, data: PromoCreateRequest, company_id: str, db: AsyncSession
    ) -> str:
        async with db as session:
            model = PromocodeORM(
                company_id=company_id,
                description=data.description,
                image_url=str(data.image_url),
                age_from=data.target.age_from if data.target else None,
                age_until=data.target.age_until if data.target else None,
                country=data.target.country if data.target else None,
                active_from=data.active_from,
                active_until=data.active_until,
                max_count=data.max_count,
                mode=data.mode,
                promo_common=data.promo_common,
            )

            model.categories = [
                CategoryORM(name=cat)
                for cat in (
                    data.target.categories or [] if data.target is not None else []
                )
            ]

            if data.mode == "UNIQUE":
                model.unique_promos = [
                    UniquePromocodeORM(promocode=un_promo)
                    for un_promo in data.promo_unique or []
                ]

            session.add(model)
            await session.commit()
            await session.refresh(model)
            return model.id

    async def get_company_promos(
        self,
        company_id: str,
        session: AsyncSession,
        filter_query: PromoFilterQueryParams,
    ) -> tuple[int, list[PromoDTO]]:
        query = (
            select(PromocodeORM)
            .options(selectinload(PromocodeORM.categories))
            .options(selectinload(PromocodeORM.unique_promos))
        )

        conditions = []
        conditions.append(PromocodeORM.company_id == company_id)

        if filter_query.country is not None:
            conditions.append(PromocodeORM.country.in_(filter_query.country))

        query = query.where(and_(*conditions))

        if filter_query.sort_by is not None:
            if filter_query.sort_by == "active_from":
                query = query.order_by(PromocodeORM.active_from.desc())
            elif filter_query.sort_by == "active_until":
                query = query.order_by(PromocodeORM.active_until.desc())

        query = query.limit(filter_query.limit).offset(filter_query.offset)

        count_stmt = select(func.count()).select_from(PromocodeORM).where(*conditions)

        async with session as session:
            result_orm = (await session.execute(query)).scalars().all()
            total = (await session.execute(count_stmt)).scalar_one_or_none() or 0

        result_dto = []
        for model in result_orm:
            model_dto = PromoDTO(
                id=model.id,
                company_id=model.company_id,
                description=model.description,
                image_url=model.image_url,  # type: ignore
                active_from=model.active_from,
                active_until=model.active_until,
                target=Target(
                    age_from=model.age_from,
                    age_until=model.age_until,
                    country=model.country,  # type: ignore
                    categories=[cat.name for cat in model.categories],
                ),
                max_count=model.max_count,
                mode=model.mode.name,
                active=model.active,
                like_count=model.like_count,
                used_count=model.used_count,
                promo_common=model.promo_common,
                promo_unique=[promo.promocode for promo in model.unique_promos]
                if model.unique_promos
                else None,
            )
            result_dto.append(model_dto)
        return total, result_dto

    async def get_company_promo_by_id(
        self, company_id: str, promo_id: str, session: AsyncSession
    ) -> PromoDTO:
        async with session as session:
            query = (
                select(PromocodeORM)
                .where(PromocodeORM.id == promo_id)
                .options(selectinload(PromocodeORM.categories))
                .options(selectinload(PromocodeORM.unique_promos))
            )
            model = (await session.execute(query)).scalar_one_or_none()
            if model is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"status": "error", "message": "Промокод не найден."},
                )
            if model.company_id != company_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "status": "error",
                        "message": "Промокод не принадлежит этой компании.",
                    },
                )
            return PromoDTO(
                id=model.id,
                company_id=model.company_id,
                description=model.description,
                image_url=model.image_url,  # type: ignore
                active_from=model.active_from,
                active_until=model.active_until,
                target=Target(
                    age_from=model.age_from,
                    age_until=model.age_until,
                    country=model.country,  # type: ignore
                    categories=[cat.name for cat in model.categories],
                ),
                max_count=model.max_count,
                mode=model.mode.name,
                active=model.active,
                like_count=model.like_count,
                used_count=model.used_count,
                promo_common=model.promo_common,
                promo_unique=[promo.promocode for promo in model.unique_promos]
                if model.unique_promos
                else None,
            )

    async def update_company_promo(
        self, data: PromoPatch, company_id: str, promo_id: str, session: AsyncSession
    ):
        async with session as session:
            query = (
                select(PromocodeORM)
                .where(PromocodeORM.id == promo_id)
                .options(selectinload(PromocodeORM.categories))
                .options(selectinload(PromocodeORM.unique_promos))
            )
            model = (await session.execute(query)).scalar_one_or_none()

            if model is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"status": "error", "message": "Промокод не найден."},
                )
            if model.company_id != company_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "status": "error",
                        "message": "Промокод не принадлежит этой компании.",
                    },
                )
            update_data = data.model_dump(
                exclude_unset=True,
                exclude={"target"},
            )
            for field, value in update_data.items():
                if value is not None:
                    setattr(model, field, value)

            if data.target is not None:
                for field, value in data.target.model_dump(
                    exclude_unset=True, exclude={"categories"}
                ).items():
                    setattr(model, field, value)
                if data.target.categories is not None:
                    cats = []
                    for cat in data.target.categories:
                        cats.append(CategoryORM(name=cat))
                    model.categories = cats
            if (
                model.active_from
                and model.active_until
                and model.active_from >= model.active_until
            ):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "status": "error",
                        "message": "Ошибка в данных запроса.",
                    },
                )
            if model.age_from and model.age_until and model.age_from >= model.age_until:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "status": "error",
                        "message": "Ошибка в данных запроса.",
                    },
                )
            session.add(model)
            await session.commit()
            await session.refresh(model)

            result_dto = PromoDTO(
                id=model.id,
                company_id=model.company_id,
                description=model.description,
                image_url=model.image_url,  # type: ignore
                active_from=model.active_from,
                active_until=model.active_until,
                target=Target(
                    age_from=model.age_from,
                    age_until=model.age_until,
                    country=model.country,  # type: ignore
                    categories=[cat.name for cat in model.categories],
                ),
                max_count=model.max_count,
                mode=model.mode.name,
                active=model.active,
                like_count=model.like_count,
                used_count=model.used_count,
                promo_common=model.promo_common,
                promo_unique=[promo.promocode for promo in model.unique_promos]
                if model.unique_promos
                else None,
            )
            return result_dto

    async def get_promo_stat(
        self, promo_id: str, company_id: str, session: AsyncSession
    ) -> PromoStat | None:
        async with session as session:
            query = select(PromocodeORM).where(PromocodeORM.id == promo_id)
            # TODO написать функцию получения статистики промокода
            pass
