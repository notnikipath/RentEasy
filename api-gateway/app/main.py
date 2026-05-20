from __future__ import annotations

from datetime import date
from time import perf_counter
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from shared.renteasy_common import CreateBookingWorkflowResult, Role, Settings, sign_token, verify_token


class GatewaySettings(BaseSettings):
    service_name: str = "api-gateway"
    service_port: int = 8400

    listing_service_url: str = "http://listing-service:8401"
    search_service_url: str = "http://search-service:8402"
    booking_service_url: str = "http://booking-service:8403"
    payment_service_url: str = "http://payment-service:8404"
    chat_service_url: str = "http://chat-service:8405"
    review_service_url: str = "http://review-service:8406"
    analytics_service_url: str = "http://analytics-service:8407"
    notification_service_url: str = "http://notification-service:8408"

    jwt_secret: str = Settings().jwt_secret
    token_exp_minutes: int = 240

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = GatewaySettings()
app = FastAPI(title="RentEasy API Gateway", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AuthRequest(BaseModel):
    user_id: str
    role: Role
    language: str = Field(default="ru", pattern="^(ru|en)$")


class CreateBookingWorkflowRequest(BaseModel):
    user_id: str
    listing_id: str
    check_in: date
    check_out: date
    guests: int = Field(default=1, ge=1, le=20)
    payment_method: str = "card"
    actor_role: Role = Role.TENANT


class ViewingWorkflowRequest(BaseModel):
    listing_id: str
    host_id: str
    user_id: str
    desired_datetime: str
    note: str = ""
    actor_role: Role = Role.TENANT


AuthRequest.model_rebuild()
CreateBookingWorkflowRequest.model_rebuild()
ViewingWorkflowRequest.model_rebuild()


async def _post_json(client: httpx.AsyncClient, url: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = await client.post(url, json=payload)
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return response.json()


async def _get_json(client: httpx.AsyncClient, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    response = await client.get(url, params=params)
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return response.json()


def _service_urls() -> dict[str, str]:
    return {
        "listing": settings.listing_service_url,
        "search": settings.search_service_url,
        "booking": settings.booking_service_url,
        "payment": settings.payment_service_url,
        "chat": settings.chat_service_url,
        "review": settings.review_service_url,
        "analytics": settings.analytics_service_url,
        "notification": settings.notification_service_url,
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.post("/auth/token")
async def issue_token(request: AuthRequest) -> dict[str, str]:
    token = sign_token(
        {"sub": request.user_id, "role": request.role.value, "language": request.language},
        settings.jwt_secret,
        exp_minutes=settings.token_exp_minutes,
    )
    return {"access_token": token, "token_type": "Bearer"}


@app.post("/auth/verify")
async def verify_auth(token: str) -> dict[str, Any]:
    payload = verify_token(token, settings.jwt_secret)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload


@app.get("/services/health")
async def service_health() -> dict[str, Any]:
    statuses: dict[str, Any] = {}
    async with httpx.AsyncClient(timeout=10.0) as client:
        for name, base_url in _service_urls().items():
            try:
                statuses[name] = await _get_json(client, f"{base_url}/health")
            except HTTPException as exc:
                statuses[name] = {"status": "error", "detail": exc.detail}
            except httpx.HTTPError as exc:
                statuses[name] = {"status": "error", "detail": str(exc)}
    return statuses


@app.post("/workflow/create-booking")
async def create_booking_workflow(request: CreateBookingWorkflowRequest) -> dict[str, Any]:
    if request.check_out <= request.check_in:
        raise HTTPException(status_code=400, detail="check_out must be greater than check_in")

    started = perf_counter()

    async with httpx.AsyncClient(timeout=25.0) as client:
        listing = await _get_json(client, f"{settings.listing_service_url}/listings/{request.listing_id}")

        availability = await _post_json(
            client,
            f"{settings.booking_service_url}/availability/check",
            {
                "listing_id": request.listing_id,
                "check_in": request.check_in.isoformat(),
                "check_out": request.check_out.isoformat(),
            },
        )
        if not availability.get("available"):
            raise HTTPException(status_code=409, detail="Selected dates are not available")

        quote = await _get_json(
            client,
            f"{settings.listing_service_url}/listings/{request.listing_id}/price-quote",
            {
                "check_in": request.check_in.isoformat(),
                "check_out": request.check_out.isoformat(),
            },
        )

        booking = await _post_json(
            client,
            f"{settings.booking_service_url}/bookings",
            {
                "user_id": request.user_id,
                "host_id": quote["host_id"],
                "listing_id": request.listing_id,
                "check_in": request.check_in.isoformat(),
                "check_out": request.check_out.isoformat(),
                "guests": request.guests,
                "nightly_price": quote["nightly_price"],
                "total_price": quote["total_price"],
                "deposit": quote["deposit"],
                "actor_id": request.user_id,
                "actor_role": request.actor_role.value,
            },
        )

        blocked_dates = await _post_json(
            client,
            f"{settings.booking_service_url}/availability/block",
            {
                "listing_id": request.listing_id,
                "booking_id": booking["booking_id"],
                "check_in": request.check_in.isoformat(),
                "check_out": request.check_out.isoformat(),
                "actor_id": "gateway-system",
                "actor_role": Role.MANAGER.value,
            },
        )

        payment = await _post_json(
            client,
            f"{settings.payment_service_url}/payments/intent",
            {
                "booking_id": booking["booking_id"],
                "payer_id": request.user_id,
                "amount": round(quote["total_price"] + quote["deposit"], 2),
                "currency": quote["currency"],
                "payment_method": request.payment_method,
                "actor_role": request.actor_role.value,
            },
        )

        await _post_json(
            client,
            f"{settings.payment_service_url}/payments/{payment['payment_id']}/capture",
            {
                "actor_id": "gateway-system",
                "actor_role": Role.MANAGER.value,
            },
        )

        await _post_json(
            client,
            f"{settings.booking_service_url}/bookings/{booking['booking_id']}/confirm",
            {
                "actor_id": "gateway-system",
                "actor_role": Role.MANAGER.value,
            },
        )

        notification = await _post_json(
            client,
            f"{settings.notification_service_url}/notify/booking-created",
            {
                "host_id": listing["host_id"],
                "booking_id": booking["booking_id"],
                "listing_id": request.listing_id,
                "check_in": request.check_in.isoformat(),
                "check_out": request.check_out.isoformat(),
                "actor_role": Role.MANAGER.value,
            },
        )

        total_latency_ms = round((perf_counter() - started) * 1000, 2)

        await _post_json(
            client,
            f"{settings.analytics_service_url}/analytics/events/booking",
            {
                "booking_id": booking["booking_id"],
                "listing_id": request.listing_id,
                "host_id": listing["host_id"],
                "amount": quote["total_price"],
                "status": "confirmed",
            },
        )
        await _post_json(
            client,
            f"{settings.analytics_service_url}/analytics/events/booking-latency",
            {"latency_ms": total_latency_ms},
        )

    result = CreateBookingWorkflowResult(
        availability=availability,
        quote=quote,
        booking=booking,
        blocked_dates=blocked_dates,
        payment=payment,
        notification=notification,
        total_latency_ms=total_latency_ms,
    )
    return result.model_dump(mode="json")


@app.post("/workflow/request-viewing")
async def request_viewing_workflow(request: ViewingWorkflowRequest) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=15.0) as client:
        viewing = await _post_json(
            client,
            f"{settings.chat_service_url}/viewings/request",
            {
                "listing_id": request.listing_id,
                "host_id": request.host_id,
                "user_id": request.user_id,
                "desired_datetime": request.desired_datetime,
                "note": request.note,
                "actor_role": request.actor_role.value,
            },
        )
        notification = await _post_json(
            client,
            f"{settings.notification_service_url}/notify/send",
            {
                "channel": "push",
                "recipient": request.host_id,
                "subject": f"Запрос на просмотр: {request.listing_id}",
                "body": f"Пользователь {request.user_id} запросил просмотр на {request.desired_datetime}",
                "severity": "info",
                "actor_role": Role.MANAGER.value,
            },
        )
    return {"viewing": viewing, "notification": notification}


@app.get("/dashboard/{host_id}")
async def host_dashboard(host_id: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=20.0) as client:
        listings = await _get_json(client, f"{settings.listing_service_url}/hosts/{host_id}/listings")
        bookings = await _get_json(client, f"{settings.booking_service_url}/bookings/host/{host_id}")
        owner_analytics = await _get_json(client, f"{settings.analytics_service_url}/analytics/owner/{host_id}")
        host_reviews = await _get_json(client, f"{settings.review_service_url}/reviews/host/{host_id}")
        notifications = await _get_json(client, f"{settings.notification_service_url}/notify/history")
        platform_kpi = await _get_json(client, f"{settings.analytics_service_url}/analytics/kpi")

    return {
        "host_id": host_id,
        "listings": listings,
        "bookings": bookings,
        "owner_analytics": owner_analytics,
        "reviews": host_reviews,
        "notifications": notifications,
        "kpi": platform_kpi,
    }
