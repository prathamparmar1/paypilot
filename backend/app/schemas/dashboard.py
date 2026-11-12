import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class RecentPayment(BaseModel):
    id: uuid.UUID
    invoice_number: str
    customer_name: str
    amount: Decimal
    currency: str
    verified_at: datetime


class DashboardSummary(BaseModel):
    total_revenue: Decimal
    pending_amount: Decimal
    pending_count: int
    overdue_amount: Decimal
    overdue_count: int
    paid_count: int
    recent_payments: list[RecentPayment]