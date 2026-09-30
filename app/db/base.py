"""
Async SQLAlchemy engine/session setup — nexus-fleet-service.

Same pattern established in nexus-identity-service's DB migration and
carried into nexus-financials-service/nexus-hr-service's write slices:
SQLite by default (`settings.DATABASE_URL`) for zero-setup local dev,
swappable to a Postgres DSN (install `asyncpg`) for staging/production
with no code change elsewhere.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    pass


def _build_engine():
    url = settings.DATABASE_URL
    kwargs: dict = {}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_async_engine(url, **kwargs)


engine = _build_engine()
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def create_all_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
