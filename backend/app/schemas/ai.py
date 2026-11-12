import uuid
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.invoice import InvoiceCreate
from datetime import datetime 
from app.schemas.invoice import InvoiceOut


class ParseRequest(BaseModel):
    text: str = Field(min_length=3, max_length=1000)


class InvoiceDraft(BaseModel):
    customer_name: str | None = None
    customer_email: str | None = None
    description: str | None = None
    amount: Decimal | None = None
    due_date: date | None = None


class SimilarCustomer(BaseModel):
    id: uuid.UUID
    name: str


class ParseOut(BaseModel):
    status: Literal["ready", "needs_clarification"]
    draft: InvoiceDraft
    missing_fields: list[str]
    question: str | None = None
    existing_customer: bool = False
    similar_customers: list[SimilarCustomer] = []


class InvoiceConfirm(InvoiceCreate):
    send: bool = False
    
class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)


class PendingActionOut(BaseModel):
    id: uuid.UUID
    action_type: str
    summary: str
    expires_at: datetime


class ChatOut(BaseModel):
    reply: str
    pending_actions: list[PendingActionOut]
    tools_used: list[str]


class MessageOut(BaseModel):
    role: str
    content: str
    created_at: datetime


class HistoryOut(BaseModel):
    messages: list[MessageOut]
    pending_actions: list[PendingActionOut]


class ActionResultOut(BaseModel):
    message: str
    invoice: InvoiceOut | None = None