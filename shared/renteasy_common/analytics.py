from __future__ import annotations


def search_latency_seconds(cache_hit_ratio: float, filter_complexity: float, elastic_boost: bool = True) -> float:
    hit_ratio = min(max(cache_hit_ratio, 0.0), 1.0)
    complexity = max(filter_complexity, 0.0)
    base = 2.6 - hit_ratio * 1.35
    complexity_penalty = max(0.0, complexity - 1.0) * 0.42
    boost = 0.36 if elastic_boost else 0.0
    return round(max(0.15, base + complexity_penalty - boost), 3)


def booking_latency_seconds(
    lock_contention: float,
    payment_roundtrip: float,
    async_notifications: bool = True,
) -> float:
    contention = min(max(lock_contention, 0.0), 1.0)
    payment = max(payment_roundtrip, 0.0)
    notification_bonus = 0.4 if async_notifications else 0.0
    latency = 1.7 + contention * 1.9 + payment - notification_bonus
    return round(max(0.4, latency), 3)


def occupancy_rate(booked_days: int, available_days: int) -> float:
    if available_days <= 0:
        return 0.0
    return round(min(max(booked_days / available_days, 0.0), 1.0), 4)


def host_profitability(total_income: float, expenses: float, active_listings: int) -> dict[str, float]:
    profit = round(total_income - expenses, 2)
    margin = round((profit / total_income) * 100, 2) if total_income > 0 else 0.0
    per_listing = round(profit / max(active_listings, 1), 2)
    return {
        "profit": profit,
        "margin_pct": margin,
        "profit_per_listing": per_listing,
    }


def average_rating(ratings: list[int | float]) -> float:
    valid = [float(value) for value in ratings if value is not None]
    if not valid:
        return 0.0
    return round(sum(valid) / len(valid), 2)


def parallel_booking_plan(requests_per_second: int, cities: int) -> dict[str, int]:
    workers = min(64, max(2, cities * 2, requests_per_second // 30))
    batch_size = max(20, requests_per_second // max(workers, 1)) if requests_per_second > 0 else 20
    return {
        "workers": workers,
        "batch_size": batch_size,
        "requests_per_second": requests_per_second,
    }
