from __future__ import annotations

from statistics import mean
from typing import Any

from fastapi import FastAPI, HTTPException

from shared.renteasy_common import (
    BookingAnalyticsEvent,
    BookingLatencyEvent,
    BookingStatus,
    Role,
    SearchLatencyEvent,
    Settings,
    ViewEvent,
    booking_latency_seconds,
    demand_forecast,
    has_permission,
    host_profitability,
    occupancy_rate,
    parallel_booking_plan,
    search_latency_seconds,
)

settings = Settings(service_name="analytics-service", service_port=8407)
app = FastAPI(title="RentEasy Analytics Service", version="1.0.0")


listing_views: dict[str, list[int]] = {
    "LIST-DEMO-APT": [120, 84, 95, 67],
    "LIST-DEMO-DAILY": [45, 39, 62],
}
host_booking_revenue: dict[str, list[float]] = {
    "HOST-001": [115000.0, 119000.0],
    "HOST-003": [21000.0, 17200.0, 24000.0],
}
host_booking_days: dict[str, dict[str, int]] = {
    "HOST-001": {"booked": 42, "available": 60},
    "HOST-003": {"booked": 23, "available": 30},
}
host_expenses: dict[str, float] = {
    "HOST-001": 52000.0,
    "HOST-003": 13800.0,
}
search_latency_samples_ms: list[float] = [540.0, 620.0, 710.0, 480.0]
booking_latency_samples_ms: list[float] = [1620.0, 1890.0, 2110.0, 1730.0]
booking_status_counters: dict[BookingStatus, int] = {
    BookingStatus.CREATED: 0,
    BookingStatus.PENDING_PAYMENT: 4,
    BookingStatus.CONFIRMED: 3,
    BookingStatus.CANCELLED: 1,
}


def _percentile(samples: list[float], p: float) -> float:
    if not samples:
        return 0.0
    sorted_samples = sorted(samples)
    idx = max(0, min(len(sorted_samples) - 1, round((len(sorted_samples) - 1) * p)))
    return round(sorted_samples[idx], 2)


def _assert_permission(role: Role, action: str, host_scope: bool = False) -> None:
    if host_scope and has_permission(role, "analytics:read:host"):
        return
    if not has_permission(role, action):
        raise HTTPException(status_code=403, detail=f"Role {role.value} cannot perform {action}")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.post("/analytics/events/view")
async def ingest_view(event: ViewEvent) -> dict[str, Any]:
    listing_views.setdefault(event.listing_id, []).append(event.duration_seconds)
    return {"status": "accepted", "listing_id": event.listing_id, "views": len(listing_views[event.listing_id])}


@app.post("/analytics/events/booking")
async def ingest_booking(event: BookingAnalyticsEvent) -> dict[str, Any]:
    host_booking_revenue.setdefault(event.host_id, []).append(event.amount)
    booking_status_counters[event.status] = booking_status_counters.get(event.status, 0) + 1
    if event.status == BookingStatus.CONFIRMED:
        host_booking_days.setdefault(event.host_id, {"booked": 0, "available": 30})["booked"] += 1
    return {"status": "accepted", "booking_id": event.booking_id}


@app.post("/analytics/events/search-latency")
async def ingest_search_latency(event: SearchLatencyEvent) -> dict[str, Any]:
    search_latency_samples_ms.append(event.latency_ms)
    return {"status": "accepted", "p95_ms": _percentile(search_latency_samples_ms, 0.95)}


@app.post("/analytics/events/booking-latency")
async def ingest_booking_latency(event: BookingLatencyEvent) -> dict[str, Any]:
    booking_latency_samples_ms.append(event.latency_ms)
    return {"status": "accepted", "p95_ms": _percentile(booking_latency_samples_ms, 0.95)}


@app.get("/analytics/listing/{listing_id}")
async def listing_metrics(listing_id: str) -> dict[str, Any]:
    durations = listing_views.get(listing_id, [])
    return {
        "listing_id": listing_id,
        "views": len(durations),
        "avg_view_duration_sec": round(mean(durations), 2) if durations else 0,
    }


@app.get("/analytics/owner/{host_id}")
async def owner_metrics(host_id: str, actor_role: Role = Role.HOST) -> dict[str, Any]:
    _assert_permission(actor_role, "analytics:read", host_scope=True)

    revenue = sum(host_booking_revenue.get(host_id, []))
    expenses = host_expenses.get(host_id, 0.0)
    listings_count = max(1, len(host_booking_revenue.get(host_id, [])))
    profitability = host_profitability(revenue, expenses, listings_count)
    occupancy_data = host_booking_days.get(host_id, {"booked": 0, "available": 0})

    return {
        "host_id": host_id,
        "revenue": round(revenue, 2),
        "expenses": round(expenses, 2),
        "occupancy_rate": occupancy_rate(occupancy_data.get("booked", 0), occupancy_data.get("available", 0)),
        **profitability,
    }


@app.get("/analytics/kpi")
async def platform_kpi() -> dict[str, Any]:
    search_p95_ms = _percentile(search_latency_samples_ms, 0.95)
    booking_p95_ms = _percentile(booking_latency_samples_ms, 0.95)

    estimated_search_sec = search_latency_seconds(
        cache_hit_ratio=0.76,
        filter_complexity=1.2,
        elastic_boost=True,
    )
    estimated_booking_sec = booking_latency_seconds(
        lock_contention=0.22,
        payment_roundtrip=1.1,
        async_notifications=True,
    )

    return {
        "search_latency_p95_ms": search_p95_ms,
        "booking_latency_p95_ms": booking_p95_ms,
        "search_time_target_sec": settings.search_target_seconds,
        "booking_time_target_sec": settings.booking_target_seconds,
        "estimated_search_latency_sec": estimated_search_sec,
        "estimated_booking_latency_sec": estimated_booking_sec,
        "search_target_met": search_p95_ms / 1000 < settings.search_target_seconds,
        "booking_target_met": booking_p95_ms / 1000 < settings.booking_target_seconds,
        "listing_capacity_target": settings.listing_capacity_target,
        "status_breakdown": {status.value: count for status, count in booking_status_counters.items()},
    }


@app.get("/analytics/demand-forecast")
async def forecast(
    history: str = "24,27,31,35,33,29",
    season_multiplier: float = 1.0,
    event_multiplier: float = 1.0,
) -> dict[str, Any]:
    values = [int(item.strip()) for item in history.split(",") if item.strip()]
    return {
        "history": values,
        "forecast_next_30_days": demand_forecast(
            values,
            season_multiplier=season_multiplier,
            event_multiplier=event_multiplier,
        ),
    }


@app.get("/analytics/capacity-plan")
async def capacity_plan(
    requests_per_second: int = 5000,
    cities: int = 12,
    actor_role: Role = Role.MANAGER,
) -> dict[str, Any]:
    _assert_permission(actor_role, "analytics:read")
    return parallel_booking_plan(requests_per_second, cities)
