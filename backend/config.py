from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    govmap_token: str = ""
    govmap_domain: str = "karka-ai.co.il"
    redis_url: str = "redis://localhost:6379"
    cache_ttl_seconds: int = 86400
    mock_mode: bool = True
    anthropic_api_key: str = ""
    database_url: str = ""  # Required — set DATABASE_URL in Railway environment variables
    openai_api_key: str = ""
    resend_api_key: str = ""
    frontend_url: str = "https://karka-ai.co.il"
    admin_email: str = ""    # Approved admin email — set ADMIN_EMAIL in Railway
    admin_secret: str = ""   # Auto-generated session secret — set ADMIN_SECRET in Railway

    class Config:
        env_file = ".env"


settings = Settings()
