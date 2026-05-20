from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException

from shared.renteasy_common import (
    ReviewCreateRequest,
    ReviewRecord,
    ReviewTargetType,
    Settings,
    average_rating,
    has_permission,
)

settings = Settings(service_name="review-service", service_port=8406)
app = FastAPI(title="RentEasy Review Service", version="1.0.0")


reviews: list[ReviewRecord] = [
    ReviewRecord(
        review_id="REV-SEED-1",
        target_type=ReviewTargetType.LISTING,
        target_id="LIST-DEMO-APT",
        listing_id="LIST-DEMO-APT",
        host_id="HOST-001",
        author_id="TENANT-041",
        rating=5,
        comment="Квартира чистая, владелец на связи, всё как на фото.",
    ),
    ReviewRecord(
        review_id="REV-SEED-2",
        target_type=ReviewTargetType.HOST,
        target_id="HOST-001",
        listing_id="LIST-DEMO-APT",
        host_id="HOST-001",
        author_id="TENANT-086",
        rating=4,
        comment="Оперативно согласовали просмотр и заселение.",
    ),
]


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.post("/reviews")
async def create_review(request: ReviewCreateRequest) -> dict[str, Any]:
    if not has_permission(request.actor_role, "review:create"):
        raise HTTPException(status_code=403, detail="Forbidden")
    item = ReviewRecord(
        review_id=str(uuid4()),
        target_type=request.target_type,
        target_id=request.target_id,
        listing_id=request.listing_id,
        host_id=request.host_id,
        author_id=request.author_id,
        rating=request.rating,
        comment=request.comment,
    )
    reviews.append(item)
    return item.model_dump(mode="json")


@app.get("/reviews/listing/{listing_id}")
async def listing_reviews(listing_id: str) -> dict[str, Any]:
    items = [review.model_dump(mode="json") for review in reviews if review.listing_id == listing_id]
    return {"items": items, "count": len(items), "avg_rating": average_rating([item["rating"] for item in items])}


@app.get("/reviews/host/{host_id}")
async def host_reviews(host_id: str) -> dict[str, Any]:
    items = [review.model_dump(mode="json") for review in reviews if review.host_id == host_id]
    return {"items": items, "count": len(items), "avg_rating": average_rating([item["rating"] for item in items])}


@app.get("/ratings/listing/{listing_id}")
async def listing_rating(listing_id: str) -> dict[str, Any]:
    items = [review.rating for review in reviews if review.listing_id == listing_id]
    if not items:
        raise HTTPException(status_code=404, detail="Listing has no ratings yet")
    return {"listing_id": listing_id, "rating": average_rating(items), "votes": len(items)}


@app.get("/ratings/host/{host_id}")
async def host_rating(host_id: str) -> dict[str, Any]:
    items = [review.rating for review in reviews if review.host_id == host_id]
    if not items:
        raise HTTPException(status_code=404, detail="Host has no ratings yet")
    return {"host_id": host_id, "rating": average_rating(items), "votes": len(items)}
