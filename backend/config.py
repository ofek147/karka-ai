from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    govmap_token: str = ""
    govmap_domain: str = "karka-ai.co.il"
    redis_url: str = "redis://localhost:6379"
    cache_ttl_seconds: int = 86400
    mock_mode: bool = True
    anthropic_api_key: str = ""
    database_url: str = ""  # Railway sets this automatically; empty = SQLite fallback

    class Config:
        env_file = ".env"


settings = Settings()
