import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class ReminderOut(BaseModel):
    id: uuid.UUID
    invoice_id: uuid.UUID
    invoice_number: str
    customer_name: str
    amount: Decimal
    currency: str
    due_date: date
    invoice_status: str
    message: str
    status: str
    created_at: datetime
    approved_at: datetime | None


class ReminderEdit(BaseModel):
    message: str = Field(min_length=5, max_length=1500)


class ReminderCandidate(BaseModel):
    invoice_id: uuid.UUID
    number: str
    customer_name: str
    amount: Decimal
    currency: str
    due_date: date
    display_status: str
    days_overdue: int
    has_draft: bool
    last_reminded_at: datetime | None