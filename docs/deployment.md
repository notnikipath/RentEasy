# Deployment

## Local prerequisites

- Docker Desktop with Compose v2
- Python 3.11+ (for local tests/lint)

## Start stack

```bash
docker compose up --build -d
```

## Stop stack

```bash
docker compose down
```

## Validate config

```bash
docker compose config
```

## Health check

- `http://localhost:8480/health`
- `http://localhost:8480/services/health`

## Notes

- This academic version keeps runtime state in-memory for fast demo and testing
- Production rollout should move entities to PostgreSQL and enable real Elasticsearch indexing and Celery workers
