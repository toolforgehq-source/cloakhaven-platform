import os
import secrets

from pydantic_settings import BaseSettings

# Use persistent volume path on Fly.io, local file otherwise
_default_db_path = "/data/app.db" if os.path.isdir("/data") else "./cloakhaven.db"


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Cloak Haven"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    SECRET_KEY: str = os.environ.get("SECRET_KEY", secrets.token_urlsafe(32))

    # Database — uses SQLite; auto-detects /data volume for Fly.io
    DATABASE_URL: str = f"sqlite+aiosqlite:///{_default_db_path}"

    # JWT
    JWT_SECRET_KEY: str = os.environ.get("JWT_SECRET_KEY", secrets.token_urlsafe(32))
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

    # Google Custom Search (deprecated — using SerpAPI instead)
    GOOGLE_API_KEY: str = ""
    GOOGLE_SEARCH_ENGINE_ID: str = ""

    # SerpAPI (Google search results proxy)
    SERPAPI_API_KEY: str = ""

    # Reddit API
    REDDIT_CLIENT_ID: str = ""
    REDDIT_CLIENT_SECRET: str = ""
    REDDIT_USER_AGENT: str = "CloakHaven/1.0"

    # YouTube Data API
    YOUTUBE_API_KEY: str = ""

    # Data Enrichment APIs
    PEOPLEDATALABS_API_KEY: str = ""

    # AI/LLM for content classification
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    LLM_PROVIDER: str = "anthropic"  # openai or anthropic

    # Email — supports SMTP or SendGrid API
    EMAIL_PROVIDER: str = "sendgrid"  # "smtp" or "sendgrid"
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SENDGRID_API_KEY: str = ""
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
