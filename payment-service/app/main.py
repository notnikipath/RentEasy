from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from shared.renteasy_common import PaymentIntentRequest, PaymentRecord, PaymentStatus, Role, Settings, has_permission

settings = Settings(service_name="payment-service", service_port=8404)
app = FastAPI(title="RentEasy Payment Service", version="1.0.0")


class PaymentActionRequest(BaseModel):
    actor_id: str
    actor_role: Role


PaymentActionRequest.model_rebuild()


payments: dict[str, PaymentRecord] = {}


def _assert_any_permission(role: Role, actions: list[str]) -> None:
    if not any(has_permission(role, action) for action in actions):
        raise HTTPException(status_code=403, detail=f"Role {role.value} cannot perform this action")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.post("/payments/intent")
async def create_intent(request: PaymentIntentRequest) -> dict[str, Any]:
    _assert_any_permission(request.actor_role, ["payment:create", "payment:create:own"])

    payment = PaymentRecord(
        payment_id=str(uuid4()),
        booking_id=request.booking_id,
        payer_id=request.payer_id,
        amount=request.amount,
        currency=request.currency,
        payment_method=request.payment_method,
        status=PaymentStatus.AUTHORIZED,
        provider_reference=f"pi_{uuid4().hex[:12]}",
    )
    payments[payment.payment_id] = payment
    return payment.model_dump(mode="json")


@app.post("/payments/{payment_id}/capture")
async def capture_payment(payment_id: str, request: PaymentActionRequest) -> dict[str, Any]:
    _assert_any_permission(request.actor_role, ["payment:update", "payment:create", "payment:create:own"])
    payment = payments.get(payment_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")
    if payment.status == PaymentStatus.REFUNDED:
        raise HTTPException(status_code=409, detail="Refunded payment cannot be captured")
    payment.status = PaymentStatus.CAPTURED
    return payment.model_dump(mode="json")


@app.post("/payments/{payment_id}/refund")
async def refund_payment(payment_id: str, request: PaymentActionRequest) -> dict[str, Any]:
    _assert_any_permission(request.actor_role, ["payment:update", "payment:create"])
    payment = payments.get(payment_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")
    payment.status = PaymentStatus.REFUNDED
    return payment.model_dump(mode="json")


@app.get("/payments/{payment_id}")
async def get_payment(payment_id: str, actor_role: Role = Role.MANAGER) -> dict[str, Any]:
    _assert_any_permission(actor_role, ["payment:read", "payment:update", "payment:create"])
    payment = payments.get(payment_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment.model_dump(mode="json")


@app.get("/payments/booking/{booking_id}")
async def list_booking_payments(booking_id: str, actor_role: Role = Role.MANAGER) -> dict[str, Any]:
    _assert_any_permission(actor_role, ["payment:read", "payment:update", "payment:create"])
    items = [payment.model_dump(mode="json") for payment in payments.values() if payment.booking_id == booking_id]
    return {"items": items, "count": len(items)}
