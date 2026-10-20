from fastapi import APIRouter

from app.api import auth, categories, health, me, tiers

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(me.router)
api_router.include_router(tiers.router)
api_router.include_router(categories.router)
