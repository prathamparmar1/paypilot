import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import delete

from app.ai import actions
from app.ai.tools import ToolContext, execute_tool
from app.core.errors import AppError
from app.db.session import SessionLocal
from app.models import (
    Business, Customer, Invoice, InvoiceStatus, Payment, PaymentStatus, PendingAction,
)


def _biz(db):
    b = Business(owner_name="O", business_name="B", email=f"as_{uuid.uuid4().hex[:8]}@e.com", password_hash="x")
    db.add(b); db.flush()
    return b


def _inv(db, b, c, n, amount, status, due_days):
    i = Invoice(
        business_id=b.id, customer_id=c.id, number=n, description="svc", amount=Decimal(amount),
        currency="USD", due_date=date.today() + timedelta(days=due_days), status=status,
        public_token=uuid.uuid4().hex,
    )
    db.add(i); db.flush()
    return i


def test_tools_confirmation_and_isolation():
    with SessionLocal() as db:
        b1, b2 = _biz(db), _biz(db)
        c = Customer(business_id=b1.id, name="Rahul"); db.add(c); db.flush()
        _inv(db, b1, c, "INV-0001", "100.00", InvoiceStatus.SENT, -3)   # overdue
        _inv(db, b1, c, "INV-0002", "50.00", InvoiceStatus.SENT, 5)     # pending
        d = _inv(db, b1, c, "INV-0003", "20.00", InvoiceStatus.DRAFT, 5)
        paid = _inv(db, b1, c, "INV-0004", "75.00", InvoiceStatus.PAID, 1)
        db.add(Payment(
            invoice_id=paid.id, business_id=b1.id, paypal_order_id="O1", paypal_capture_id="C1",
            amount=Decimal("75.00"), currency="USD", status=PaymentStatus.COMPLETED,
        ))
        db.commit()
        ctx1, ctx2 = ToolContext(db, b1), ToolContext(db, b2)
        try:
            out = execute_tool(ctx1, "get_outstanding_total", {})
            assert out["unpaid_total_usd"] == "150.00" and out["overdue_total_usd"] == "100.00"
            assert execute_tool(ctx1, "get_revenue", {"period": "all_time"})["total_revenue_usd"] == "75.00"
            ov = execute_tool(ctx1, "list_invoices", {"status": "OVERDUE"})
            assert ov["count"] == 1 and ov["invoices"][0]["number"] == "INV-0001"

            # isolation + bad args
            assert execute_tool(ctx2, "list_invoices", {})["count"] == 0
            assert "error" in execute_tool(ctx2, "get_invoice_details", {"invoice_number": "INV-0001"})
            assert "error" in execute_tool(ctx1, "get_revenue", {"period": "nonsense"})
            assert "error" in execute_tool(ctx1, "drop_database", {})

            # write tool only proposes
            assert "error" in execute_tool(ctx1, "send_invoice", {"invoice_number": "INV-0002"})  # not draft
            res = execute_tool(ctx1, "send_invoice", {"invoice_number": "INV-0003"})
            assert res["status"] == "awaiting_user_confirmation"
            db.refresh(d)
            assert d.status == InvoiceStatus.DRAFT
            action_id = ctx1.pending[0]

            # other business cannot confirm it
            with pytest.raises(AppError) as e:
                actions.confirm_action(db, b2, action_id)
            assert e.value.status_code == 404

            inv, _ = actions.confirm_action(db, b1, action_id)
            assert inv.status == InvoiceStatus.SENT
            with pytest.raises(AppError) as e:   # single use
                actions.confirm_action(db, b1, action_id)
            assert e.value.status_code == 409
        finally:
            db.rollback()
            ids = [b1.id, b2.id]
            db.execute(delete(PendingAction).where(PendingAction.business_id.in_(ids)))
            db.execute(delete(Payment).where(Payment.business_id.in_(ids)))
            db.execute(delete(Invoice).where(Invoice.business_id.in_(ids)))
            db.execute(delete(Customer).where(Customer.business_id.in_(ids)))
            db.execute(delete(Business).where(Business.id.in_(ids)))
            db.commit()