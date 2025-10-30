"""
Database Connection Pool Unit Tests

Unit tests for PostgreSQL connection pool configuration and interface.
Integration tests with actual database are in /tests/integration/

Author: Validation Engineer
Date: 2025-10-30
"""

import inspect

import pytest

from workspace.shared.database.connection import DatabasePool

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def db_config():
    """Database configuration"""
    return {
        "host": "localhost",
        "port": 5432,
        "database": "trading_system",
        "user": "postgres",
        "password": "test_password",
        "min_size": 10,
        "max_size": 50,
        "command_timeout": 10.0,
    }


# ============================================================================
# Initialization Tests
# ============================================================================


def test_db_pool_initialization(db_config):
    """Test database pool initializes with correct config"""
    pool = DatabasePool(**db_config)

    assert pool.config["host"] == "localhost"
    assert pool.config["port"] == 5432
    assert pool.config["database"] == "trading_system"
    assert pool.config["user"] == "postgres"
    assert pool.config["password"] == "test_password"
    assert pool.config["min_size"] == 10
    assert pool.config["max_size"] == 50
    assert pool.config["command_timeout"] == 10.0
    assert pool.is_initialized is False
    assert pool.pool is None


def test_db_pool_default_config():
    """Test database pool with default configuration"""
    pool = DatabasePool()

    assert pool.config["host"] == "localhost"
    assert pool.config["port"] == 5432
    assert pool.config["database"] == "trading_system"
    assert pool.config["user"] == "postgres"
    assert pool.config["min_size"] == 10
    assert pool.config["max_size"] == 50


def test_db_pool_custom_pool_size():
    """Test database pool with custom pool size"""
    pool = DatabasePool(min_size=5, max_size=100)

    assert pool.config["min_size"] == 5
    assert pool.config["max_size"] == 100


def test_db_pool_custom_command_timeout():
    """Test database pool with custom command timeout"""
    pool = DatabasePool(command_timeout=30.0)

    assert pool.config["command_timeout"] == 30.0


def test_db_pool_custom_max_queries():
    """Test database pool with custom max_queries"""
    pool = DatabasePool(max_queries=100000)

    assert pool.config["max_queries"] == 100000


def test_db_pool_with_password():
    """Test database pool with password"""
    pool = DatabasePool(password="secure_pass")

    assert pool.config["password"] == "secure_pass"


def test_db_pool_without_password():
    """Test database pool without password"""
    pool = DatabasePool(password=None)

    assert pool.config["password"] is None


def test_db_pool_max_inactive_connection_lifetime():
    """Test pool max_inactive_connection_lifetime configuration"""
    pool = DatabasePool(max_inactive_connection_lifetime=600.0)

    assert pool.config["max_inactive_connection_lifetime"] == 600.0


# ============================================================================
# Interface Tests
# ============================================================================


def test_db_pool_has_initialize_method():
    """Test database pool has initialize method"""
    pool = DatabasePool()

    assert hasattr(pool, "initialize")
    assert callable(pool.initialize)


def test_db_pool_has_close_method():
    """Test database pool has close method"""
    pool = DatabasePool()

    assert hasattr(pool, "close")
    assert callable(pool.close)


def test_db_pool_has_acquire_method():
    """Test database pool has acquire method"""
    pool = DatabasePool()

    assert hasattr(pool, "acquire")
    assert callable(pool.acquire)


def test_db_pool_has_execute_method():
    """Test database pool has execute method"""
    pool = DatabasePool()

    assert hasattr(pool, "execute")
    assert callable(pool.execute)


def test_db_pool_has_fetch_method():
    """Test database pool has fetch method"""
    pool = DatabasePool()

    assert hasattr(pool, "fetch")
    assert callable(pool.fetch)


def test_db_pool_has_fetchrow_method():
    """Test database pool has fetchrow method"""
    pool = DatabasePool()

    assert hasattr(pool, "fetchrow")
    assert callable(pool.fetchrow)


def test_db_pool_has_fetchval_method():
    """Test database pool has fetchval method"""
    pool = DatabasePool()

    assert hasattr(pool, "fetchval")
    assert callable(pool.fetchval)


def test_db_pool_has_health_check_method():
    """Test database pool has health_check method"""
    pool = DatabasePool()

    assert hasattr(pool, "health_check")
    assert callable(pool.health_check)


def test_db_pool_has_context_manager_methods():
    """Test database pool has context manager support"""
    pool = DatabasePool()

    assert hasattr(pool, "__aenter__")
    assert hasattr(pool, "__aexit__")


# ============================================================================
# Method Signature Tests
# ============================================================================


def test_db_pool_execute_signature():
    """Test execute method has correct signature"""
    pool = DatabasePool()

    sig = inspect.signature(pool.execute)
    assert "query" in sig.parameters
    assert "timeout" in sig.parameters


def test_db_pool_fetch_signature():
    """Test fetch method has correct signature"""
    pool = DatabasePool()

    sig = inspect.signature(pool.fetch)
    assert "query" in sig.parameters
    assert "timeout" in sig.parameters


def test_db_pool_fetchrow_signature():
    """Test fetchrow method has correct signature"""
    pool = DatabasePool()

    sig = inspect.signature(pool.fetchrow)
    assert "query" in sig.parameters
    assert "timeout" in sig.parameters


def test_db_pool_fetchval_signature():
    """Test fetchval method has correct signature"""
    pool = DatabasePool()

    sig = inspect.signature(pool.fetchval)
    assert "query" in sig.parameters
    assert "column" in sig.parameters
    assert "timeout" in sig.parameters


# ============================================================================
# State Management Tests
# ============================================================================


def test_db_pool_initial_state():
    """Test database pool initial state"""
    pool = DatabasePool()

    assert pool.is_initialized is False
    assert pool.pool is None
    assert hasattr(pool, "_health_check_task")


def test_db_pool_has_config_attribute():
    """Test database pool has config dictionary"""
    pool = DatabasePool(host="custom_host", port=9999)

    assert isinstance(pool.config, dict)
    assert pool.config["host"] == "custom_host"
    assert pool.config["port"] == 9999


# ============================================================================
# Error Handling Tests
# ============================================================================


@pytest.mark.asyncio
async def test_db_pool_acquire_without_initialization():
    """Test acquiring connection without initialization fails"""
    pool = DatabasePool()

    with pytest.raises(RuntimeError, match="Database pool not initialized"):
        async with pool.acquire():
            pass


@pytest.mark.asyncio
async def test_db_pool_execute_without_initialization():
    """Test execute without initialization fails"""
    pool = DatabasePool()

    with pytest.raises(RuntimeError, match="Database pool not initialized"):
        await pool.execute("SELECT 1")


@pytest.mark.asyncio
async def test_db_pool_fetch_without_initialization():
    """Test fetch without initialization fails"""
    pool = DatabasePool()

    with pytest.raises(RuntimeError, match="Database pool not initialized"):
        await pool.fetch("SELECT 1")


@pytest.mark.asyncio
async def test_db_pool_fetchrow_without_initialization():
    """Test fetchrow without initialization fails"""
    pool = DatabasePool()

    with pytest.raises(RuntimeError, match="Database pool not initialized"):
        await pool.fetchrow("SELECT 1")


@pytest.mark.asyncio
async def test_db_pool_fetchval_without_initialization():
    """Test fetchval without initialization fails"""
    pool = DatabasePool()

    with pytest.raises(RuntimeError, match="Database pool not initialized"):
        await pool.fetchval("SELECT 1")


# ============================================================================
# Close Behavior Tests
# ============================================================================


@pytest.mark.asyncio
async def test_db_pool_close_without_initialize():
    """Test closing pool that was never initialized"""
    pool = DatabasePool()

    # Should not raise error
    await pool.close()
    assert pool.is_initialized is False


# ============================================================================
# Health Check Tests
# ============================================================================


@pytest.mark.asyncio
async def test_db_pool_health_check_without_initialization():
    """Test health check without initialization"""
    pool = DatabasePool()

    health = await pool.health_check()

    assert health["healthy"] is False
    assert "error" in health
    assert "timestamp" in health


# ============================================================================
# Global Manager Interface Tests
# ============================================================================


def test_global_pool_functions_exist():
    """Test global pool manager functions exist"""
    from workspace.shared.database.connection import (
        close_pool,
        get_pool,
        init_pool,
    )

    assert callable(init_pool)
    assert callable(get_pool)
    assert callable(close_pool)


# ============================================================================
# Configuration Immutability Tests
# ============================================================================


def test_db_pool_config_is_stored():
    """Test that pool configuration is properly stored"""
    custom_config = {
        "host": "my_host",
        "port": 7777,
        "database": "my_db",
        "user": "my_user",
        "password": "my_pass",
    }

    pool = DatabasePool(**custom_config)

    for key, value in custom_config.items():
        assert pool.config[key] == value


# ============================================================================
# Async Method Tests
# ============================================================================


def test_db_pool_methods_are_async():
    """Test that pool methods are async"""
    pool = DatabasePool()

    import inspect

    assert inspect.iscoroutinefunction(pool.initialize)
    assert inspect.iscoroutinefunction(pool.close)
    assert inspect.iscoroutinefunction(pool.health_check)
    assert inspect.iscoroutinefunction(pool.execute)
    assert inspect.iscoroutinefunction(pool.fetch)
    assert inspect.iscoroutinefunction(pool.fetchrow)
    assert inspect.iscoroutinefunction(pool.fetchval)
