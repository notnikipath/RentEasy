# Project Report (Task 27)

## Project

RentEasy - платформа для аренды жилой и коммерческой недвижимости.

## Goal

Реализовать единый контур:

- публикация объявлений
- фильтруемый поиск
- онлайн-бронирование и блокировка дат
- безопасная оплата
- чат и запросы на просмотр
- отзывы и рейтинги
- аналитика владельца и системные KPI

## Architecture summary

- Backend: FastAPI microservices
- Data stack: PostgreSQL + Redis + Elasticsearch
- Gateway orchestration for key workflows
- React dashboard for host and operations visibility

## Required functionality status

- Property types: covered (квартиры/комнаты, дома/коттеджи, офисы/склады, посуточная аренда)
- Listing module: CRUD + media + geo + quote
- Search module: filters + save search + recommendations + cache
- Booking module: availability + create booking + date blocking
- Communication module: chat + viewing requests + chatbot hints
- Payment module: intent/capture/refund
- Review module: ratings for listing and host
- Analytics module: views, profitability, KPI, demand forecast

## Quality metrics

- Search target: `< 2 sec` (tracked via analytics KPI)
- Booking target: `< 5 sec` (tracked via analytics KPI)
- Capacity target: `1,000,000 listings` (config-level KPI target)

## Test status

- Unit tests for pricing/recommendation/fraud/security/helpers
- Integration tests for end-to-end booking/payment and chat/review/analytics flows
