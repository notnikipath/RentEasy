# RentEasy

RentEasy is a microservice platform for residential and commercial rental workflows: listing publication, fast search, online booking, secure payment, landlord-tenant chat, ratings, and owner analytics.

## Modules

- `api-gateway` - orchestration, auth, unified workflow endpoints, host dashboard
- `listing-service` - listing CRUD, media, map geo-data, price quote
- `search-service` - filter search, saved searches, caching, recommendations
- `booking-service` - availability calendar, booking creation, date blocking, parallel plan
- `payment-service` - payment intent, capture, refund (Stripe-like flow)
- `chat-service` - chat messages, viewing requests, chatbot hints
- `review-service` - listing and host reviews, rating aggregation
- `analytics-service` - view and booking analytics, owner profitability, KPI targets
- `notification-service` - booking and system notifications
- `frontend` - React dashboard for owner and platform KPI visualization

## Implemented optional improvements

- Group A:
  - Recommendation endpoint (`search-service /search/recommendations`)
  - Rental price estimation helper (`estimate_rent_price`)
  - Demand forecasting endpoint (`analytics-service /analytics/demand-forecast`)
  - Fraud signal endpoint (`listing-service /fraud/check/{listing_id}`)
- Group C:
  - Search result caching (`search-service` in-memory TTL cache)
  - Parallel booking plan (`booking-service /bookings/parallel-plan`)
  - Search sharding plan by cities (`search-service /search/shards`)

## Tech stack

- Backend: Python + FastAPI
- Data: PostgreSQL, Redis, Elasticsearch
- Queue foundation: Celery broker URL configured (Redis)
- Payments: Stripe-style intent/capture abstraction
- Frontend: React + Vite

## Local run

```bash
cd RentEasy
docker compose up --build -d
```

## Useful URLs

- Frontend: `http://localhost:32068`
- Gateway health: `http://localhost:32059/health`
- Services health: `http://localhost:32059/services/health`
- Gateway docs: `http://localhost:32059/docs`

## Validation

```bash
python -m ruff check .
python -m pytest -q
docker compose config
```

## Demo workflow

```bash
python scripts/demo_pipeline.py
```

## Sample data

```bash
python scripts/generate_sample_data.py
```

Result file: `data/samples/rental_events.json`
