import uuid
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import CheckConstraint, Date, Enum, ForeignKey, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.base import CreatedAt, UUIDPk
from app.models.enums import InvoiceStatus


class Invoice(Base, UUIDPk, CreatedAt):
    __tablename__ = "invoices"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_invoice_amount_positive"),
        UniqueConstraint("business_id", "number", name="uq_invoice_business_number"),
        Index("ix_invoice_business_status", "business_id", "status"),
        Index("ix_invoice_business_due", "business_id", "due_date"),
    )

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    number: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[InvoiceStatus] = mapped_column(
        Enum(InvoiceStatus, name="invoice_status"), default=InvoiceStatus.DRAFT, nullable=False
    )
    public_token: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    paypal_order_id: Mapped[Optional[str]] = mapped_column(String(64), index=True)

    business = relationship("Business", back_populates="invoices")
    customer = relationship("Customer", back_populates="invoices")
    payments = relationship("Payment", back_populates="invoice")
    reminders = relationship("Reminder", back_populates="invoice")