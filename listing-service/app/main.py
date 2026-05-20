from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from shared.renteasy_common import (
    ListingCreateRequest,
    ListingRecord,
    ListingStatus,
    ListingUpdateRequest,
    MediaAsset,
    MediaType,
    PropertyType,
    RentalMode,
    Role,
    Settings,
    build_audit_event,
    detect_fraud_listing,
    estimate_rent_price,
    has_permission,
)

settings = Settings(service_name="listing-service", service_port=8401)
app = FastAPI(title="RentEasy Listing Service", version="1.0.0")


class MediaCreateRequest(BaseModel):
    media_type: MediaType
    url: str
    is_primary: bool = False
    actor_id: str
    actor_role: Role


class ViewTrackRequest(BaseModel):
    session_id: str | None = None


MediaCreateRequest.model_rebuild()
ViewTrackRequest.model_rebuild()


def _seed_listings() -> dict[str, ListingRecord]:
    now = datetime.now(UTC)
    return {
        "LIST-DEMO-APT": ListingRecord(
            listing_id="LIST-DEMO-APT",
            host_id="HOST-001",
            title="2-комнатная квартира рядом с метро",
            description="Светлая квартира после ремонта, 7 минут до метро, закрытый двор.",
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
            amenities=["wifi", "parking", "washing_machine"],
            media=[
                MediaAsset(
                    media_id="MEDIA-APT-1",
                    media_type=MediaType.PHOTO,
                    url="https://cdn.renteasy.local/listings/apt-1.jpg",
                    is_primary=True,
                ),
                MediaAsset(
                    media_id="MEDIA-APT-PLAN",
                    media_type=MediaType.FLOOR_PLAN,
                    url="https://cdn.renteasy.local/listings/apt-1-plan.pdf",
                ),
            ],
            status=ListingStatus.ACTIVE,
            rating_avg=4.8,
            views=214,
            created_at=now,
            updated_at=now,
        ),
        "LIST-DEMO-OFFICE": ListingRecord(
            listing_id="LIST-DEMO-OFFICE",
            host_id="HOST-002",
            title="Офис 120 м2 в бизнес-центре",
            description="Офис open-space, переговорная, доступ 24/7, парковка для арендаторов.",
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
            amenities=["elevator", "security", "meeting_room"],
            media=[
                MediaAsset(
                    media_id="MEDIA-OFFICE-1",
                    media_type=MediaType.PHOTO,
                    url="https://cdn.renteasy.local/listings/office-1.jpg",
                    is_primary=True,
                )
            ],
            status=ListingStatus.ACTIVE,
            rating_avg=4.6,
            views=141,
            created_at=now,
            updated_at=now,
        ),
        "LIST-DEMO-DAILY": ListingRecord(
            listing_id="LIST-DEMO-DAILY",
            host_id="HOST-003",
            title="Студия посуточно у набережной",
            description="Студия для короткой аренды, бесконтактное заселение, кондиционер.",
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
            amenities=["wifi", "air_conditioning", "smart_lock"],
            media=[
                MediaAsset(
                    media_id="MEDIA-DAILY-1",
                    media_type=MediaType.PHOTO,
                    url="https://cdn.renteasy.local/listings/daily-1.jpg",
                    is_primary=True,
                ),
                MediaAsset(
                    media_id="MEDIA-DAILY-2",
                    media_type=MediaType.VIDEO,
                    url="https://cdn.renteasy.local/listings/daily-1-tour.mp4",
                ),
            ],
            status=ListingStatus.ACTIVE,
            rating_avg=4.9,
            views=388,
            created_at=now,
            updated_at=now,
        ),
    }


listings: dict[str, ListingRecord] = _seed_listings()
audit_log: list[dict[str, Any]] = []


def _assert_permission(role: Role, action: str) -> None:
    if not has_permission(role, action):
        raise HTTPException(status_code=403, detail=f"Role {role.value} cannot perform {action}")


def _audit(actor_id: str, actor_role: Role, action: str, object_id: str, details: dict[str, Any] | None = None) -> None:
    audit_log.append(
        build_audit_event(
            actor_id=actor_id,
            actor_role=actor_role,
            action=action,
            object_type="listing",
            object_id=object_id,
            details=details or {},
        ).model_dump(mode="json")
    )


def _is_visible(listing: ListingRecord) -> bool:
    return listing.status in {ListingStatus.ACTIVE, ListingStatus.HIDDEN}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.get("/listings")
async def list_listings(
    city: str | None = None,
    district: str | None = None,
    property_type: PropertyType | None = None,
    rental_mode: RentalMode | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    min_area: float | None = None,
    max_area: float | None = None,
    pets_allowed: bool | None = None,
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for listing in listings.values():
        if not _is_visible(listing):
            continue
        if city and listing.geo.city.lower() != city.lower():
            continue
        if district and listing.geo.district.lower() != district.lower():
            continue
        if property_type and listing.property_type != property_type:
            continue
        if rental_mode and listing.rental_mode != rental_mode:
            continue
        monthly_price = listing.pricing.monthly_price
        if min_price is not None and monthly_price < min_price:
            continue
        if max_price is not None and monthly_price > max_price:
            continue
        if min_area is not None and listing.area_m2 < min_area:
            continue
        if max_area is not None and listing.area_m2 > max_area:
            continue
        if pets_allowed is not None and listing.pets_allowed != pets_allowed:
            continue
        items.append(listing.model_dump(mode="json"))

    items.sort(key=lambda item: (item["pricing"]["monthly_price"], -item["rating_avg"]))
    return {"items": items, "count": len(items)}


@app.get("/listings/{listing_id}")
async def get_listing(listing_id: str, actor_role: Role = Role.TENANT) -> dict[str, Any]:
    _assert_permission(actor_role, "listing:read")
    listing = listings.get(listing_id)
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing.model_dump(mode="json")


@app.post("/listings")
async def create_listing(request: ListingCreateRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "listing:create")
    listing = ListingRecord(
        listing_id=str(uuid4()),
        host_id=request.host_id,
        title=request.title,
        description=request.description,
        property_type=request.property_type,
        rental_mode=request.rental_mode,
        rooms=request.rooms,
        area_m2=request.area_m2,
        floor=request.floor,
        is_furnished=request.is_furnished,
        pets_allowed=request.pets_allowed,
        geo=request.geo,
        pricing=request.pricing,
        available_from=request.available_from,
        available_to=request.available_to,
        amenities=request.amenities,
        status=ListingStatus.ACTIVE,
    )
    listings[listing.listing_id] = listing
    _audit(request.actor_id, request.actor_role, "listing.create", listing.listing_id)
    return listing.model_dump(mode="json")


@app.put("/listings/{listing_id}")
async def update_listing(listing_id: str, request: ListingUpdateRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "listing:update")
    listing = listings.get(listing_id)
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")

    for field in [
        "title",
        "description",
        "rental_mode",
        "rooms",
        "area_m2",
        "floor",
        "is_furnished",
        "pets_allowed",
        "pricing",
        "available_from",
        "available_to",
        "amenities",
        "status",
    ]:
        value = getattr(request, field)
        if value is not None:
            setattr(listing, field, value)

    listing.updated_at = datetime.now(UTC)
    _audit(request.actor_id, request.actor_role, "listing.update", listing_id)
    return listing.model_dump(mode="json")


@app.post("/listings/{listing_id}/media")
async def add_media(listing_id: str, request: MediaCreateRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "listing:update")
    listing = listings.get(listing_id)
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")

    if request.is_primary:
        for item in listing.media:
            item.is_primary = False

    media = MediaAsset(
        media_id=str(uuid4()),
        media_type=request.media_type,
        url=request.url,
        is_primary=request.is_primary,
    )
    listing.media.append(media)
    listing.updated_at = datetime.now(UTC)

    _audit(request.actor_id, request.actor_role, "listing.media.add", listing_id, {"media_id": media.media_id})
    return media.model_dump(mode="json")


@app.post("/listings/{listing_id}/view")
async def register_view(listing_id: str, request: ViewTrackRequest) -> dict[str, Any]:
    listing = listings.get(listing_id)
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    listing.views += 1
    listing.updated_at = datetime.now(UTC)
    return {"listing_id": listing_id, "views": listing.views, "session_id": request.session_id}


@app.get("/listings/{listing_id}/price-quote")
async def calculate_price(listing_id: str, check_in: date, check_out: date) -> dict[str, Any]:
    listing = listings.get(listing_id)
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")

    nights = (check_out - check_in).days
    if nights <= 0:
        raise HTTPException(status_code=400, detail="check_out must be greater than check_in")

    if listing.rental_mode == RentalMode.SHORT_TERM:
        nightly = listing.pricing.daily_price or estimate_rent_price(
            listing.area_m2,
            base_rate_per_m2=listing.pricing.monthly_price / max(listing.area_m2, 1),
            district_index=1.0,
            furnished=listing.is_furnished,
            short_term=True,
        )
    else:
        nightly = round((listing.pricing.monthly_price / 30), 2)

    total = round(nightly * nights, 2)
    return {
        "listing_id": listing_id,
        "host_id": listing.host_id,
        "check_in": check_in,
        "check_out": check_out,
        "nights": nights,
        "nightly_price": nightly,
        "total_price": total,
        "deposit": listing.pricing.deposit,
        "currency": listing.pricing.currency,
    }


@app.get("/hosts/{host_id}/listings")
async def host_listings(host_id: str, actor_role: Role = Role.HOST) -> dict[str, Any]:
    _assert_permission(actor_role, "listing:read")
    items = [listing.model_dump(mode="json") for listing in listings.values() if listing.host_id == host_id]
    return {"items": items, "count": len(items)}


@app.get("/fraud/check/{listing_id}")
async def check_fraud(listing_id: str) -> dict[str, Any]:
    listing = listings.get(listing_id)
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")

    market_ratio = listing.pricing.monthly_price / max(
        estimate_rent_price(
            listing.area_m2,
            1800,
            1.0,
            listing.is_furnished,
            False,
        ),
        1,
    )
    findings = detect_fraud_listing(
        view_count=listing.views,
        contact_switches=0,
        price_to_market_ratio=market_ratio,
        duplicate_photo_ratio=0.0,
    )
    return {"listing_id": listing_id, "findings": findings, "risk_score": len(findings) * 25}


@app.get("/audit")
async def get_audit(limit: int = 100, actor_role: Role = Role.ADMIN) -> dict[str, Any]:
    _assert_permission(actor_role, "audit:read")
    return {"items": audit_log[-limit:]}
