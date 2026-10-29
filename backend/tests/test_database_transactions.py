"""Focused Unit and Integration Tests for DatabaseManager Transaction Support."""
import uuid
import pytest
import asyncpg

from backend.app.db import db_manager


@pytest.mark.asyncio
async def test_transaction_commits_on_successful_exit():
    """Verify that operations inside transaction context commit when exiting normally."""
    test_id = uuid.uuid4()
    test_title = f"Tx Commit Test {test_id}"

    async with db_manager.transaction() as conn:
        await conn.execute(
            """
            INSERT INTO content_drafts (id, title, content_text, status)
            VALUES ($1, $2, $3, $4);
            """,
            test_id,
            test_title,
            "Content for transaction commit test.",
            "draft",
        )

    # Verify outside transaction using standard pool connection
    row = await db_manager.fetchrow(
        "SELECT id, title, status FROM content_drafts WHERE id = $1;",
        test_id,
    )
    assert row is not None
    assert row["id"] == test_id
    assert row["title"] == test_title

    # Cleanup
    await db_manager.execute("DELETE FROM content_drafts WHERE id = $1;", test_id)


@pytest.mark.asyncio
async def test_transaction_rolls_back_on_exception():
    """Verify that an unhandled exception rolls back all writes within the transaction."""
    test_id = uuid.uuid4()
    test_title = f"Tx Rollback Test {test_id}"

    with pytest.raises(RuntimeError, match="Simulated transaction failure"):
        async with db_manager.transaction() as conn:
            await conn.execute(
                """
                INSERT INTO content_drafts (id, title, content_text, status)
                VALUES ($1, $2, $3, $4);
                """,
                test_id,
                test_title,
                "Content that must be rolled back.",
                "draft",
            )
            raise RuntimeError("Simulated transaction failure")

    # Verify outside transaction: row MUST NOT exist
    row = await db_manager.fetchrow(
        "SELECT id FROM content_drafts WHERE id = $1;",
        test_id,
    )
    assert row is None, "Transaction rollback failed: draft was saved despite exception"


@pytest.mark.asyncio
async def test_transaction_uses_same_connection_throughout():
    """Verify that the transaction context yields a single active connection with stable txid."""
    async with db_manager.transaction() as conn:
        assert isinstance(conn, asyncpg.Connection)
        assert not conn.is_closed()

        # Query the transaction ID multiple times within the block
        txid1 = await conn.fetchval("SELECT txid_current();")
        txid2 = await conn.fetchval("SELECT txid_current();")
        assert txid1 == txid2, "Transaction ID changed within the same transaction context"

        # Verify db_manager methods accept the active connection
        val = await db_manager.fetchrow("SELECT 1 AS num;", conn=conn)
        assert val["num"] == 1


@pytest.mark.asyncio
async def test_transaction_releases_connection_to_pool_on_success_and_error():
    """Verify that connection is released back to the pool in both success and error paths."""
    await db_manager.connect()
    pool = db_manager.pool
    assert pool is not None
    initial_idle = pool.get_idle_size()

    # 1. Normal exit
    async with db_manager.transaction() as conn:
        pass
    # Connection returned to pool
    assert pool.get_idle_size() >= initial_idle

    # 2. Error exit
    try:
        async with db_manager.transaction() as conn:
            raise ValueError("error to check release")
    except ValueError:
        pass
    # Connection returned to pool
    assert pool.get_idle_size() >= initial_idle

    # 3. Connection can be acquired immediately without deadlocks
    async with db_manager.transaction() as conn:
        res = await conn.fetchval("SELECT 42;")
        assert res == 42
