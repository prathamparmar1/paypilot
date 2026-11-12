import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.base import CreatedAt, UUIDPk
from app.models.enums import ReminderStatus


class Reminder(Base, UUIDPk, CreatedAt):
    __tablename__ = "reminders"

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), index=True, nullable=False
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="CASCADE"), index=True, nullable=False
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[ReminderStatus] = mapped_column(
        Enum(ReminderStatus, name="reminder_status"), default=ReminderStatus.DRAFT, nullable=False
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    invoice = relationship("Invoice", back_populates="reminders")