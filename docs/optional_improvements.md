# Optional Improvements Mapping

## Group A

1. Recommendation system: implemented in `search-service /search/recommendations`
2. Rental price estimation: implemented in `shared/renteasy_common/assignment.py`
3. Demand forecasting: implemented in `analytics-service /analytics/demand-forecast`
4. Fraud detection: implemented in `listing-service /fraud/check/{listing_id}`

## Group B

1. External marketplaces (ЦИАН/Авито): architecture-ready, not connected in this educational build
2. Passport verification: architecture-ready, not connected
3. Bank mortgage integrations: architecture-ready, not connected
4. Tax report export: architecture-ready, not connected

## Group C

1. Search caching: implemented in `search-service` (TTL cache)
2. Parallel booking handling: implemented with lock + parallel planning endpoint
3. City sharding plan: implemented in `search-service /search/shards`
4. Async media upload: service contract prepared through media endpoint abstraction

## Group D

1. Mobile AR viewing: not implemented
2. 360 tours: API-ready via media type `video` and floor-plan attachments
3. Voice search: not implemented
4. Chatbot matching: implemented minimal logic in `chat-service /chatbot/match`
