"""
ADAPT — Database Engine & Session Management

Async SQLAlchemy setup for local SQLite database.
"""

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

settings = get_settings()

# SQLite doesn't support pool_size/max_overflow, so conditionally set engine args
_engine_kwargs = {
    "echo": settings.debug,
}
if "sqlite" not in settings.database_url:
    _engine_kwargs.update({
        "pool_size": 20,
        "max_overflow": 10,
        "pool_pre_ping": True,
    })

engine = create_async_engine(
    settings.database_url,
    **_engine_kwargs,
)

# Configure SQLite concurrency settings (WAL mode + 60s busy timeout)
if "sqlite" in settings.database_url:
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA busy_timeout=60000;")  # wait up to 60s instead of throwing locked error
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.close()

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


async def get_db() -> AsyncSession:
    """FastAPI dependency that yields a database session per request."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def _sync_create_and_migrate(connection):
    import app.models  # ensure all models are registered
    Base.metadata.create_all(connection)

    # SQLite automatic schema migration for newly added columns
    if "sqlite" in connection.dialect.name.lower():
        from sqlalchemy import text
        from sqlalchemy.dialects import sqlite
        dialect = sqlite.dialect()

        for table_name, table in Base.metadata.tables.items():
            res = connection.execute(text(f"PRAGMA table_info({table_name})"))
            existing_cols = {row[1] for row in res.fetchall()}
            if not existing_cols:
                continue
            for col in table.columns:
                if col.name not in existing_cols:
                    col_type = col.type.compile(dialect=dialect)
                    connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {col.name} {col_type}"))


async def init_db():
    """Create all tables and perform lightweight schema migrations."""
    async with engine.begin() as conn:
        await conn.run_sync(_sync_create_and_migrate)
