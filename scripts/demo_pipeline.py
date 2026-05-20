from __future__ import annotations

import json
import urllib.request

BASE = "http://localhost:8480"


def request(method: str, path: str, payload: dict | None = None) -> dict:
    data = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(f"{BASE}{path}", data=data, headers=headers, method=method)
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode("utf-8"))


if __name__ == "__main__":
    booking_result = request(
        "POST",
        "/workflow/create-booking",
        {
            "user_id": "TENANT-100",
            "listing_id": "LIST-DEMO-APT",
            "check_in": "2026-06-10",
            "check_out": "2026-06-14",
            "guests": 2,
            "payment_method": "card",
            "actor_role": "tenant",
        },
    )
    print("Create booking workflow result:")
    print(json.dumps(booking_result, ensure_ascii=False, indent=2))

    viewing_result = request(
        "POST",
        "/workflow/request-viewing",
        {
            "listing_id": "LIST-DEMO-APT",
            "host_id": "HOST-001",
            "user_id": "TENANT-100",
            "desired_datetime": "2026-06-01T18:30:00Z",
            "note": "Удобно после 18:00",
            "actor_role": "tenant",
        },
    )
    print("\nViewing workflow result:")
    print(json.dumps(viewing_result, ensure_ascii=False, indent=2))
