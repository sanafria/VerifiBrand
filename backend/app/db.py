"""Database Connection and Pool Manager for PostgreSQL / Supabase.

Uses asyncpg connection pool with automatic initialization, graceful teardown,
and helper methods for queries and transactions.
"""
import json
import logging
from typing import Any, List, Optional
import asyncpg
from backend.app.config import settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    """PostgreSQL database manager using asyncpg connection pool."""

    def __init__(self) -> None:
        self.pool: Optional[asyncpg.Pool] = None

    def _is_pool_valid(self) -> bool:
        """Check if pool exists and its event loop is still running."""
        if self.pool is None:
            return False
        try:
            loop = getattr(self.pool, "_loop", None)
            if loop is not None and loop.is_closed():
                return False
        except Exception:
            return False
        return True

    async def connect(self) -> None:
        """Initialize the connection pool."""
        if not self._is_pool_valid():
            self.pool = None
        if self.pool is not None:
            return

        dsn = settings.DATABASE_URL
        if not dsn:
            logger.warning("DATABASE_URL not configured. Running without live database pool.")
            return

        try:
            self.pool = await asyncpg.create_pool(
                dsn=dsn,
                min_size=1,
                max_size=10,
                timeout=10.0,
            )
            logger.info("Database connection pool established.")
        except Exception as exc:
            logger.error(f"Failed to connect to database: {exc}")
            self.pool = None
            raise

    async def disconnect(self) -> None:
        """Close the connection pool."""
        if self.pool is not None:
            try:
                loop = getattr(self.pool, "_loop", None)
                if loop is not None and not loop.is_closed():
                    await self.pool.close()
            except Exception:
                pass
            finally:
                self.pool = None
            logger.info("Database connection pool closed.")

    @property
    def is_connected(self) -> bool:
        """Return True if connection pool is active."""
        return self._is_pool_valid()

    async def fetch(self, query: str, *args: Any) -> List[asyncpg.Record]:
        """Execute a SELECT query and return all matching records."""
        if not self._is_pool_valid():
            self.pool = None
            await self.connect()
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query: str, *args: Any) -> Optional[asyncpg.Record]:
        """Execute a SELECT query and return a single record or None."""
        if not self._is_pool_valid():
            self.pool = None
            await self.connect()
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def execute(self, query: str, *args: Any) -> str:
        """Execute an INSERT, UPDATE, or DELETE statement."""
        if not self._is_pool_valid():
            self.pool = None
            await self.connect()
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)


db_manager = DatabaseManager()
