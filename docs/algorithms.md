# Algorithms and Logic

## 1. Price quote

`listing-service` computes quote by dates:

- `nights = check_out - check_in`
- short-term listing uses `daily_price`
- long-term listing uses `monthly_price / 30`
- total = `nightly * nights`
- deposit is included separately

## 2. Availability and blocking

`booking-service` checks overlap by interval intersection:

- overlap when `left_start < right_end` and `right_start < left_end`
- blocking uses per-listing async lock to reduce concurrent race on same listing

## 3. Search optimization

`search-service` stores query results in TTL cache keyed by request body.

- cache hit reduces response time and keeps SLA under 2 sec
- misses are indexed in cache stats for monitoring

## 4. Recommendations

`recommend_listings` scores candidates by:

- city match
- property type match
- budget distance
- room fit
- historical rating

## 5. Fraud signals

`detect_fraud_listing` emits findings for:

- critically low price-to-market ratio
- repeated contact changes
- high duplicate-media ratio
- suspicious high-traffic underpricing pattern

## 6. Demand forecast

`demand_forecast` estimates next 30-day bookings from recent history:

- monthly forecast = `avg_daily * 30 * season_multiplier * event_multiplier`
