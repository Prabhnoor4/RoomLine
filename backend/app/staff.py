from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db import engine
from app.models import HousekeepingRequest, MaintenanceTicket, Order, StaffEscalation, WakeUpCall

router = APIRouter()


@router.get("/staff/requests")
async def staff_requests() -> dict:
    async with AsyncSession(engine) as session:
        result = await session.execute(
            select(HousekeepingRequest).where(HousekeepingRequest.status != "done")
        )
        housekeeping = result.scalars().all()
        
        maintenance_result = await session.execute(
            select(MaintenanceTicket).where(MaintenanceTicket.status != "resolved")
        )
        maintenance = maintenance_result.scalars().all()

        orders_result = await session.execute(
            select(Order).where(Order.status != "delivered")
        )
        orders = orders_result.scalars().all()

        wake_up_calls_result = await session.execute(
            select(WakeUpCall).where(WakeUpCall.active == True)
        )
        wake_up_calls = wake_up_calls_result.scalars().all()

        escalations_result = await session.execute(
            select(StaffEscalation).where(StaffEscalation.status != "resolved")
        )
        escalations = escalations_result.scalars().all()

    return {
        "housekeeping": housekeeping,
        "maintenance": maintenance,
        "orders": orders,
        "wake_up_calls": wake_up_calls,
        "escalations": escalations,
    }
