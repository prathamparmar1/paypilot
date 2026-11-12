import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import delete

from app.ai import insights, reminder_writer
from app.core.errors import AppError
from app.db.session import SessionLocal
from app.models import Business, Customer, Invoice, InvoiceStatus, Payment, PaymentStatus, Reminder
from app.services import insights_service, reminder_service


def _inv(db, b, c, n, amount, status, due_days):
    i = Invoice(
        business_id=b.id, customer_id=c.id, number=n, description="svc", amount=Decimal(amount),
        currency="USD", due_date=date.today() + timedelta(days=due_days), status=status,
        public_token=uuid.uuid4().hex,
    )
    db.add(i); db.flush()
    return i


def test_reminder_flow_and_validation(monkeypatch):
    with SessionLocal() as db:
        b1 = Business(owner_name="O", business_name="Biz", email=f"r1_{uuid.uuid4().hex[:6]}@e.com", password_hash="x")
        b2 = Business(owner_name="O", business_name="Biz2", email=f"r2_{uuid.uuid4().hex[:6]}@e.com", password_hash="x")
        db.add_all([b1, b2]); db.flush()
        c = Customer(business_id=b1.id, name="Rahul"); db.add(c); db.flush()
        sent = _inv(db, b1, c, "INV-0001", "20.00", InvoiceStatus.SENT, -3)
        draft = _inv(db, b1, c, "INV-0002", "30.00", InvoiceStatus.DRAFT, 5)
        db.commit()
        try:
            # invented amount -> falls back to template
            monkeypatch.setattr(reminder_writer, "generate_text", lambda *a, **k: "Hi Rahul, INV-0001 for $999 is due.")
            r = reminder_service.generate(db, b1, sent.id)
            assert "$20.00" in r.message and "$999" not in r.message and "/pay/" in r.message

            # valid AI text accepted; regenerate reuses the same draft row
            good = "Hi Rahul, invoice INV-0001 for $20.00 was due recently.\n\nThank you,\nBiz"
            monkeypatch.setattr(reminder_writer, "generate_text", lambda *a, **k: good)
            r2 = reminder_service.generate(db, b1, sent.id)
            assert r2.id == r.id and r2.message.startswith("Hi Rahul, invoice INV-0001")

            with pytest.raises(AppError) as e:   # draft invoice not eligible
                reminder_service.generate(db, b1, draft.id)
            assert e.value.status_code == 409

            with pytest.raises(AppError) as e:   # ownership
                reminder_service.approve(db, b2, r.id)
            assert e.value.status_code == 404

            edited = reminder_service.edit(db, b1, r.id, "Hi Rahul, please pay INV-0001 soon.")
            assert "please pay" in edited.message
            assert reminder_service.approve(db, b1, r.id).status.value == "APPROVED"
            with pytest.raises(AppError) as e:
                reminder_service.approve(db, b1, r.id)
            assert e.value.status_code == 409
        finally:
            db.rollback()
            ids = [b1.id, b2.id]
            db.execute(delete(Reminder).where(Reminder.business_id.in_(ids)))
            db.execute(delete(Invoice).where(Invoice.business_id.in_(ids)))
            db.execute(delete(Customer).where(Customer.business_id.in_(ids)))
            db.execute(delete(Business).where(Business.id.in_(ids)))
            db.commit()


def test_insights_stats_and_validation():
    with SessionLocal() as db:
        b = Business(owner_name="O", business_name="Biz", email=f"i_{uuid.uuid4().hex[:6]}@e.com", password_hash="x")
        db.add(b); db.flush()
        c = Customer(business_id=b.id, name="Rahul"); db.add(c); db.flush()
        _inv(db, b, c, "INV-0001", "100.00", InvoiceStatus.SENT, -10)
        paid = _inv(db, b, c, "INV-0002", "75.00", InvoiceStatus.PAID, 2)
        db.add(Payment(
            invoice_id=paid.id, business_id=b.id, paypal_order_id=uuid.uuid4().hex, paypal_capture_id=uuid.uuid4().hex,
            amount=Decimal("75.00"), currency="USD", status=PaymentStatus.COMPLETED,
        ))
        db.commit()
        try:
            s = insights_service.compute_stats(db, b.id)
            assert s["totals"]["overdue_total_usd"] == "100.00"
            assert s["totals"]["all_time_revenue_usd"] == "75.00"
            assert s["overdue_aging"][1]["count"] == 1          # 8-30 days bucket
            assert s["customer_patterns"][0]["customer"] == "Rahul"

            amounts = insights.allowed_amounts(s)
            assert insights._valid("You are owed $100.00 overdue.", amounts, None)
            assert not insights._valid("You are owed $101.00 overdue.", amounts, None)
            assert not insights._valid("Revenue is up 40%.", amounts, None)
            assert insights.deterministic_highlights(s)
        finally:
            db.rollback()
            db.execute(delete(Payment).where(Payment.business_id == b.id))
            db.execute(delete(Invoice).where(Invoice.business_id == b.id))
            db.execute(delete(Customer).where(Customer.business_id == b.id))
            db.execute(delete(Business).where(Business.id == b.id))
            db.commit()