# API Overview

## Gateway

- `GET /health`
- `GET /services/health`
- `POST /auth/token`
- `POST /auth/verify`
- `POST /workflow/create-booking`
- `POST /workflow/request-viewing`
- `GET /dashboard/{host_id}`

## Listing service

- `GET /listings`
- `GET /listings/{listing_id}`
- `POST /listings`
- `PUT /listings/{listing_id}`
- `POST /listings/{listing_id}/media`
- `POST /listings/{listing_id}/view`
- `GET /listings/{listing_id}/price-quote`
- `GET /hosts/{host_id}/listings`
- `GET /fraud/check/{listing_id}`

## Search service

- `POST /search/index`
- `POST /search/query`
- `POST /search/saved`
- `GET /search/saved/{user_id}`
- `POST /search/recommendations`
- `GET /search/cache/stats`
- `GET /search/shards`

## Booking service

- `POST /availability/check`
- `GET /availability/{listing_id}`
- `POST /bookings`
- `POST /availability/block`
- `POST /bookings/{booking_id}/confirm`
- `POST /bookings/{booking_id}/cancel`
- `GET /bookings/user/{user_id}`
- `GET /bookings/host/{host_id}`

## Payment service

- `POST /payments/intent`
- `POST /payments/{payment_id}/capture`
- `POST /payments/{payment_id}/refund`
- `GET /payments/{payment_id}`
- `GET /payments/booking/{booking_id}`

## Chat and review services

- `POST /chats/messages`
- `GET /chats/{conversation_id}`
- `POST /viewings/request`
- `POST /reviews`
- `GET /reviews/listing/{listing_id}`
- `GET /reviews/host/{host_id}`
- `GET /ratings/listing/{listing_id}`
- `GET /ratings/host/{host_id}`

## Analytics service

- `POST /analytics/events/view`
- `POST /analytics/events/booking`
- `POST /analytics/events/search-latency`
- `POST /analytics/events/booking-latency`
- `GET /analytics/listing/{listing_id}`
- `GET /analytics/owner/{host_id}`
- `GET /analytics/kpi`
- `GET /analytics/demand-forecast`
