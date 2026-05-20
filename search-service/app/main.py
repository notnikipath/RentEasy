from __future__ import annotations

from datetime import date
from time import perf_counter
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from shared.renteasy_common import (
    ListingRecord,
    PropertyType,
    RentalMode,
    Role,
    SavedSearch,
    SavedSearchRequest,
    SearchRequest,
    Settings,
    TTLCache,
    parallel_booking_plan,
    recommend_listings,
    search_latency_seconds,
    split_search_shards,
)

settings = Settings(service_name="search-service", service_port=8402)
app = FastAPI(title="RentEasy Search Service", version="1.0.0")


class SearchQueryRequest(BaseModel):
    query: SearchRequest
    user_id: str | None = None
    save: bool = False
    save_name: str | None = None


class ListingIndexRequest(BaseModel):
    listing: ListingRecord


class RecommendationRequest(BaseModel):
    preferences: dict[str, Any] = Field(default_factory=dict)
    limit: int = Field(default=5, ge=1, le=50)


SearchQueryRequest.model_rebuild()
ListingIndexRequest.model_rebuild()
RecommendationRequest.model_rebuild()


def _seed_index() -> dict[str, ListingRecord]:
    seeds = [
        ListingRecord(
            listing_id="LIST-DEMO-APT",
            host_id="HOST-001",
            title="2-комнатная квартира рядом с метро",
            description="Светлая квартира после ремонта.",
            property_type=PropertyType.APARTMENT,
            rental_mode=RentalMode.LONG_TERM,
            rooms=2,
            area_m2=58,
            floor=9,
            is_furnished=True,
            pets_allowed=True,
            geo={
                "city": "Москва",
                "district": "Пресненский",
                "address": "ул. Красная Пресня, 30",
                "latitude": 55.7602,
                "longitude": 37.5722,
            },
            pricing={"daily_price": 0, "monthly_price": 115000, "deposit": 115000, "currency": "RUB"},
            available_from=date(2026, 5, 20),
            amenities=["wifi", "parking"],
            rating_avg=4.8,
            views=214,
        ),
        ListingRecord(
            listing_id="LIST-DEMO-OFFICE",
            host_id="HOST-002",
            title="Офис 120 м2 в бизнес-центре",
            description="Open-space + переговорная.",
            property_type=PropertyType.OFFICE,
            rental_mode=RentalMode.LONG_TERM,
            rooms=4,
            area_m2=120,
            floor=4,
            is_furnished=False,
            pets_allowed=False,
            geo={
                "city": "Санкт-Петербург",
                "district": "Центральный",
                "address": "Невский пр., 110",
                "latitude": 59.9315,
                "longitude": 30.3609,
            },
            pricing={"daily_price": 0, "monthly_price": 230000, "deposit": 230000, "currency": "RUB"},
            available_from=date(2026, 6, 1),
            amenities=["security", "meeting_room"],
            rating_avg=4.6,
            views=141,
        ),
        ListingRecord(
            listing_id="LIST-DEMO-DAILY",
            host_id="HOST-003",
            title="Студия посуточно у набережной",
            description="Короткая аренда, бесконтактное заселение.",
            property_type=PropertyType.ROOM,
            rental_mode=RentalMode.SHORT_TERM,
            rooms=1,
            area_m2=28,
            floor=3,
            is_furnished=True,
            pets_allowed=False,
            geo={
                "city": "Казань",
                "district": "Вахитовский",
                "address": "ул. Баумана, 18",
                "latitude": 55.7902,
                "longitude": 49.1143,
            },
            pricing={"daily_price": 5200, "monthly_price": 94000, "deposit": 5000, "currency": "RUB"},
            available_from=date(2026, 5, 14),
            amenities=["wifi", "smart_lock"],
            rating_avg=4.9,
            views=388,
        ),
    ]
    return {item.listing_id: item for item in seeds}


indexed_listings: dict[str, ListingRecord] = _seed_index()
cache = TTLCache(ttl_seconds=120)
saved_searches: dict[str, list[SavedSearch]] = {}
cache_stats = {"hits": 0, "misses": 0}


def _cache_key(query: SearchRequest) -> str:
    return query.model_dump_json()


def _filter_listing(listing: ListingRecord, query: SearchRequest) -> bool:
    if query.city and listing.geo.city.lower() != query.city.lower():
        return False
    if query.district and listing.geo.district.lower() != query.district.lower():
        return False
    if query.property_type and listing.property_type != query.property_type:
        return False
    if query.rental_mode and listing.rental_mode != query.rental_mode:
        return False

    price = listing.pricing.monthly_price
    if query.min_price is not None and price < query.min_price:
        return False
    if query.max_price is not None and price > query.max_price:
        return False
    if query.min_area is not None and listing.area_m2 < query.min_area:
        return False
    if query.max_area is not None and listing.area_m2 > query.max_area:
        return False
    if query.pets_allowed is not None and listing.pets_allowed != query.pets_allowed:
        return False
    if query.furnished_only and not listing.is_furnished:
        return False

    return True


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.post("/search/index")
async def index_listing(request: ListingIndexRequest, actor_role: Role = Role.MANAGER) -> dict[str, Any]:
    if actor_role not in {Role.MANAGER, Role.ADMIN}:
        raise HTTPException(status_code=403, detail="Forbidden")
    indexed_listings[request.listing.listing_id] = request.listing
    return {"status": "indexed", "listing_id": request.listing.listing_id, "total": len(indexed_listings)}


@app.post("/search/query")
async def query_search(request: SearchQueryRequest) -> dict[str, Any]:
    start = perf_counter()
    cache_key = _cache_key(request.query)
    cached = cache.get(cache_key)
    if cached is not None:
        cache_stats["hits"] += 1
        latency_ms = round((perf_counter() - start) * 1000, 2)
        return {
            **cached,
            "cache": "hit",
            "latency_ms": latency_ms,
        }

    cache_stats["misses"] += 1
    all_items = [listing for listing in indexed_listings.values() if _filter_listing(listing, request.query)]
    all_items.sort(key=lambda listing: (-listing.rating_avg, listing.pricing.monthly_price, -listing.views))

    offset = (request.query.page - 1) * request.query.per_page
    page_items = all_items[offset : offset + request.query.per_page]
    payload = {
        "items": [item.model_dump(mode="json") for item in page_items],
        "count": len(all_items),
        "page": request.query.page,
        "per_page": request.query.per_page,
        "search_estimate_sec": search_latency_seconds(
            cache_hit_ratio=cache_stats["hits"] / max(cache_stats["hits"] + cache_stats["misses"], 1),
            filter_complexity=1.0 + sum(
                int(value is not None and value is not False)
                for value in request.query.model_dump().values()
            )
            / 10,
            elastic_boost=True,
        ),
    }
    cache.set(cache_key, payload)

    if request.save and request.user_id:
        saved = SavedSearch(
            search_id=f"SRCH-{len(saved_searches.get(request.user_id, [])) + 1:04d}",
            user_id=request.user_id,
            name=request.save_name or "Saved search",
            query=request.query,
        )
        saved_searches.setdefault(request.user_id, []).append(saved)

    latency_ms = round((perf_counter() - start) * 1000, 2)
    return {
        **payload,
        "cache": "miss",
        "latency_ms": latency_ms,
    }


@app.post("/search/saved")
async def save_search(request: SavedSearchRequest) -> dict[str, Any]:
    item = SavedSearch(
        search_id=f"SRCH-{len(saved_searches.get(request.user_id, [])) + 1:04d}",
        user_id=request.user_id,
        name=request.name,
        query=request.query,
    )
    saved_searches.setdefault(request.user_id, []).append(item)
    return item.model_dump(mode="json")


@app.get("/search/saved/{user_id}")
async def get_saved_searches(user_id: str) -> dict[str, Any]:
    items = [search.model_dump(mode="json") for search in saved_searches.get(user_id, [])]
    return {"items": items, "count": len(items)}


@app.post("/search/recommendations")
async def recommendations(request: RecommendationRequest) -> dict[str, Any]:
    candidates = [
        {
            "listing_id": listing.listing_id,
            "city": listing.geo.city,
            "property_type": listing.property_type.value,
            "price": listing.pricing.monthly_price,
            "rooms": listing.rooms,
            "rating": listing.rating_avg,
        }
        for listing in indexed_listings.values()
    ]
    ranked_ids = recommend_listings(request.preferences, candidates)
    selected = [
        indexed_listings[item_id].model_dump(mode="json")
        for item_id in ranked_ids[: request.limit]
        if item_id in indexed_listings
    ]
    return {"items": selected, "count": len(selected)}


@app.get("/search/cache/stats")
async def cache_status() -> dict[str, Any]:
    total = cache_stats["hits"] + cache_stats["misses"]
    return {
        "hits": cache_stats["hits"],
        "misses": cache_stats["misses"],
        "hit_ratio": round(cache_stats["hits"] / total, 3) if total else 0.0,
    }


@app.get("/search/parallel-plan")
async def search_parallel_plan(requests_per_second: int = 2200, cities: int = 8) -> dict[str, int]:
    return parallel_booking_plan(requests_per_second, cities)


@app.get("/search/shards")
async def search_shards(cities: str = "Москва,Санкт-Петербург,Казань,Екатеринбург") -> dict[str, Any]:
    city_list = [city.strip() for city in cities.split(",") if city.strip()]
    return {"shards": split_search_shards(city_list, max_shards=8), "count": len(city_list)}
