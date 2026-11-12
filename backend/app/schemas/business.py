import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BusinessOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_name: str
    email: str
    business_name: str
    phone: str | None
    currency: str
    created_at: datetime


class BusinessUpdate(BaseModel):
    owner_name: str | None = Field(default=None, min_length=2, max_length=120)
    business_name: str | None = Field(default=None, min_length=2, max_length=160)
    phone: str | None = Field(default=None, max_length=32)