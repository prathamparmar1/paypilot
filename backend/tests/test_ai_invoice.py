import uuid

from sqlalchemy import delete

from app.ai import invoice_parser
from app.db.session import SessionLocal
from app.models import Business, Customer


def _llm(**kw):
    base = dict(customer_name=None, customer_email=None, description=None, amount=None,
                currency=None, due_date=None, due_in_days=None)
    base.update(kw)
    return lambda *a, **k: base


def test_parser_guardrails(monkeypatch):
    with SessionLocal() as db:
        b = Business(owner_name="O", business_name="B", email=f"a_{uuid.uuid4().hex[:8]}@e.com", password_hash="x")
        db.add(b); db.flush()
        db.add(Customer(business_id=b.id, name="Rahul Sharma")); db.commit()
        try:
            text = "Create an invoice for Rahul for 2,000 for haircut and grooming, due in 5 days"
            ok = dict(customer_name="Rahul", description="haircut and grooming", amount=2000, due_in_days=5)

            monkeypatch.setattr(invoice_parser, "generate_json", _llm(**ok))
            r = invoice_parser.parse_invoice_text(db, b.id, text)
            assert r.status == "ready" and str(r.draft.amount) == "2000.00"
            assert [s.name for s in r.similar_customers] == ["Rahul Sharma"]

            # hallucinated amount (not in text) -> asks again
            monkeypatch.setattr(invoice_parser, "generate_json", _llm(**{**ok, "amount": 9999}))
            r = invoice_parser.parse_invoice_text(db, b.id, text)
            assert r.status == "needs_clarification" and "amount" in r.missing_fields

            # missing due date
            monkeypatch.setattr(invoice_parser, "generate_json", _llm(**{**ok, "due_in_days": None}))
            r = invoice_parser.parse_invoice_text(db, b.id, text)
            assert r.missing_fields == ["due_date"]

            # non-USD currency
            monkeypatch.setattr(invoice_parser, "generate_json", _llm(**{**ok, "currency": "INR"}))
            r = invoice_parser.parse_invoice_text(db, b.id, text)
            assert r.status == "needs_clarification" and "USD" in r.question

            # invented customer name
            monkeypatch.setattr(invoice_parser, "generate_json", _llm(**{**ok, "customer_name": "Priya"}))
            r = invoice_parser.parse_invoice_text(db, b.id, text)
            assert "customer_name" in r.missing_fields
        finally:
            db.execute(delete(Customer).where(Customer.business_id == b.id))
            db.execute(delete(Business).where(Business.id == b.id))
            db.commit()