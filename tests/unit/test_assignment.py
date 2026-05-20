from shared.renteasy_common import (
    detect_fraud_listing,
    estimate_rent_price,
    parallel_booking_batches,
    recommend_listings,
)


def test_estimate_rent_price_short_term_higher() -> None:
    long_term = estimate_rent_price(42, 1500, district_index=1.15, furnished=True, short_term=False)
    short_term = estimate_rent_price(42, 1500, district_index=1.15, furnished=True, short_term=True)
    assert long_term > 0
    assert short_term > long_term


def test_detect_fraud_listing_flags_underpriced_duplicates() -> None:
    findings = detect_fraud_listing(
        view_count=1800,
        contact_switches=4,
        price_to_market_ratio=0.51,
        duplicate_photo_ratio=0.7,
    )
    codes = {item["code"] for item in findings}
    assert "suspicious_price" in codes
    assert "duplicate_media" in codes


def test_recommend_listings_prefers_budget_city_and_type() -> None:
    ranked = recommend_listings(
        preferences={
            "city": "Москва",
            "property_type": "apartment",
            "budget": 120000,
            "rooms": 2,
        },
        candidates=[
            {
                "listing_id": "A",
                "city": "Москва",
                "property_type": "apartment",
                "price": 115000,
                "rooms": 2,
                "rating": 4.7,
            },
            {
                "listing_id": "B",
                "city": "Казань",
                "property_type": "room",
                "price": 58000,
                "rooms": 1,
                "rating": 4.9,
            },
            {
                "listing_id": "C",
                "city": "Москва",
                "property_type": "office",
                "price": 210000,
                "rooms": 3,
                "rating": 4.8,
            },
        ],
    )
    assert ranked[0] == "A"


def test_parallel_booking_batches_distributes_without_loss() -> None:
    ids = [f"B-{index}" for index in range(12)]
    batches = parallel_booking_batches(ids, workers=4)
    flattened = [item for batch in batches for item in batch]
    assert sorted(flattened) == sorted(ids)
    assert len(batches) == 4
