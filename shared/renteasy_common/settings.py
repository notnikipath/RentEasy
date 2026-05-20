from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_name: str = "renteasy-service"
    service_port: int = 8400
    environment: str = "dev"

    postgres_dsn: str = "postgresql+psycopg://renteasy:renteasy@postgres:5432/renteasy"
    redis_url: str = "redis://redis:6379/0"
    elasticsearch_url: str = "http://elasticsearch:9200"
    celery_broker_url: str = "redis://redis:6379/1"
    stripe_api_base: str = "https://api.stripe.com"

    jwt_secret: str = "renteasy-dev-secret"
    encryption_key: str = "renteasy-dev-encryption-key"

    search_target_seconds: float = 2.0
    booking_target_seconds: float = 5.0
    listing_capacity_target: int = 1_000_000

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
