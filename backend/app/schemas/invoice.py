import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


class InvoiceCreate(BaseModel):
    customer_id: uuid.UUID | None = None
    customer_name: str | None = Field(default=None, max_length=160)
    customer_email: EmailStr | None = None
    description: str = Field(min_length=3, max_length=500)
    amount: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    due_date: date

    @field_validator("due_date")
    @classmethod
    def not_past(cls, v: date) -> date:
        if v < date.today():
            raise ValueError("Due date cannot be in the past")
        return v

    @model_validator(mode="after")
    def need_customer(self):
        if not self.customer_id and not (self.customer_name and self.customer_name.strip()):
            raise ValueError("Provide customer_id or customer_name")
        return self


class InvoiceOut(BaseModel):
    id: uuid.UUID
    number: str
    customer_id: uuid.UUID
    customer_name: str
    description: str
    amount: Decimal
    currency: str
    due_date: date
    status: str
    display_status: str
    public_token: str
    created_at: datetime