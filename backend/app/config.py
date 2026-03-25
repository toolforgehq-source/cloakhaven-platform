from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Cloak Haven"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production-use-a-real-secret-key"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/cloakhaven"

    # JWT
    JWT_SECRET_KEY: str = "change-me-jwt-secret-key"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Stripe
    STRIPE_SECRET_KEY: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_AUDIT_PRICE_ID: str = ""  # $19 one-time
    STRIPE_SUBSCRIBER_PRICE_ID: str = ""  # $9/month
    STRIPE_EMPLOYER_PRICE_ID: str = ""  # $49/month

    # X/Twitter API
    TWITTER_API_KEY: str = ""
    TWITTER_API_SECRET: str = ""
    TWITTER_BEARER_TOKEN: str = ""

    # Google Custom Search
    GOOGLE_API_KEY: str = ""
    GOOGLE_SEARCH_ENGINE_ID: str = ""

    # AI/LLM for content classification
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    LLM_PROVIDER: str = "openai"  # openai or anthropic

    # Email
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    FROM_EMAIL: str = "hello@cloakhaven.com"
    EMAIL_FROM_HELLO: str = "hello@cloakhaven.com"
    EMAIL_FROM_SUPPORT: str = "support@cloakhaven.com"
    EMAIL_FROM_PRIVACY: str = "privacy@cloakhaven.com"

    # Frontend URL (for email links, CORS, etc.)
    FRONTEND_URL: str = "http://localhost:5173"

    # File upload
    MAX_UPLOAD_SIZE_MB: int = 5120  # 5GB
    TEMP_UPLOAD_DIR: str = "/tmp/cloakhaven-uploads"

    # Score refresh
    PUBLIC_SCORE_REFRESH_DAYS: int = 30

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
