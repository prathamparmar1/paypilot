from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_business
from app.db.session import get_db
from app.models import Business
from app.schemas.dashboard import DashboardSummary
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def summary(business: Business = Depends(get_current_business), db: Session = Depends(get_db)):
    return dashboard_service.get_summary(db, business.id)