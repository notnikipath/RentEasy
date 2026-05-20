# Architecture

RentEasy is designed as a microservice platform for rental operations with a gateway-driven orchestration layer.

## Service responsibilities

- `api-gateway`: auth, health aggregation, booking workflow orchestration, host dashboard aggregation
- `listing-service`: listing lifecycle, media and floor plans, map coordinates, quote calculation
- `search-service`: filter-based search, saved queries, cache, recommendation feed
- `booking-service`: availability checks, booking records, date blocking, confirmation and cancellation
- `payment-service`: payment intent, capture, refund
- `chat-service`: tenant-host chat and viewing request handling
- `review-service`: reviews and rating aggregation for listings and hosts
- `analytics-service`: search/booking latency KPIs, profitability, occupancy, demand forecast
- `notification-service`: unified outbound notifications

## Storage and infrastructure

- PostgreSQL: durable storage target for listings, bookings, payments, reviews (in this educational build services keep in-memory state)
- Redis: cache and Celery broker
- Elasticsearch: search index target

## Core workflow: create booking

1. Gateway requests listing details from `listing-service`
2. Gateway checks date availability in `booking-service`
3. Gateway requests quote from `listing-service`
4. Gateway creates booking in `booking-service`
5. Gateway blocks dates in `booking-service`
6. Gateway creates and captures payment in `payment-service`
7. Gateway sends host notification via `notification-service`
8. Gateway writes booking and latency events to `analytics-service`

## Reliability and scaling notes

- Search caching and sharding plan reduce latency spikes
- Booking date blocking uses per-listing async lock to reduce race conditions
- KPI endpoints track SLA compliance:
  - search time target `< 2 sec`
  - booking time target `< 5 sec`
- Listing capacity target stored as `1,000,000`
