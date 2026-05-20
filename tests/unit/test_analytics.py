from shared.renteasy_common import (
    booking_latency_seconds,
    host_profitability,
    occupancy_rate,
    parallel_booking_plan,
    search_latency_seconds,
)


def test_search_latency_seconds_under_target() -> None:
    value = search_latency_seconds(cache_hit_ratio=0.8, filter_complexity=1.0, elastic_boost=True)
    assert 0 < value < 2


def test_booking_latency_seconds_under_target() -> None:
    value = booking_latency_seconds(lock_contention=0.2, payment_roundtrip=1.2, async_notifications=True)
    assert 0 < value < 5


def test_occupancy_and_profitability() -> None:
    assert occupancy_rate(21, 30) == 0.7
    profile = host_profitability(total_income=300000, expenses=120000, active_listings=3)
    assert profile["profit"] == 180000
    assert profile["profit_per_listing"] == 60000


def test_parallel_booking_plan_has_workers() -> None:
    plan = parallel_booking_plan(requests_per_second=5400, cities=8)
    assert plan["workers"] >= 2
    assert plan["batch_size"] >= 20
