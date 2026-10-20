from fastapi import APIRouter

from app.api import auth, categories, health, me, quests, rewards, tiers, transactions

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(me.router)
api_router.include_router(tiers.router)
api_router.include_router(categories.router)
api_router.include_router(rewards.router)
api_router.include_router(quests.router)
api_router.include_router(transactions.router)
