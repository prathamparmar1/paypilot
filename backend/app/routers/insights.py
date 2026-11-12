from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.ai.insights import build_insights
from app.core.deps import get_current_business
from app.db.session import get_db
from app.models import Business
from app.routers.ai import _rate_limit
from app.services.insights_service import compute_stats

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("")
def insights(business: Business = Depends(get_current_business), db: Session = Depends(get_db)):
    _rate_limit(business.id, limit=30)
    stats = compute_stats(db, business.id)
    items, ai = build_insights(business.id, stats)
    return {"stats": stats, "insights": items, "ai_generated": ai}