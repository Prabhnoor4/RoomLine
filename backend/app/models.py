from datetime import datetime, timezone
from typing import Optional

from sqlmodel import SQLModel, Field


class MenuItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    category: str  # breakfast | mains | drinks | dessert
    price: float
    description: str
    available: bool = True


class Order(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    room_number: str
    items_json: str  # JSON-encoded list of {"name": ..., "quantity": ...}
    notes: Optional[str] = None
    status: str = "received"  # received | preparing | delivered
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class HousekeepingRequest(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    room_number: str
    request_type: str  # towels | pillows | cleaning | do_not_disturb | toiletries
    notes: Optional[str] = None
    status: str = "pending"  # pending | in_progress | done
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MaintenanceTicket(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    room_number: str
    description: str
    urgency: str = "normal"  # low | normal | high
    status: str = "open"  # open | in_progress | resolved
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class WakeUpCall(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    room_number: str
    time: datetime
    active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class StaffEscalation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    room_number: str
    reason: str
    status: str = "open"  # open | resolved
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

