import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.core.deps import get_current_business
from app.core.errors import AppError
from app.db.session import get_db
from app.models import Business, Customer, Invoice, InvoiceStatus
from app.schemas.customer import CustomerCreate, CustomerOut, CustomerSummary

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("", response_model=list[CustomerSummary])
def list_customers(business: Business = Depends(get_current_business), db: Session = Depends(get_db)):
    paid = func.coalesce(func.sum(case((Invoice.status == InvoiceStatus.PAID, Invoice.amount), else_=0)), 0)
    outstanding = func.coalesce(
        func.sum(case((Invoice.status == InvoiceStatus.SENT, Invoice.amount), else_=0)), 0
    )
    rows = db.execute(
        select(Customer, func.count(Invoice.id), paid, outstanding)
        .outerjoin(Invoice, Invoice.customer_id == Customer.id)
        .where(Customer.business_id == business.id)
        .group_by(Customer.id)
        .order_by(Customer.name)
    ).all()
    return [
        CustomerSummary(
            id=c.id, name=c.name, email=c.email, phone=c.phone, created_at=c.created_at,
            invoice_count=count, total_paid=p, outstanding=o,
        )
        for c, count, p, o in rows
    ]


@router.post("", response_model=CustomerOut, status_code=201)
def create_customer(
    data: CustomerCreate, business: Business = Depends(get_current_business), db: Session = Depends(get_db)
):
    name = data.name.strip()
    exists = db.scalar(
        select(Customer).where(Customer.business_id == business.id, func.lower(Customer.name) == name.lower())
    )
    if exists:
        raise AppError("A customer with this name already exists", 409, "customer_exists")
    c = Customer(business_id=business.id, name=name, email=data.email, phone=data.phone)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


@router.get("/{customer_id}", response_model=CustomerOut)
def get_customer(
    customer_id: uuid.UUID, business: Business = Depends(get_current_business), db: Session = Depends(get_db)
):
    c = db.scalar(select(Customer).where(Customer.id == customer_id, Customer.business_id == business.id))
    if not c:
        raise AppError("Customer not found", 404, "not_found")
    return c