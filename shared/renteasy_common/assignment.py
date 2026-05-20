from __future__ import annotations

from collections import Counter

from .schemas import Severity


def estimate_rent_price(
    area_m2: float,
    base_rate_per_m2: float,
    district_index: float,
    furnished: bool,
    short_term: bool,
) -> float:
    base = max(area_m2, 1) * max(base_rate_per_m2, 0)
    district_multiplier = max(0.55, min(district_index, 2.2))
    furnished_bonus = 1.08 if furnished else 1.0
    short_term_bonus = 1.35 if short_term else 1.0
    return round(base * district_multiplier * furnished_bonus * short_term_bonus, 2)


def recommend_listings(preferences: dict[str, object], candidates: list[dict[str, object]]) -> list[str]:
    scored: list[tuple[float, str]] = []
    preferred_city = str(preferences.get("city", "")).lower()
    preferred_type = str(preferences.get("property_type", "")).lower()
    budget = float(preferences.get("budget", 0) or 0)
    desired_rooms = float(preferences.get("rooms", 0) or 0)

    for listing in candidates:
        listing_id = str(listing.get("listing_id", ""))
        city = str(listing.get("city", "")).lower()
        property_type = str(listing.get("property_type", "")).lower()
        price = float(listing.get("price", 0) or 0)
        rooms = float(listing.get("rooms", 0) or 0)
        rating = float(listing.get("rating", 0) or 0)

        score = rating * 8
        if preferred_city and city == preferred_city:
            score += 18
        if preferred_type and property_type == preferred_type:
            score += 14
        if budget > 0:
            score += 10 if price <= budget else max(-10, -((price - budget) / budget) * 10)
        if desired_rooms > 0:
            score += max(0, 6 - abs(rooms - desired_rooms) * 3)

        scored.append((score, listing_id))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [listing_id for _, listing_id in scored if listing_id]


def detect_fraud_listing(
    view_count: int,
    contact_switches: int,
    price_to_market_ratio: float,
    duplicate_photo_ratio: float,
) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []

    if price_to_market_ratio < 0.55:
        findings.append(
            {
                "severity": Severity.CRITICAL.value,
                "code": "suspicious_price",
                "message": "Listing price is critically below market baseline.",
            }
        )
    elif price_to_market_ratio < 0.72:
        findings.append(
            {
                "severity": Severity.WARNING.value,
                "code": "low_price",
                "message": "Listing price is below market and needs manual review.",
            }
        )

    if contact_switches >= 3:
        findings.append(
            {
                "severity": Severity.WARNING.value,
                "code": "contact_switching",
                "message": "Owner changed contact details multiple times.",
            }
        )

    if duplicate_photo_ratio >= 0.5:
        findings.append(
            {
                "severity": Severity.CRITICAL.value,
                "code": "duplicate_media",
                "message": "Large share of media duplicates other listings.",
            }
        )

    if view_count > 1200 and contact_switches == 0 and price_to_market_ratio < 0.7:
        findings.append(
            {
                "severity": Severity.WARNING.value,
                "code": "high_attention_underpriced",
                "message": "Abnormally high traffic for an underpriced listing.",
            }
        )

    return findings


def demand_forecast(
    last_30_days_bookings: list[int],
    season_multiplier: float = 1.0,
    event_multiplier: float = 1.0,
) -> int:
    if not last_30_days_bookings:
        return 0
    avg_daily = sum(last_30_days_bookings) / len(last_30_days_bookings)
    forecast = avg_daily * 30 * max(season_multiplier, 0) * max(event_multiplier, 0)
    return max(0, round(forecast))


def split_search_shards(cities: list[str], max_shards: int = 8) -> dict[str, list[str]]:
    normalized = [city.strip() for city in cities if city.strip()]
    if not normalized:
        return {"shard-1": []}

    unique = list(dict.fromkeys(normalized))
    shard_count = max(1, min(max_shards, len(unique)))
    shards: dict[str, list[str]] = {f"shard-{idx + 1}": [] for idx in range(shard_count)}

    for index, city in enumerate(unique):
        key = f"shard-{index % shard_count + 1}"
        shards[key].append(city)

    return shards


def parallel_booking_batches(booking_ids: list[str], workers: int) -> list[list[str]]:
    safe_workers = max(1, workers)
    batches: list[list[str]] = [[] for _ in range(safe_workers)]
    for index, booking_id in enumerate(booking_ids):
        batches[index % safe_workers].append(booking_id)
    return [batch for batch in batches if batch]


def top_search_districts(history: list[str], top_n: int = 3) -> list[str]:
    if not history:
        return []
    return [district for district, _ in Counter(history).most_common(top_n)]
