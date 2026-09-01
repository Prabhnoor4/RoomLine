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
HOUSEKEEPING_STATUSES = ["pending", "in_progress", "done", "cancelled"]
MAINTENANCE_STATUSES = ["open", "in_progress", "resolved"]
ORDER_STATUSES = ["received", "preparing", "delivered", "cancelled"]
ESCALATION_STATUSES = ["open", "resolved"]


@router.get("/staff/requests")
async def staff_requests() -> dict:
    async with AsyncSession(engine) as session:
        result = await session.execute(
            select(HousekeepingRequest).where(
                HousekeepingRequest.status != "done",
                HousekeepingRequest.status != "cancelled",
            )
        )
        housekeeping = result.scalars().all()

        maintenance_result = await session.execute(
            select(MaintenanceTicket).where(MaintenanceTicket.status != "resolved")
        )
        maintenance = maintenance_result.scalars().all()

        orders_result = await session.execute(
            select(Order).where(
                Order.status != "delivered",
                Order.status != "cancelled",
            )
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


async def count_outstanding(room_number: str) -> dict:
    """Count everything still unfinished for one room, per category.

    This is a plain helper, not an endpoint - checkout() calls it directly so
    the "is this room still busy?" rule lives in one place.
    """
    async with AsyncSession(engine) as session:
        housekeeping_result = await session.execute(
            select(HousekeepingRequest).where(
                HousekeepingRequest.room_number == room_number,
                HousekeepingRequest.status != "done",
                HousekeepingRequest.status != "cancelled",
            )
        )
        housekeeping = housekeeping_result.scalars().all()

        maintenance_result = await session.execute(
            select(MaintenanceTicket).where(
                MaintenanceTicket.room_number == room_number,
                MaintenanceTicket.status != "resolved",
            )
        )
        maintenance = maintenance_result.scalars().all()

        orders_result = await session.execute(
            select(Order).where(
                Order.room_number == room_number,
                Order.status != "delivered",
                Order.status != "cancelled",
            )
        )
        orders = orders_result.scalars().all()

        wake_up_calls_result = await session.execute(
            select(WakeUpCall).where(
                WakeUpCall.room_number == room_number,
                WakeUpCall.active == True,
            )
        )
        wake_up_calls = wake_up_calls_result.scalars().all()

        escalations_result = await session.execute(
            select(StaffEscalation).where(
                StaffEscalation.room_number == room_number,
                StaffEscalation.status != "resolved",
            )
        )
        escalations = escalations_result.scalars().all()

    return {
        "housekeeping": len(housekeeping),
        "maintenance": len(maintenance),
        "orders": len(orders),
        "wake_up_calls": len(wake_up_calls),
        "escalations": len(escalations),
    }


async def cancel_guest_requests(room_number: str) -> dict:
    """Cancel the leftover requests that only made sense while the guest was here.

    Maintenance tickets and escalations are deliberately NOT cancelled - a
    leaking faucet is still leaking after the guest leaves (and wants fixing
    before the next one arrives), and an escalation still needs a human to
    follow up on it.
    """
    async with AsyncSession(engine) as session:
        housekeeping_result = await session.execute(
            select(HousekeepingRequest).where(
                HousekeepingRequest.room_number == room_number,
                HousekeepingRequest.status != "done",
                HousekeepingRequest.status != "cancelled",
            )
        )
        housekeeping = housekeeping_result.scalars().all()
        for request in housekeeping:
            request.status = "cancelled"
            session.add(request)

        orders_result = await session.execute(
            select(Order).where(
                Order.room_number == room_number,
                Order.status != "delivered",
                Order.status != "cancelled",
            )
        )
        orders = orders_result.scalars().all()
        for order in orders:
            order.status = "cancelled"
            session.add(order)

        wake_up_calls_result = await session.execute(
            select(WakeUpCall).where(
                WakeUpCall.room_number == room_number,
                WakeUpCall.active == True,
            )
        )
        wake_up_calls = wake_up_calls_result.scalars().all()
        for call in wake_up_calls:
            call.active = False
            session.add(call)

        await session.commit()

    return {
        "housekeeping": len(housekeeping),
        "orders": len(orders),
        "wake_up_calls": len(wake_up_calls),
    }


@router.post("/staff/checkout/{room_number}")
async def checkout(room_number: str, force: bool = False) -> dict:
    counts = await count_outstanding(room_number)
    total = sum(counts.values())

    # Refuse to clear a room that still has unfinished work, unless the caller
    # explicitly passes ?force=true. Keeping this check in the backend - rather
    # than only in the dashboard - means it applies to every caller, not just
    # people using our page.
    if total > 0 and not force:
        return {
            "status": "needs_confirmation",
            "room_number": room_number,
            "counts": counts,
            "total": total,
        }

    # Imported here (not at the top of the file) to avoid a circular import -
    # main.py imports this router before `graph` exists, so importing it at
    # module load time would fail. By the time this endpoint actually runs,
    # the app has finished starting up and graph is set.
    from app.main import graph

    # Wipes the AI conversation history for this room so the next guest
    # doesn't inherit the previous guest's chat.
    await graph.checkpointer.adelete_thread(room_number)

    # Guest-specific requests get cancelled rather than left hanging - but the
    # records themselves stay in the database, just marked "cancelled" so the
    # history stays honest about what actually happened.
    cancelled = await cancel_guest_requests(room_number)

    return {"status": "cleared", "room_number": room_number, "cancelled": cancelled}


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


@router.post("/staff/maintenance/{ticket_id}/status")
async def update_maintenance_status(ticket_id: int, body: StatusUpdate) -> dict:
    if body.status not in MAINTENANCE_STATUSES:
        raise HTTPException(status_code=400, detail=f"status must be one of {MAINTENANCE_STATUSES}")

    async with AsyncSession(engine) as session:
        result = await session.execute(
            select(MaintenanceTicket).where(MaintenanceTicket.id == ticket_id)
        )
        ticket = result.scalars().first()

        if ticket is None:
            raise HTTPException(status_code=404, detail="Maintenance ticket not found")

        ticket.status = body.status
        session.add(ticket)
        await session.commit()

    return {"id": ticket_id, "status": body.status}


@router.post("/staff/orders/{order_id}/status")
async def update_order_status(order_id: int, body: StatusUpdate) -> dict:
    if body.status not in ORDER_STATUSES:
        raise HTTPException(status_code=400, detail=f"status must be one of {ORDER_STATUSES}")

    async with AsyncSession(engine) as session:
        result = await session.execute(
            select(Order).where(Order.id == order_id)
        )
        order = result.scalars().first()

        if order is None:
            raise HTTPException(status_code=404, detail="Order not found")

        order.status = body.status
        session.add(order)
        await session.commit()

    return {"id": order_id, "status": body.status}


@router.post("/staff/escalations/{escalation_id}/status")
async def update_escalation_status(escalation_id: int, body: StatusUpdate) -> dict:
    if body.status not in ESCALATION_STATUSES:
        raise HTTPException(status_code=400, detail=f"status must be one of {ESCALATION_STATUSES}")

    async with AsyncSession(engine) as session:
        result = await session.execute(
            select(StaffEscalation).where(StaffEscalation.id == escalation_id)
        )
        escalation = result.scalars().first()

        if escalation is None:
            raise HTTPException(status_code=404, detail="Escalation not found")

        escalation.status = body.status
        session.add(escalation)
        await session.commit()

    return {"id": escalation_id, "status": body.status}


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
