import uuid
from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.db.session import SessionLocal
from app.main import app
from app.models import Business, Customer, Invoice

client = TestClient(app)
B = "/api/v1"


def _register():
    email = f"t_{uuid.uuid4().hex[:8]}@example.com"
    r = client.post(
        f"{B}/auth/register",
        json={"owner_name": "Owner", "business_name": "Biz", "email": email, "password": "StrongPass123"},
    )
    return email, {"Authorization": f"Bearer {r.json()['access_token']}"}


def _cleanup(emails):
    with SessionLocal() as db:
        ids = [b.id for b in db.query(Business).filter(Business.email.in_(emails))]
        db.execute(delete(Invoice).where(Invoice.business_id.in_(ids)))
        db.execute(delete(Customer).where(Customer.business_id.in_(ids)))
        db.execute(delete(Business).where(Business.id.in_(ids)))
        db.commit()


def test_invoice_lifecycle_and_isolation():
    e1, h1 = _register()
    e2, h2 = _register()
    try:
        body = {
            "customer_name": "Rahul",
            "description": "Haircut and grooming",
            "amount": "2000.00",
            "due_date": str(date.today() + timedelta(days=5)),
        }
        r = client.post(f"{B}/invoices", json=body, headers=h1)
        assert r.status_code == 201
        inv = r.json()
        assert inv["status"] == "DRAFT" and inv["number"] == "INV-0001"

        # validation
        assert client.post(f"{B}/invoices", json={**body, "amount": "-5"}, headers=h1).status_code == 422
        past = {**body, "due_date": str(date.today() - timedelta(days=1))}
        assert client.post(f"{B}/invoices", json=past, headers=h1).status_code == 422

        # lifecycle
        assert client.post(f"{B}/invoices/{inv['id']}/send", headers=h1).json()["status"] == "SENT"
        assert client.get(f"{B}/invoices?status=PENDING", headers=h1).json()[0]["id"] == inv["id"]
        assert client.get(f"{B}/invoices?status=OVERDUE", headers=h1).json() == []

        # isolation: other business cannot see/modify
        assert client.get(f"{B}/invoices/{inv['id']}", headers=h2).status_code == 404
        assert client.post(f"{B}/invoices/{inv['id']}/cancel", headers=h2).status_code == 404
        assert client.get(f"{B}/invoices", headers=h2).json() == []

        s = client.get(f"{B}/dashboard/summary", headers=h1).json()
        assert s["pending_count"] == 1 and float(s["pending_amount"]) == 2000.0
        assert float(s["total_revenue"]) == 0.0

        assert client.post(f"{B}/invoices/{inv['id']}/cancel", headers=h1).json()["status"] == "CANCELLED"
        assert client.post(f"{B}/invoices/{inv['id']}/send", headers=h1).status_code == 409

        c = client.get(f"{B}/customers", headers=h1).json()
        assert c[0]["name"] == "Rahul" and c[0]["invoice_count"] == 1
    finally:
        _cleanup([e1, e2])