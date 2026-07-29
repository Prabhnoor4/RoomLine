from datetime import datetime

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db import engine
from app.hotel_config import load_hotel_config
from app.models import HousekeepingRequest, MaintenanceTicket, WakeUpCall


@tool
def get_room_service_menu() -> list[dict]:
    """Get the hotel's current room service menu, with item names, categories, prices, and descriptions."""
    config = load_hotel_config()
    return config["menu_items"]


@tool
async def submit_housekeeping_request(request_type: str, config: RunnableConfig, notes: str = "") -> dict:
    """Submit a housekeeping request for items the guest wants, for example: towels, pillows, cleaning, do-not-disturb."""
    room_number = config["configurable"]["room_number"]

    async with AsyncSession(engine) as session:
        new_request = HousekeepingRequest(
            room_number=room_number,
            request_type=request_type,
            notes=notes,
        )
        session.add(new_request)
        await session.commit()
        await session.refresh(new_request)

    return {"ticket_id": new_request.id, "status": new_request.status}

@tool
async def report_maintenance_issue(description: str, config: RunnableConfig, urgency: str = "normal") -> dict:
    """Report something broken or not functioning properly, for example: AC not working, leaky faucet etc."""
    room_number = config["configurable"]["room_number"]

    async with AsyncSession(engine) as session:
        new_request = MaintenanceTicket(
            room_number=room_number,
            description=description,
            urgency=urgency,
        )
        session.add(new_request)
        await session.commit()
        await session.refresh(new_request)

    return {"ticket_id": new_request.id, "status": new_request.status}

@tool
async def schedule_wake_up_call(time: datetime, config: RunnableConfig) -> dict:
    """Schedule a wake-up call for the guest's room at the given time."""
    room_number = config["configurable"]["room_number"]

    async with AsyncSession(engine) as session:
        new_call = WakeUpCall(
            room_number=room_number,
            time=time,
        )
        session.add(new_call)
        await session.commit()
        await session.refresh(new_call)

    return {"wake_up_call_id": new_call.id, "time": str(new_call.time), "status": "scheduled"}


@tool
async def cancel_wake_up_call(config: RunnableConfig) -> dict:
    """Cancel the guest's currently scheduled wake-up call, if one exists."""
    room_number = config["configurable"]["room_number"]

    async with AsyncSession(engine) as session:
        result = await session.exec(
            select(WakeUpCall).where(
                WakeUpCall.room_number == room_number,
                WakeUpCall.active == True,
            )
        )
        existing_call = result.first()

        if existing_call is None:
            return {"status": "no_active_wake_up_call"}

        existing_call.active = False
        session.add(existing_call)
        await session.commit()

    return {"wake_up_call_id": existing_call.id, "status": "cancelled"}
