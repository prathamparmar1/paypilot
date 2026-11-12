import uuid

from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.db.session import SessionLocal
from app.main import app
from app.models import Business

client = TestClient(app)
BASE = "/api/v1"


def _cleanup(email: str):
    with SessionLocal() as db:
        db.execute(delete(Business).where(Business.email == email))
        db.commit()


def test_register_login_profile_flow():
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "owner_name": "Test Owner",
        "business_name": "Test Salon",
        "email": email,
        "password": "StrongPass123",
    }
    try:
        r = client.post(f"{BASE}/auth/register", json=payload)
        assert r.status_code == 201
        token = r.json()["access_token"]

        # duplicate
        assert client.post(f"{BASE}/auth/register", json=payload).status_code == 409

        # bad login
        bad = client.post(f"{BASE}/auth/login", json={"email": email, "password": "wrongpass1"})
        assert bad.status_code == 401

        # good login
        ok = client.post(f"{BASE}/auth/login", json={"email": email, "password": "StrongPass123"})
        assert ok.status_code == 200

        headers = {"Authorization": f"Bearer {token}"}
        me = client.get(f"{BASE}/business/me", headers=headers)
        assert me.status_code == 200
        assert me.json()["email"] == email
        assert me.json()["currency"] == "USD"
        assert "password_hash" not in me.json()

        up = client.patch(f"{BASE}/business/me", json={"business_name": "New Name"}, headers=headers)
        assert up.status_code == 200
        assert up.json()["business_name"] == "New Name"

        # unauthenticated
        assert client.get(f"{BASE}/business/me").status_code == 401
        assert client.get(f"{BASE}/business/me", headers={"Authorization": "Bearer junk"}).status_code == 401
    finally:
        _cleanup(email)