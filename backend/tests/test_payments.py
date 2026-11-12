import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import delete, select

from app.core.errors import AppError
from app.db.session import SessionLocal
from app.models import Business, Customer, Invoice, InvoiceStatus, Payment
from app.services.payment_service import record_capture


def _fake_order(inv, amount="50.00", cap_id=None):
    return {
        "id": "ORDER-" + uuid.uuid4().hex[:8],
        "status": "COMPLETED",
        "payer": {"email_address": "buyer@example.com"},
        "purchase_units": [{
            "custom_id": str(inv.id),
            "payments": {"captures": [{
                "id": cap_id or "CAP-" + uuid.uuid4().hex[:8],
                "status": "COMPLETED",
                "amount": {"value": amount, "currency_code": "USD"},
            }]},
        }],
    }


def test_record_capture_validates_and_is_idempotent():
    with SessionLocal() as db:
        b = Business(owner_name="O", business_name="B", email=f"p_{uuid.uuid4().hex[:8]}@e.com", password_hash="x")
        db.add(b); db.flush()
        c = Customer(business_id=b.id, name="Rahul"); db.add(c); db.flush()
        inv = Invoice(
            business_id=b.id, customer_id=c.id, number="INV-0001", description="Test",
            amount=Decimal("50.00"), currency="USD", due_date=date.today() + timedelta(days=3),
            status=InvoiceStatus.SENT, public_token=uuid.uuid4().hex,
        )
        db.add(inv); db.commit()
        try:
            # wrong amount rejected, invoice stays SENT
            with pytest.raises(AppError):
                record_capture(db, inv, _fake_order(inv, amount="10.00"))
            db.refresh(inv)
            assert inv.status == InvoiceStatus.SENT

            # wrong invoice binding rejected
            bad = _fake_order(inv); bad["purchase_units"][0]["custom_id"] = str(uuid.uuid4())
            with pytest.raises(AppError):
                record_capture(db, inv, bad)

            # valid capture, twice -> one payment
            order = _fake_order(inv, cap_id="CAP-FIXED-1")
            p1 = record_capture(db, inv, order)
            p2 = record_capture(db, inv, order)
            assert p1.id == p2.id
            db.refresh(inv)
            assert inv.status == InvoiceStatus.PAID
            assert len(db.scalars(select(Payment).where(Payment.invoice_id == inv.id)).all()) == 1
        finally:
            db.rollback()
            db.execute(delete(Payment).where(Payment.business_id == b.id))
            db.execute(delete(Invoice).where(Invoice.business_id == b.id))
            db.execute(delete(Customer).where(Customer.business_id == b.id))
            db.execute(delete(Business).where(Business.id == b.id))
            db.commit()