from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from shared.renteasy_common import NotificationChannel, NotificationPayload, Role, Settings, Severity, has_permission

settings = Settings(service_name="notification-service", service_port=8408)
app = FastAPI(title="RentEasy Notification Service", version="1.0.0")


class NotificationRequest(BaseModel):
    channel: NotificationChannel
    recipient: str
    subject: str
    body: str
    severity: Severity = Severity.INFO
    actor_role: Role


class BookingNotificationRequest(BaseModel):
    host_id: str
    booking_id: str
    listing_id: str
    check_in: str
    check_out: str
    actor_role: Role


NotificationRequest.model_rebuild()
BookingNotificationRequest.model_rebuild()


messages: list[dict[str, Any]] = []


def _assert_permission(role: Role) -> None:
    if not has_permission(role, "notification:send"):
        raise HTTPException(status_code=403, detail="Forbidden")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.post("/notify/send")
async def send_notification(request: NotificationRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role)
    payload = NotificationPayload(
        channel=request.channel,
        recipient=request.recipient,
        subject=request.subject,
        body=request.body,
        severity=request.severity,
    ).model_dump(mode="json")
    payload["status"] = "queued"
    messages.append(payload)
    return payload


@app.post("/notify/booking-created")
async def notify_booking_created(request: BookingNotificationRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role)
    payload = NotificationPayload(
        channel=NotificationChannel.PUSH,
        recipient=request.host_id,
        subject=f"Новая бронь {request.booking_id}",
        body=f"По объекту {request.listing_id} создана бронь на период {request.check_in} - {request.check_out}.",
        severity=Severity.INFO,
    ).model_dump(mode="json")
    payload["status"] = "queued"
    messages.append(payload)
    return payload


@app.get("/notify/history")
async def history() -> dict[str, Any]:
    return {"items": messages, "count": len(messages)}
