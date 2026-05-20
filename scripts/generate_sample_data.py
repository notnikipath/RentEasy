from __future__ import annotations

import json
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path

PROPERTY_TYPES = ["apartment", "room", "house", "cottage", "office", "warehouse"]
RENTAL_MODES = ["long_term", "short_term"]
CITIES = ["Москва", "Санкт-Петербург", "Казань", "Екатеринбург", "Новосибирск", "Сочи"]
DISTRICTS = ["Центральный", "Пресненский", "Вахитовский", "Октябрьский", "Ленинский"]


def generate_record(index: int) -> dict:
    city = random.choice(CITIES)
    district = random.choice(DISTRICTS)
    property_type = random.choice(PROPERTY_TYPES)
    rental_mode = random.choice(RENTAL_MODES)
    area = round(random.uniform(18, 220), 1)
    monthly = round(area * random.uniform(1100, 3200), 2)
    daily = round(monthly / 25, 2) if rental_mode == "short_term" else 0
    booked_days = random.randint(0, 30)
    available_days = 30

    return {
        "listing_id": f"LIST-{index:06d}",
        "host_id": f"HOST-{random.randint(1, 4000):04d}",
        "city": city,
        "district": district,
        "property_type": property_type,
        "rental_mode": rental_mode,
        "area_m2": area,
        "monthly_price": monthly,
        "daily_price": daily,
        "deposit": round(monthly * random.choice([0.5, 1.0, 1.5]), 2),
        "rating": round(random.uniform(3.2, 5.0), 2),
        "views": random.randint(0, 5000),
        "booked_days": booked_days,
        "available_days": available_days,
        "occupancy": round(booked_days / available_days, 2),
        "created_at": (datetime.now(UTC) - timedelta(minutes=index)).isoformat(),
    }


if __name__ == "__main__":
    random.seed(27)
    output = Path(__file__).resolve().parents[1] / "data" / "samples" / "rental_events.json"
    payload = [generate_record(index) for index in range(1, 12001)]
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(payload)} records to {output}")
