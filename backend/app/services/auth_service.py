from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import create_access_token, hash_password, verify_password
from app.models import Business
from app.schemas.auth import LoginRequest, RegisterRequest


def register_business(db: Session, data: RegisterRequest) -> str:
    email = data.email.lower()
    if db.scalar(select(Business).where(Business.email == email)):
        raise AppError("Email already registered", 409, "email_exists")
    business = Business(
        owner_name=data.owner_name,
        business_name=data.business_name,
        email=email,
        phone=data.phone,
        password_hash=hash_password(data.password),
        currency="USD",
    )
    db.add(business)
    db.commit()
    db.refresh(business)
    return create_access_token(business.id)


def login_business(db: Session, data: LoginRequest) -> str:
    business = db.scalar(select(Business).where(Business.email == data.email.lower()))
    if not business or not verify_password(data.password, business.password_hash):
        raise AppError("Invalid email or password", 401, "invalid_credentials")
    return create_access_token(business.id)