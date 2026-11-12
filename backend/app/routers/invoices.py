import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_business
from app.db.session import get_db
from app.models import Business
from app.schemas.invoice import InvoiceCreate, InvoiceOut
from app.services import invoice_service as svc

router = APIRouter(prefix="/invoices", tags=["invoices"])


@router.get("", response_model=list[InvoiceOut])
def list_invoices(
    status: str | None = Query(default=None, description="DRAFT|SENT|PENDING|OVERDUE|PAID|CANCELLED"),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    return [svc.to_out(i) for i in svc.list_invoices(db, business.id, status, limit, offset)]


@router.post("", response_model=InvoiceOut, status_code=201)
def create_invoice(
    data: InvoiceCreate, business: Business = Depends(get_current_business), db: Session = Depends(get_db)
):
    return svc.to_out(svc.create_invoice(db, business, data))


@router.get("/{invoice_id}", response_model=InvoiceOut)
def get_invoice(
    invoice_id: uuid.UUID, business: Business = Depends(get_current_business), db: Session = Depends(get_db)
):
    return svc.to_out(svc.get_invoice(db, business.id, invoice_id))


@router.post("/{invoice_id}/send", response_model=InvoiceOut)
def send_invoice(
    invoice_id: uuid.UUID, business: Business = Depends(get_current_business), db: Session = Depends(get_db)
):
    inv = svc.get_invoice(db, business.id, invoice_id)
    return svc.to_out(svc.send_invoice(db, inv))


@router.post("/{invoice_id}/cancel", response_model=InvoiceOut)
def cancel_invoice(
    invoice_id: uuid.UUID, business: Business = Depends(get_current_business), db: Session = Depends(get_db)
):
    inv = svc.get_invoice(db, business.id, invoice_id)
    return svc.to_out(svc.cancel_invoice(db, inv))