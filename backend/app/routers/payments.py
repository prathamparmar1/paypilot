from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_business
from app.db.session import get_db
from app.models import Business, Customer, Invoice, Payment
from app.schemas.payment import PaymentOut

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("", response_model=list[PaymentOut])
def list_payments(business: Business = Depends(get_current_business), db: Session = Depends(get_db)):
    rows = db.execute(
        select(Payment, Invoice.number, Customer.name)
        .join(Invoice, Invoice.id == Payment.invoice_id)
        .join(Customer, Customer.id == Invoice.customer_id)
        .where(Payment.business_id == business.id)
        .order_by(Payment.verified_at.desc())
        .limit(200)
    ).all()
    return [
        PaymentOut(
            id=p.id, invoice_id=p.invoice_id, invoice_number=num, customer_name=name,
            amount=p.amount, currency=p.currency, status=p.status.value,
            paypal_order_id=p.paypal_order_id, paypal_capture_id=p.paypal_capture_id,
            payer_email=p.payer_email, verified_at=p.verified_at,
        )
        for p, num, name in rows
    ]