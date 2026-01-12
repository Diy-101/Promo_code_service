from fastapi import APIRouter

from .business import business_router
from .user import user_router

main_router = APIRouter(prefix="/api", tags=["main"])
main_router.include_router(business_router)
main_router.include_router(user_router)

__all__ = ["main_router"]
