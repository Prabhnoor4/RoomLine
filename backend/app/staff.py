from fastapi import APIRouter, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db import engine
from app.models import HousekeepingRequest, MaintenanceTicket, Order, StaffEscalation, WakeUpCall
from app.schemas import StatusUpdate

router = APIRouter()

# Each type's status column only ever holds one of these values - a
# dropdown on the frontend is built from this same list, and the backend
# re-checks it here too so a bad request can't sneak in a made-up status.
HOUSEKEEPING_STATUSES = ["pending", "in_progress", "done"]


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


@router.post("/staff/checkout/{room_number}")
async def checkout(room_number: str) -> dict:
    # Imported here (not at the top of the file) to avoid a circular import -
    # main.py imports this router before `graph` exists, so importing it at
    # module load time would fail. By the time this endpoint actually runs,
    # the app has finished starting up and graph is set.
    from app.main import graph

    # Wipes the AI conversation history for this room so the next guest
    # doesn't inherit the previous guest's chat. Does NOT touch orders,
    # housekeeping requests, etc. - those stay as real staff-facing records.
    await graph.checkpointer.adelete_thread(room_number)

    return {"status": "cleared", "room_number": room_number}


@router.post("/staff/housekeeping/{request_id}/status")
async def update_housekeeping_status(request_id: int, body: StatusUpdate) -> dict:
    if body.status not in HOUSEKEEPING_STATUSES:
        raise HTTPException(status_code=400, detail=f"status must be one of {HOUSEKEEPING_STATUSES}")

    async with AsyncSession(engine) as session:
        result = await session.execute(
            select(HousekeepingRequest).where(HousekeepingRequest.id == request_id)
        )
        request = result.scalars().first()

        if request is None:
            raise HTTPException(status_code=404, detail="Housekeeping request not found")

        request.status = body.status
        session.add(request)
        await session.commit()

    return {"id": request_id, "status": body.status}


@router.post("/staff/wakeup/{call_id}/cancel")
async def cancel_wake_up_call(call_id: int) -> dict:
    # Wake-up calls don't have a status column at all - just this one
    # active flag - so there's no dropdown here, only a single cancel action.
    async with AsyncSession(engine) as session:
        result = await session.execute(
            select(WakeUpCall).where(WakeUpCall.id == call_id)
        )
        call = result.scalars().first()

        if call is None:
            raise HTTPException(status_code=404, detail="Wake-up call not found")

        call.active = False
        session.add(call)
        await session.commit()

    return {"id": call_id, "active": False}
