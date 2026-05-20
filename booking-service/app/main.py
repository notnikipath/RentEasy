from __future__ import annotations

import asyncio
from datetime import date
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from shared.renteasy_common import (
    AvailabilityBlockRequest,
    AvailabilityCheckRequest,
    BookingCreateRequest,
    BookingRecord,
    BookingStatus,
    Role,
    Settings,
    build_audit_event,
    has_permission,
    parallel_booking_batches,
)

settings = Settings(service_name="booking-service", service_port=8403)
app = FastAPI(title="RentEasy Booking Service", version="1.0.0")


class BookingStatusRequest(BaseModel):
    actor_id: str
    actor_role: Role


BookingStatusRequest.model_rebuild()


bookings: dict[str, BookingRecord] = {}
blocked_calendar: dict[str, list[dict[str, Any]]] = {
    "LIST-DEMO-APT": [
        {"booking_id": "BOOK-SEED-1", "check_in": date(2026, 5, 25), "check_out": date(2026, 5, 31)},
    ]
}
audit_log: list[dict[str, Any]] = []
listing_locks: dict[str, asyncio.Lock] = {}


def _get_lock(listing_id: str) -> asyncio.Lock:
    lock = listing_locks.get(listing_id)
    if lock is None:
        lock = asyncio.Lock()
        listing_locks[listing_id] = lock
    return lock


def _assert_permission(role: Role, action: str) -> None:
    if not has_permission(role, action):
        raise HTTPException(status_code=403, detail=f"Role {role.value} cannot perform {action}")


def _audit(actor_id: str, actor_role: Role, action: str, object_id: str, details: dict[str, Any] | None = None) -> None:
    audit_log.append(
        build_audit_event(
            actor_id=actor_id,
            actor_role=actor_role,
            action=action,
            object_type="booking",
            object_id=object_id,
            details=details or {},
        ).model_dump(mode="json")
    )


def _overlap(left_start: date, left_end: date, right_start: date, right_end: date) -> bool:
    return left_start < right_end and right_start < left_end


def _is_available(listing_id: str, check_in: date, check_out: date, ignore_booking_id: str | None = None) -> bool:
    for item in blocked_calendar.get(listing_id, []):
        if ignore_booking_id and item["booking_id"] == ignore_booking_id:
            continue
        if _overlap(check_in, check_out, item["check_in"], item["check_out"]):
            return False
    return True


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.post("/availability/check")
async def check_availability(request: AvailabilityCheckRequest) -> dict[str, Any]:
    available = _is_available(request.listing_id, request.check_in, request.check_out)
    return {
        "listing_id": request.listing_id,
        "check_in": request.check_in,
        "check_out": request.check_out,
        "available": available,
    }


@app.get("/availability/{listing_id}")
async def listing_calendar(listing_id: str) -> dict[str, Any]:
    items = blocked_calendar.get(listing_id, [])
    return {
        "listing_id": listing_id,
        "blocked": [
            {
                "booking_id": item["booking_id"],
                "check_in": item["check_in"],
                "check_out": item["check_out"],
            }
            for item in items
        ],
        "count": len(items),
    }


@app.post("/bookings")
async def create_booking(request: BookingCreateRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "booking:create")

    nights = (request.check_out - request.check_in).days
    if nights <= 0:
        raise HTTPException(status_code=400, detail="check_out must be greater than check_in")

    if not _is_available(request.listing_id, request.check_in, request.check_out):
        raise HTTPException(status_code=409, detail="Dates not available")

    booking = BookingRecord(
        booking_id=str(uuid4()),
        user_id=request.user_id,
        host_id=request.host_id,
        listing_id=request.listing_id,
        check_in=request.check_in,
        check_out=request.check_out,
        guests=request.guests,
        nights=nights,
        nightly_price=request.nightly_price,
        total_price=request.total_price,
        deposit=request.deposit,
        status=BookingStatus.PENDING_PAYMENT,
    )
    bookings[booking.booking_id] = booking
    _audit(request.actor_id, request.actor_role, "booking.create", booking.booking_id)
    return booking.model_dump(mode="json")


@app.post("/availability/block")
async def block_dates(request: AvailabilityBlockRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "booking:update")
    booking = bookings.get(request.booking_id)
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")

    lock = _get_lock(request.listing_id)
    async with lock:
        if not _is_available(
            request.listing_id,
            request.check_in,
            request.check_out,
            ignore_booking_id=request.booking_id,
        ):
            raise HTTPException(status_code=409, detail="Dates already blocked")
        blocked_calendar.setdefault(request.listing_id, []).append(
            {
                "booking_id": request.booking_id,
                "check_in": request.check_in,
                "check_out": request.check_out,
            }
        )

    _audit(request.actor_id, request.actor_role, "booking.block_dates", request.booking_id)
    return {
        "booking_id": request.booking_id,
        "listing_id": request.listing_id,
        "status": "blocked",
    }


@app.post("/bookings/{booking_id}/confirm")
async def confirm_booking(booking_id: str, request: BookingStatusRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "booking:update")
    booking = bookings.get(booking_id)
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    booking.status = BookingStatus.CONFIRMED
    _audit(request.actor_id, request.actor_role, "booking.confirm", booking_id)
    return booking.model_dump(mode="json")


@app.post("/bookings/{booking_id}/cancel")
async def cancel_booking(booking_id: str, request: BookingStatusRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "booking:update")
    booking = bookings.get(booking_id)
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")

    booking.status = BookingStatus.CANCELLED
    blocked_items = blocked_calendar.get(booking.listing_id, [])
    blocked_calendar[booking.listing_id] = [item for item in blocked_items if item["booking_id"] != booking_id]

    _audit(request.actor_id, request.actor_role, "booking.cancel", booking_id)
    return booking.model_dump(mode="json")


@app.get("/bookings/{booking_id}")
async def get_booking(booking_id: str) -> dict[str, Any]:
    booking = bookings.get(booking_id)
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking.model_dump(mode="json")


@app.get("/bookings/user/{user_id}")
async def user_bookings(user_id: str) -> dict[str, Any]:
    items = [booking.model_dump(mode="json") for booking in bookings.values() if booking.user_id == user_id]
    return {"items": items, "count": len(items)}


@app.get("/bookings/host/{host_id}")
async def host_bookings(host_id: str) -> dict[str, Any]:
    items = [booking.model_dump(mode="json") for booking in bookings.values() if booking.host_id == host_id]
    return {"items": items, "count": len(items)}


@app.get("/bookings/parallel-plan")
async def parallel_plan(total_bookings: int = 4800, workers: int = 8) -> dict[str, Any]:
    booking_ids = [f"BK-{index:05d}" for index in range(1, total_bookings + 1)]
    batches = parallel_booking_batches(booking_ids, workers)
    return {
        "workers": workers,
        "batches": len(batches),
        "largest_batch": max((len(batch) for batch in batches), default=0),
    }


@app.get("/audit")
async def get_audit(limit: int = 100, actor_role: Role = Role.ADMIN) -> dict[str, Any]:
    _assert_permission(actor_role, "audit:read")
    return {"items": audit_log[-limit:]}
