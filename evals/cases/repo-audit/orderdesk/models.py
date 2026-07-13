"""Pydantic request/response models."""
from enum import Enum

from pydantic import BaseModel, Field


class Priority(str, Enum):
    low = "low"
    normal = "normal"
    high = "high"


class OrderStatus(str, Enum):
    pending = "pending"
    paid = "paid"
    shipped = "shipped"
    cancelled = "cancelled"


class OrderCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    notes: str = Field(default="", max_length=2000)
    priority: Priority = Priority.normal
    callback_url: str | None = Field(default=None, max_length=500)


class OrderUpdate(BaseModel):
    """Fields a client may send on a PATCH. Applied by the service layer."""
    title: str | None = Field(default=None, min_length=1, max_length=200)
    notes: str | None = Field(default=None, max_length=2000)
    priority: Priority | None = None
    status: OrderStatus | None = None
    amount_cents: int | None = None
    user_id: int | None = None


class OrderOut(BaseModel):
    id: int
    title: str
    notes: str
    priority: Priority
    status: OrderStatus
    amount_cents: int


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=12, max_length=200)
