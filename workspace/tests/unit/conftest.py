"""
Shared Test Fixtures for Unit Tests

Provides common fixtures for database mocking, async testing,
and service instantiation across all unit tests.

Author: Validation Engineer Team Fix-Hotel
Date: 2025-10-31
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_db_pool():
    """
    Comprehensive database pool mock for asyncpg.

    Provides properly mocked:
    - Connection pool with acquire context manager
    - Connection with execute/fetch/fetchval methods
    - Transaction context manager
    - All async operations
    """
    pool = AsyncMock()

    # Mock connection
    conn = AsyncMock()
    conn.execute = AsyncMock()
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchval = AsyncMock(return_value=None)
    conn.fetchrow = AsyncMock(return_value=None)
    conn.commit = AsyncMock()
    conn.rollback = AsyncMock()
    conn.close = AsyncMock()

    # Transaction context manager
    transaction = AsyncMock()
    transaction.__aenter__ = AsyncMock(return_value=transaction)
    transaction.__aexit__ = AsyncMock(return_value=None)
    conn.transaction = MagicMock(return_value=transaction)

    # Acquire context manager
    pool.acquire = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

    return pool


@pytest.fixture
def mock_db_session():
    """
    Comprehensive database session mock for SQLAlchemy-style usage.

    Provides properly mocked:
    - Basic CRUD operations (execute, commit, rollback, close)
    - Query operations (scalar, scalars)
    - Transaction context manager
    - Refresh and add operations
    """
    session = AsyncMock()

    # Basic operations
    session.execute = AsyncMock(
        return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=None),
            scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[]))),
        )
    )
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()

    # Query operations
    session.scalar = AsyncMock(return_value=None)
    session.scalars = AsyncMock(return_value=MagicMock(all=MagicMock(return_value=[])))

    # Transaction context manager
    transaction = AsyncMock()
    transaction.__aenter__ = AsyncMock(return_value=transaction)
    transaction.__aexit__ = AsyncMock(return_value=None)
    session.begin = MagicMock(return_value=transaction)

    return session


@pytest.fixture
def patch_database_pool(mock_db_pool):
    """
    Patch DatabasePool.get_connection() globally for tests.

    Use this fixture in tests that need database access without
    manual patching. The patched connection will return the
    mock_db_pool fixture.

    Example:
        def test_with_database(patch_database_pool):
            # DatabasePool.get_connection() will use mock
            service = MyService()
            result = await service.database_operation()
    """
    with patch("workspace.shared.database.connection.DatabasePool") as mock_pool_class:
        mock_pool_class.get_connection.return_value = mock_db_pool.acquire()
        yield mock_pool_class


@pytest.fixture
def patch_database_get_pool(mock_db_pool):
    """
    Patch get_pool() function for reconciliation and other services.

    Some services use get_pool() instead of DatabasePool.get_connection().
    This fixture handles those cases.

    Example:
        def test_reconciliation(patch_database_get_pool):
            service = ReconciliationService(...)
            await service._update_position_quantity(...)
    """
    with patch(
        "workspace.features.trade_executor.reconciliation.get_pool"
    ) as mock_get_pool:
        mock_get_pool.return_value = mock_db_pool
        yield mock_get_pool
