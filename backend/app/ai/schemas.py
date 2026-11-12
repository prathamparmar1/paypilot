from typing import Optional

from pydantic import BaseModel


class ParsedInvoiceLLM(BaseModel):
    customer_name: Optional[str]
    customer_email: Optional[str]
    description: Optional[str]
    amount: Optional[float]
    currency: Optional[str]
    due_date: Optional[str]
    due_in_days: Optional[int]