from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.payment import CaptureOut, CaptureRequest, OrderOut, PublicInvoice
from app.services import payment_service as svc

router = APIRouter(prefix="/pay", tags=["public-pay"])


@router.get("/{token}", response_model=PublicInvoice)
def view_invoice(token: str, db: Session = Depends(get_db)):
    return svc.public_view(svc.get_payable_invoice(db, token))


@router.post("/{token}/create-order", response_model=OrderOut)
def create_order(token: str, db: Session = Depends(get_db)):
    return OrderOut(order_id=svc.create_order(db, token))


@router.post("/{token}/capture", response_model=CaptureOut)
def capture(token: str, data: CaptureRequest, db: Session = Depends(get_db)):
    inv = svc.capture(db, token, data.order_id)
    return CaptureOut(invoice_status=inv.status.value)