import logging

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import event, text
from app.config import settings

logger = logging.getLogger(__name__)

is_sqlite = settings.DATABASE_URL.startswith("sqlite")

engine_kwargs: dict = {
    "echo": settings.DEBUG,
}

if is_sqlite:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_size"] = 20
    engine_kwargs["max_overflow"] = 10

engine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


# Register SQLite foreign key pragma once at module level (not inside init_db)
if is_sqlite:
    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Safe column migrations for existing deployments (create_all won't ALTER)
    await _run_safe_migrations()


async def _run_safe_migrations():
    """Add columns that create_all() can't add to existing tables."""
    migrations = [
        ("disputes", "deadline_at", "DATETIME"),
        # Passive scan accuracy fields on public_profiles
        ("public_profiles", "identity_confidence", "FLOAT DEFAULT 0.0"),
        ("public_profiles", "match_context", "JSON"),
        ("public_profiles", "identity_match_reasoning", "VARCHAR(2000)"),
        ("public_profiles", "sources_scanned", "JSON"),
        ("public_profiles", "social_media_score", "INTEGER"),
        ("public_profiles", "web_presence_score", "INTEGER"),
        ("public_profiles", "posting_behavior_score", "INTEGER"),
        ("public_profiles", "total_findings_count", "INTEGER DEFAULT 0"),
        ("public_profiles", "scan_duration_seconds", "FLOAT"),
    ]
    async with engine.begin() as conn:
        for table, column, col_type in migrations:
            try:
                await conn.execute(
                    text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
                )
                logger.info("Migration: added %s.%s", table, column)
            except Exception:
                # Column already exists — safe to ignore
                pass
