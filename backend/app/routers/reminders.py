import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_business
from app.db.session import get_db
from app.models import Business
from app.routers.ai import _rate_limit
from app.schemas.reminder import ReminderCandidate, ReminderEdit, ReminderOut
from app.services import reminder_service as svc

router = APIRouter(prefix="/reminders", tags=["reminders"])


@router.get("", response_model=list[ReminderOut])
def list_reminders(
    status: str | None = None, business: Business = Depends(get_current_business), db: Session = Depends(get_db)
):
    return [svc.to_out(r) for r in svc.list_reminders(db, business.id, status)]


@router.get("/candidates", response_model=list[ReminderCandidate])
def candidates(business: Business = Depends(get_current_business), db: Session = Depends(get_db)):
    return svc.candidates(db, business.id)


@router.post("/generate/{invoice_id}", response_model=ReminderOut)
def generate(
    invoice_id: uuid.UUID, business: Business = Depends(get_current_business), db: Session = Depends(get_db)
):
    _rate_limit(business.id)
    return svc.to_out(svc.generate(db, business, invoice_id))


@router.patch("/{reminder_id}", response_model=ReminderOut)
def edit(
    reminder_id: uuid.UUID, data: ReminderEdit,
    business: Business = Depends(get_current_business), db: Session = Depends(get_db),
):
    return svc.to_out(svc.edit(db, business, reminder_id, data.message))


@router.post("/{reminder_id}/approve", response_model=ReminderOut)
def approve(
    reminder_id: uuid.UUID, business: Business = Depends(get_current_business), db: Session = Depends(get_db)
):
    return svc.to_out(svc.approve(db, business, reminder_id))


@router.post("/{reminder_id}/dismiss", response_model=ReminderOut)
def dismiss(
    reminder_id: uuid.UUID, business: Business = Depends(get_current_business), db: Session = Depends(get_db)
):
    return svc.to_out(svc.dismiss(db, business, reminder_id))