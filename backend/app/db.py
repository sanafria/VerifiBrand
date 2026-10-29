"""Database Connection and Pool Manager for PostgreSQL / Supabase.

Uses asyncpg connection pool with automatic initialization, graceful teardown,
and helper methods for queries and transactions.
"""
import asyncio
from contextlib import asynccontextmanager
import json
import logging
from typing import Any, AsyncIterator, List, Optional
import asyncpg
from backend.app.config import settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    """PostgreSQL database manager using asyncpg connection pool."""

    def __init__(self) -> None:
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self) -> None:
        """Initialize the connection pool."""
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None

        if self.pool is not None:
            pool_loop = getattr(self.pool, "_loop", None)
            if pool_loop is not None and (pool_loop.is_closed() or (current_loop and pool_loop is not current_loop)):
                self.pool = None
            else:
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
                await self.pool.close()
            except Exception:
                pass
            finally:
                self.pool = None
                logger.info("Database connection pool closed.")

    @property
    def is_connected(self) -> bool:
        """Return True if connection pool is active."""
        return self.pool is not None

    async def _ensure_pool(self) -> None:
        """Ensure connection pool is initialized and bound to the current running loop."""
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None

        if self.pool is not None:
            pool_loop = getattr(self.pool, "_loop", None)
            if pool_loop is not None and (pool_loop.is_closed() or (current_loop and pool_loop is not current_loop)):
                self.pool = None

        if not self.pool:
            await self.connect()

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[asyncpg.Connection]:
        """Acquire a pooled connection and execute within an atomic transaction.

        - Connects to the database pool if not yet initialized or if the event loop changed.
        - Acquires exactly one pooled connection for the scope of the context.
        - Enters an asyncpg transaction block (`async with conn.transaction():`).
        - Yields the active connection to the caller.
        - Commits automatically upon normal exit.
        - Rolls back automatically if an unhandled exception escapes the block.
        - Releases the connection back to the pool in all exit paths.
        """
        await self._ensure_pool()
        if not self.pool:
            raise RuntimeError("Database connection pool could not be initialized.")

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                yield conn

    async def fetch(
        self,
        query: str,
        *args: Any,
        conn: Optional[asyncpg.Connection] = None,
    ) -> List[asyncpg.Record]:
        """Execute a SELECT query and return all matching records."""
        if conn is not None:
            return await conn.fetch(query, *args)
        await self._ensure_pool()
        async with self.pool.acquire() as acquired_conn:
            return await acquired_conn.fetch(query, *args)

    async def fetchrow(
        self,
        query: str,
        *args: Any,
        conn: Optional[asyncpg.Connection] = None,
    ) -> Optional[asyncpg.Record]:
        """Execute a SELECT query and return a single record or None."""
        if conn is not None:
            return await conn.fetchrow(query, *args)
        await self._ensure_pool()
        async with self.pool.acquire() as acquired_conn:
            return await acquired_conn.fetchrow(query, *args)

    async def execute(
        self,
        query: str,
        *args: Any,
        conn: Optional[asyncpg.Connection] = None,
    ) -> str:
        """Execute an INSERT, UPDATE, or DELETE statement."""
        if conn is not None:
            return await conn.execute(query, *args)
        await self._ensure_pool()
        async with self.pool.acquire() as acquired_conn:
            return await acquired_conn.execute(query, *args)


db_manager = DatabaseManager()
