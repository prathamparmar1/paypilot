import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


class PublicInvoice(BaseModel):
    business_name: str
    number: str
    customer_name: str
    description: str
    amount: Decimal
    currency: str
    due_date: date
    status: str
    display_status: str
    paypal_client_id: str


class OrderOut(BaseModel):
    order_id: str


class CaptureRequest(BaseModel):
    order_id: str


class CaptureOut(BaseModel):
    invoice_status: str


class PaymentOut(BaseModel):
    id: uuid.UUID
    invoice_id: uuid.UUID
    invoice_number: str
    customer_name: str
    amount: Decimal
    currency: str
    status: str
    paypal_order_id: str
    paypal_capture_id: str
    payer_email: str | None
    verified_at: datetime