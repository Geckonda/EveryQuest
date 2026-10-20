from fastapi import APIRouter
from sqlalchemy import select

from app.db import DbSession
from app.deps import CurrentUser
from app.models import Tier
from app.schemas import TierOut

router = APIRouter(prefix="/tiers", tags=["tiers"])


@router.get("")
def list_tiers(user: CurrentUser, db: DbSession, include_archived: bool = False) -> list[TierOut]:
    query = select(Tier).where(Tier.user_id == user.id).order_by(Tier.level, Tier.id)
    if not include_archived:
        query = query.where(Tier.is_archived.is_(False))
    return [TierOut.model_validate(tier) for tier in db.scalars(query)]
