from pathlib import Path

from fastapi.testclient import TestClient

from tests.integration.helpers import load_module

ROOT = Path(__file__).resolve().parents[2]

listing_module = load_module("listing_module", ROOT / "listing-service" / "app" / "main.py")
search_module = load_module("search_module", ROOT / "search-service" / "app" / "main.py")
booking_module = load_module("booking_module", ROOT / "booking-service" / "app" / "main.py")
payment_module = load_module("payment_module", ROOT / "payment-service" / "app" / "main.py")
chat_module = load_module("chat_module", ROOT / "chat-service" / "app" / "main.py")
review_module = load_module("review_module", ROOT / "review-service" / "app" / "main.py")
analytics_module = load_module("analytics_module", ROOT / "analytics-service" / "app" / "main.py")
notification_module = load_module("notification_module", ROOT / "notification-service" / "app" / "main.py")

listing_client = TestClient(listing_module.app)
search_client = TestClient(search_module.app)
booking_client = TestClient(booking_module.app)
payment_client = TestClient(payment_module.app)
chat_client = TestClient(chat_module.app)
review_client = TestClient(review_module.app)
analytics_client = TestClient(analytics_module.app)
notification_client = TestClient(notification_module.app)


def test_listing_search_booking_payment_flow() -> None:
    listing_response = listing_client.get("/listings/LIST-DEMO-APT")
    assert listing_response.status_code == 200
    listing = listing_response.json()
    assert listing["geo"]["city"] == "Москва"

    search_response = search_client.post(
        "/search/query",
        json={
            "query": {
                "city": "Москва",
                "property_type": "apartment",
                "min_price": 90000,
                "max_price": 150000,
                "page": 1,
                "per_page": 10,
            },
            "user_id": "TENANT-100",
            "save": True,
            "save_name": "Moscow apartments",
        },
    )
    assert search_response.status_code == 200
    assert search_response.json()["count"] >= 1

    availability = booking_client.post(
        "/availability/check",
        json={
            "listing_id": "LIST-DEMO-APT",
            "check_in": "2026-06-10",
            "check_out": "2026-06-14",
        },
    )
    assert availability.status_code == 200
    assert availability.json()["available"] is True

    quote = listing_client.get(
        "/listings/LIST-DEMO-APT/price-quote",
        params={"check_in": "2026-06-10", "check_out": "2026-06-14"},
    )
    assert quote.status_code == 200
    quote_payload = quote.json()

    booking_create = booking_client.post(
        "/bookings",
        json={
            "user_id": "TENANT-100",
            "host_id": quote_payload["host_id"],
            "listing_id": "LIST-DEMO-APT",
            "check_in": "2026-06-10",
            "check_out": "2026-06-14",
            "guests": 2,
            "nightly_price": quote_payload["nightly_price"],
            "total_price": quote_payload["total_price"],
            "deposit": quote_payload["deposit"],
            "actor_id": "TENANT-100",
            "actor_role": "tenant",
        },
    )
    assert booking_create.status_code == 200
    booking = booking_create.json()

    blocked = booking_client.post(
        "/availability/block",
        json={
            "listing_id": "LIST-DEMO-APT",
            "booking_id": booking["booking_id"],
            "check_in": booking["check_in"],
            "check_out": booking["check_out"],
            "actor_id": "SYS-1",
            "actor_role": "manager",
        },
    )
    assert blocked.status_code == 200

    payment = payment_client.post(
        "/payments/intent",
        json={
            "booking_id": booking["booking_id"],
            "payer_id": "TENANT-100",
            "amount": quote_payload["total_price"] + quote_payload["deposit"],
            "currency": "RUB",
            "payment_method": "card",
            "actor_role": "tenant",
        },
    )
    assert payment.status_code == 200
    payment_payload = payment.json()

    capture = payment_client.post(
        f"/payments/{payment_payload['payment_id']}/capture",
        json={"actor_id": "SYS-1", "actor_role": "manager"},
    )
    assert capture.status_code == 200
    assert capture.json()["status"] == "captured"

    confirm = booking_client.post(
        f"/bookings/{booking['booking_id']}/confirm",
        json={"actor_id": "SYS-1", "actor_role": "manager"},
    )
    assert confirm.status_code == 200
    assert confirm.json()["status"] == "confirmed"

    analytics_booking = analytics_client.post(
        "/analytics/events/booking",
        json={
            "booking_id": booking["booking_id"],
            "listing_id": booking["listing_id"],
            "host_id": booking["host_id"],
            "amount": booking["total_price"],
            "status": "confirmed",
        },
    )
    assert analytics_booking.status_code == 200

    notification = notification_client.post(
        "/notify/booking-created",
        json={
            "host_id": booking["host_id"],
            "booking_id": booking["booking_id"],
            "listing_id": booking["listing_id"],
            "check_in": booking["check_in"],
            "check_out": booking["check_out"],
            "actor_role": "manager",
        },
    )
    assert notification.status_code == 200


def test_chat_review_analytics_flow() -> None:
    message = chat_client.post(
        "/chats/messages",
        json={
            "conversation_id": "CONV-APT-001",
            "listing_id": "LIST-DEMO-APT",
            "sender_id": "TENANT-100",
            "recipient_id": "HOST-001",
            "text": "Здравствуйте! Можно посмотреть квартиру в воскресенье?",
            "actor_role": "tenant",
        },
    )
    assert message.status_code == 200

    viewing = chat_client.post(
        "/viewings/request",
        json={
            "listing_id": "LIST-DEMO-APT",
            "user_id": "TENANT-100",
            "host_id": "HOST-001",
            "desired_datetime": "2026-06-01T18:00:00Z",
            "note": "После работы",
            "actor_role": "tenant",
        },
    )
    assert viewing.status_code == 200

    review = review_client.post(
        "/reviews",
        json={
            "target_type": "listing",
            "target_id": "LIST-DEMO-APT",
            "listing_id": "LIST-DEMO-APT",
            "host_id": "HOST-001",
            "author_id": "TENANT-100",
            "rating": 5,
            "comment": "Удобное расположение и быстрый ответ владельца.",
            "actor_role": "tenant",
        },
    )
    assert review.status_code == 200

    ratings = review_client.get("/ratings/listing/LIST-DEMO-APT")
    assert ratings.status_code == 200
    assert ratings.json()["rating"] >= 4

    view_track = listing_client.post(
        "/listings/LIST-DEMO-APT/view",
        json={"session_id": "SESSION-501"},
    )
    assert view_track.status_code == 200

    analytics_view = analytics_client.post(
        "/analytics/events/view",
        json={
            "listing_id": "LIST-DEMO-APT",
            "user_id": "TENANT-100",
            "session_id": "SESSION-501",
            "city": "Москва",
            "duration_seconds": 142,
        },
    )
    assert analytics_view.status_code == 200

    owner = analytics_client.get("/analytics/owner/HOST-001", params={"actor_role": "host"})
    assert owner.status_code == 200
    assert owner.json()["profit"] >= 0

    kpi = analytics_client.get("/analytics/kpi")
    assert kpi.status_code == 200
    assert "search_latency_p95_ms" in kpi.json()
