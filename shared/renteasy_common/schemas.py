from __future__ import annotations

from datetime import UTC, date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class PropertyType(str, Enum):
    APARTMENT = "apartment"
    ROOM = "room"
    HOUSE = "house"
    COTTAGE = "cottage"
    OFFICE = "office"
    WAREHOUSE = "warehouse"


class RentalMode(str, Enum):
    LONG_TERM = "long_term"
    SHORT_TERM = "short_term"


class MediaType(str, Enum):
    PHOTO = "photo"
    VIDEO = "video"
    FLOOR_PLAN = "floor_plan"


class ListingStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    HIDDEN = "hidden"
    ARCHIVED = "archived"


class BookingStatus(str, Enum):
    CREATED = "created"
    PENDING_PAYMENT = "pending_payment"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    AUTHORIZED = "authorized"
    CAPTURED = "captured"
    REFUNDED = "refunded"
    FAILED = "failed"


class Role(str, Enum):
    TENANT = "tenant"
    HOST = "host"
    MANAGER = "manager"
    SUPPORT = "support"
    ADMIN = "admin"


class NotificationChannel(str, Enum):
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    WEBHOOK = "webhook"


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class ReviewTargetType(str, Enum):
    LISTING = "listing"
    HOST = "host"


class MediaAsset(BaseModel):
    media_id: str
    media_type: MediaType
    url: str
    is_primary: bool = False
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class GeoPoint(BaseModel):
    city: str
    district: str
    address: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class ListingPricing(BaseModel):
    daily_price: float = Field(ge=0)
    monthly_price: float = Field(ge=0)
    deposit: float = Field(ge=0)
    currency: str = "RUB"


class ListingCreateRequest(BaseModel):
    host_id: str
    title: str
    description: str
    property_type: PropertyType
    rental_mode: RentalMode = RentalMode.LONG_TERM
    rooms: float = Field(gt=0)
    area_m2: float = Field(gt=0)
    floor: int | None = Field(default=None, ge=0)
    is_furnished: bool = False
    pets_allowed: bool = False
    geo: GeoPoint
    pricing: ListingPricing
    available_from: date
    available_to: date | None = None
    amenities: list[str] = Field(default_factory=list)
    actor_id: str
    actor_role: Role


class ListingUpdateRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    rental_mode: RentalMode | None = None
    rooms: float | None = Field(default=None, gt=0)
    area_m2: float | None = Field(default=None, gt=0)
    floor: int | None = Field(default=None, ge=0)
    is_furnished: bool | None = None
    pets_allowed: bool | None = None
    pricing: ListingPricing | None = None
    available_from: date | None = None
    available_to: date | None = None
    amenities: list[str] | None = None
    status: ListingStatus | None = None
    actor_id: str
    actor_role: Role


class ListingRecord(BaseModel):
    listing_id: str
    host_id: str
    title: str
    description: str
    property_type: PropertyType
    rental_mode: RentalMode
    rooms: float
    area_m2: float
    floor: int | None = None
    is_furnished: bool = False
    pets_allowed: bool = False
    geo: GeoPoint
    pricing: ListingPricing
    available_from: date
    available_to: date | None = None
    amenities: list[str] = Field(default_factory=list)
    media: list[MediaAsset] = Field(default_factory=list)
    status: ListingStatus = ListingStatus.ACTIVE
    rating_avg: float = Field(default=0.0, ge=0, le=5)
    views: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SearchRequest(BaseModel):
    city: str | None = None
    district: str | None = None
    property_type: PropertyType | None = None
    rental_mode: RentalMode | None = None
    min_price: float | None = Field(default=None, ge=0)
    max_price: float | None = Field(default=None, ge=0)
    min_area: float | None = Field(default=None, ge=0)
    max_area: float | None = Field(default=None, ge=0)
    pets_allowed: bool | None = None
    furnished_only: bool = False
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=100)


class SavedSearchRequest(BaseModel):
    user_id: str
    name: str
    query: SearchRequest


class SavedSearch(BaseModel):
    search_id: str
    user_id: str
    name: str
    query: SearchRequest
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AvailabilityCheckRequest(BaseModel):
    listing_id: str
    check_in: date
    check_out: date


class AvailabilityBlockRequest(BaseModel):
    listing_id: str
    booking_id: str
    check_in: date
    check_out: date
    actor_id: str
    actor_role: Role


class BookingCreateRequest(BaseModel):
    user_id: str
    host_id: str
    listing_id: str
    check_in: date
    check_out: date
    guests: int = Field(default=1, ge=1, le=20)
    nightly_price: float = Field(ge=0)
    total_price: float = Field(ge=0)
    deposit: float = Field(ge=0)
    actor_id: str
    actor_role: Role


class BookingRecord(BaseModel):
    booking_id: str
    user_id: str
    host_id: str
    listing_id: str
    check_in: date
    check_out: date
    guests: int
    nights: int = Field(ge=1)
    nightly_price: float = Field(ge=0)
    total_price: float = Field(ge=0)
    deposit: float = Field(ge=0)
    status: BookingStatus = BookingStatus.CREATED
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class PaymentIntentRequest(BaseModel):
    booking_id: str
    payer_id: str
    amount: float = Field(gt=0)
    currency: str = "RUB"
    payment_method: str = "card"
    actor_role: Role


class PaymentRecord(BaseModel):
    payment_id: str
    booking_id: str
    payer_id: str
    amount: float
    currency: str
    payment_method: str
    status: PaymentStatus
    provider_reference: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ChatMessageRequest(BaseModel):
    conversation_id: str
    listing_id: str
    sender_id: str
    recipient_id: str
    text: str = Field(min_length=1, max_length=2000)
    actor_role: Role


class ChatMessage(BaseModel):
    message_id: str
    conversation_id: str
    listing_id: str
    sender_id: str
    recipient_id: str
    text: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ViewingRequest(BaseModel):
    listing_id: str
    user_id: str
    host_id: str
    desired_datetime: datetime
    note: str = ""
    actor_role: Role


class ViewingRecord(BaseModel):
    viewing_id: str
    listing_id: str
    user_id: str
    host_id: str
    desired_datetime: datetime
    note: str
    status: str = "pending"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ReviewCreateRequest(BaseModel):
    target_type: ReviewTargetType
    target_id: str
    listing_id: str
    host_id: str
    author_id: str
    rating: int = Field(ge=1, le=5)
    comment: str = Field(min_length=3, max_length=1500)
    actor_role: Role


class ReviewRecord(BaseModel):
    review_id: str
    target_type: ReviewTargetType
    target_id: str
    listing_id: str
    host_id: str
    author_id: str
    rating: int
    comment: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class NotificationPayload(BaseModel):
    channel: NotificationChannel
    recipient: str
    subject: str
    body: str
    severity: Severity = Severity.INFO
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ViewEvent(BaseModel):
    listing_id: str
    user_id: str | None = None
    session_id: str
    city: str
    duration_seconds: int = Field(default=0, ge=0)


class BookingAnalyticsEvent(BaseModel):
    booking_id: str
    listing_id: str
    host_id: str
    amount: float = Field(ge=0)
    status: BookingStatus


class SearchLatencyEvent(BaseModel):
    latency_ms: float = Field(ge=0)


class BookingLatencyEvent(BaseModel):
    latency_ms: float = Field(ge=0)


class AuditEvent(BaseModel):
    event_id: str
    actor_id: str
    actor_role: Role | str
    action: str
    object_type: str
    object_id: str
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CreateBookingWorkflowResult(BaseModel):
    availability: dict[str, Any]
    quote: dict[str, Any]
    booking: dict[str, Any]
    blocked_dates: dict[str, Any]
    payment: dict[str, Any]
    notification: dict[str, Any]
    total_latency_ms: float
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
