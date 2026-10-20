from fastapi import APIRouter, status
from sqlalchemy import select

from app.crud import apply_changes, ensure_can_archive, get_owned
from app.db import DbSession
from app.deps import CurrentUser
from app.models import Tier
from app.schemas import ArchiveConflict, TierCreate, TierOut, TierUpdate

router = APIRouter(prefix="/tiers", tags=["tiers"])


@router.get("")
def list_tiers(user: CurrentUser, db: DbSession, include_archived: bool = False) -> list[TierOut]:
    query = select(Tier).where(Tier.user_id == user.id).order_by(Tier.level, Tier.id)
    if not include_archived:
        query = query.where(Tier.is_archived.is_(False))
    return [TierOut.model_validate(tier) for tier in db.scalars(query)]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_tier(data: TierCreate, user: CurrentUser, db: DbSession) -> TierOut:
    tier = Tier(user_id=user.id, **data.model_dump())
    db.add(tier)
    db.commit()
    return TierOut.model_validate(tier)


@router.patch("/{tier_id}", responses={409: {"model": ArchiveConflict}})
def update_tier(tier_id: int, data: TierUpdate, user: CurrentUser, db: DbSession) -> TierOut:
    tier = get_owned(db, Tier, tier_id, user)
    changes = data.changes()
    if changes.get("is_archived") and not tier.is_archived:
        ensure_can_archive(db, "tier_id", tier.id)
    apply_changes(tier, changes)
    db.commit()
    return TierOut.model_validate(tier)
