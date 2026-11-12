import secrets
import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.errors import AppError
from app.models import Business, Customer, Invoice, InvoiceStatus
from app.schemas.invoice import InvoiceCreate, InvoiceOut


def effective_status(inv: Invoice) -> str:
    if inv.status == InvoiceStatus.SENT and inv.due_date < date.today():
        return "OVERDUE"
    return inv.status.value


def to_out(inv: Invoice) -> InvoiceOut:
    return InvoiceOut(
        id=inv.id,
        number=inv.number,
        customer_id=inv.customer_id,
        customer_name=inv.customer.name,
        description=inv.description,
        amount=inv.amount,
        currency=inv.currency,
        due_date=inv.due_date,
        status=inv.status.value,
        display_status=effective_status(inv),
        public_token=inv.public_token,
        created_at=inv.created_at,
    )


def _resolve_customer(db: Session, business: Business, data: InvoiceCreate) -> Customer:
    if data.customer_id:
        c = db.scalar(
            select(Customer).where(Customer.id == data.customer_id, Customer.business_id == business.id)
        )
        if not c:
            raise AppError("Customer not found", 404, "not_found")
        return c
    name = data.customer_name.strip()
    c = db.scalar(
        select(Customer).where(
            Customer.business_id == business.id, func.lower(Customer.name) == name.lower()
        )
    )
    if c:
        if data.customer_email and not c.email:
            c.email = data.customer_email
        return c
    c = Customer(business_id=business.id, name=name, email=data.customer_email)
    db.add(c)
    db.flush()
    return c


def _next_number(db: Session, business_id: uuid.UUID) -> str:
    count = db.scalar(select(func.count(Invoice.id)).where(Invoice.business_id == business_id)) or 0
    return f"INV-{count + 1:04d}"


def create_invoice(db: Session, business: Business, data: InvoiceCreate) -> Invoice:
    customer = _resolve_customer(db, business, data)
    inv = Invoice(
        business_id=business.id,
        customer_id=customer.id,
        number=_next_number(db, business.id),
        description=data.description.strip(),
        amount=data.amount,
        currency="USD",
        due_date=data.due_date,
        status=InvoiceStatus.DRAFT,
        public_token=secrets.token_urlsafe(24),
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)
    return inv


def get_invoice(db: Session, business_id: uuid.UUID, invoice_id: uuid.UUID) -> Invoice:
    inv = db.scalar(
        select(Invoice)
        .options(joinedload(Invoice.customer))
        .where(Invoice.id == invoice_id, Invoice.business_id == business_id)
    )
    if not inv:
        raise AppError("Invoice not found", 404, "not_found")
    return inv


def list_invoices(
    db: Session, business_id: uuid.UUID, status: str | None, limit: int, offset: int
) -> list[Invoice]:
    q = select(Invoice).options(joinedload(Invoice.customer)).where(Invoice.business_id == business_id)
    today = date.today()
    if status:
        s = status.upper()
        if s == "OVERDUE":
            q = q.where(Invoice.status == InvoiceStatus.SENT, Invoice.due_date < today)
        elif s == "PENDING":
            q = q.where(Invoice.status == InvoiceStatus.SENT, Invoice.due_date >= today)
        elif s in InvoiceStatus.__members__:
            q = q.where(Invoice.status == InvoiceStatus[s])
        else:
            raise AppError("Invalid status filter", 422, "validation_error")
    q = q.order_by(Invoice.created_at.desc()).limit(limit).offset(offset)
    return list(db.scalars(q).unique())


def send_invoice(db: Session, inv: Invoice) -> Invoice:
    if inv.status == InvoiceStatus.SENT:
        return inv
    if inv.status != InvoiceStatus.DRAFT:
        raise AppError(f"Cannot send a {inv.status.value.lower()} invoice", 409, "invalid_state")
    inv.status = InvoiceStatus.SENT
    db.commit()
    db.refresh(inv)
    return inv


def cancel_invoice(db: Session, inv: Invoice) -> Invoice:
    if inv.status == InvoiceStatus.CANCELLED:
        return inv
    if inv.status == InvoiceStatus.PAID:
        raise AppError("Paid invoices cannot be cancelled", 409, "invalid_state")
    inv.status = InvoiceStatus.CANCELLED
    db.commit()
    db.refresh(inv)
    return inv