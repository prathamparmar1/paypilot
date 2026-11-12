import uuid
from typing import Optional

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.base import CreatedAt, UUIDPk


class Customer(Base, UUIDPk, CreatedAt):
    __tablename__ = "customers"
    __table_args__ = (UniqueConstraint("business_id", "name", name="uq_customer_business_name"),)

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255))
    phone: Mapped[Optional[str]] = mapped_column(String(32))

    business = relationship("Business", back_populates="customers")
    invoices = relationship("Invoice", back_populates="customer")