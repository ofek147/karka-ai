from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    govmap_token: str = ""
    govmap_domain: str = "karka-ai.co.il"
    mock_mode: bool = False  # Override with MOCK_MODE=true for local dev
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
