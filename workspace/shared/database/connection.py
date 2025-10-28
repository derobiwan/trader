"""
Database Connection Pool Management

Provides async connection pooling for PostgreSQL using asyncpg.
Handles connection lifecycle, health checks, and graceful shutdown.

Configuration:
- Pool size: 10-50 connections
- Connection timeout: 10 seconds
- Health check interval: 60 seconds

Usage:
    from workspace.shared.database.connection import DatabasePool

    # Initialize pool
    pool = DatabasePool(
        host="localhost",
        port=5432,
        database="trading_system",
        user="trading_app",
        password="secure_password"
    )
    await pool.initialize()

    # Execute query
    async with pool.acquire() as conn:
        result = await conn.fetch("SELECT * FROM positions WHERE status = 'OPEN'")

    # Cleanup
    await pool.close()
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional, Dict, Any

import asyncpg
from asyncpg import Pool, Connection

logger = logging.getLogger(__name__)


class DatabasePool:
    """
    Async PostgreSQL connection pool with health monitoring.

    Attributes:
        pool: asyncpg connection pool
        config: Database configuration
        is_initialized: Whether pool is ready for use
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "trading_system",
        user: str = "postgres",
        password: str = "",
        min_size: int = 10,
        max_size: int = 50,
        command_timeout: float = 10.0,
        max_queries: int = 50000,
        max_inactive_connection_lifetime: float = 300.0
    ):
        """
        Initialize database pool configuration.

        Args:
            host: Database host
            port: Database port
            database: Database name
            user: Database user
            password: Database password
            min_size: Minimum pool size
            max_size: Maximum pool size
            command_timeout: Query timeout in seconds
            max_queries: Max queries per connection before recycling
            max_inactive_connection_lifetime: Max idle time before closing
        """
        self.config = {
            "host": host,
            "port": port,
            "database": database,
            "user": user,
            "password": password,
            "min_size": min_size,
            "max_size": max_size,
            "command_timeout": command_timeout,
            "max_queries": max_queries,
            "max_inactive_connection_lifetime": max_inactive_connection_lifetime
        }
        self.pool: Optional[Pool] = None
        self.is_initialized: bool = False
        self._health_check_task: Optional[asyncio.Task] = None

    async def initialize(self) -> None:
        """
        Initialize connection pool and start health monitoring.

        Raises:
            ConnectionError: If unable to connect to database
        """
        if self.is_initialized:
            logger.warning("Database pool already initialized")
            return

        try:
            logger.info(
                f"Initializing database pool: {self.config['database']}@{self.config['host']}:{self.config['port']}"
            )

            # Create connection pool
            self.pool = await asyncpg.create_pool(
                host=self.config["host"],
                port=self.config["port"],
                database=self.config["database"],
                user=self.config["user"],
                password=self.config["password"],
                min_size=self.config["min_size"],
                max_size=self.config["max_size"],
                command_timeout=self.config["command_timeout"],
                max_queries=self.config["max_queries"],
                max_inactive_connection_lifetime=self.config["max_inactive_connection_lifetime"]
            )

            # Verify connection
            async with self.pool.acquire() as conn:
                version = await conn.fetchval("SELECT version()")
                logger.info(f"Connected to PostgreSQL: {version}")

                # Verify TimescaleDB extension
                timescaledb = await conn.fetchval(
                    "SELECT extversion FROM pg_extension WHERE extname = 'timescaledb'"
                )
                if timescaledb:
                    logger.info(f"TimescaleDB extension loaded: {timescaledb}")
                else:
                    logger.warning("TimescaleDB extension not found")

            self.is_initialized = True

            # Start health check task
            self._health_check_task = asyncio.create_task(self._periodic_health_check())

            logger.info(
                f"Database pool initialized: {self.config['min_size']}-{self.config['max_size']} connections"
            )

        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}")
            raise ConnectionError(f"Database connection failed: {e}") from e

    @asynccontextmanager
    async def acquire(self) -> Connection:
        """
        Acquire a connection from the pool.

        Yields:
            asyncpg.Connection: Database connection

        Raises:
            RuntimeError: If pool not initialized

        Example:
            async with pool.acquire() as conn:
                result = await conn.fetch("SELECT * FROM positions")
        """
        if not self.is_initialized or not self.pool:
            raise RuntimeError("Database pool not initialized. Call initialize() first.")

        async with self.pool.acquire() as connection:
            yield connection

    async def execute(self, query: str, *args, timeout: Optional[float] = None) -> str:
        """
        Execute a query that doesn't return results.

        Args:
            query: SQL query
            *args: Query parameters
            timeout: Optional timeout override

        Returns:
            Query status string

        Example:
            status = await pool.execute(
                "INSERT INTO positions (symbol, side, quantity) VALUES ($1, $2, $3)",
                "BTCUSDT", "LONG", 0.1
            )
        """
        async with self.acquire() as conn:
            return await conn.execute(query, *args, timeout=timeout)

    async def fetch(self, query: str, *args, timeout: Optional[float] = None) -> list:
        """
        Fetch all rows from a query.

        Args:
            query: SQL query
            *args: Query parameters
            timeout: Optional timeout override

        Returns:
            List of records

        Example:
            positions = await pool.fetch("SELECT * FROM positions WHERE status = $1", "OPEN")
        """
        async with self.acquire() as conn:
            return await conn.fetch(query, *args, timeout=timeout)

    async def fetchrow(self, query: str, *args, timeout: Optional[float] = None) -> Optional[asyncpg.Record]:
        """
        Fetch a single row from a query.

        Args:
            query: SQL query
            *args: Query parameters
            timeout: Optional timeout override

        Returns:
            Single record or None

        Example:
            position = await pool.fetchrow("SELECT * FROM positions WHERE id = $1", position_id)
        """
        async with self.acquire() as conn:
            return await conn.fetchrow(query, *args, timeout=timeout)

    async def fetchval(self, query: str, *args, column: int = 0, timeout: Optional[float] = None) -> Any:
        """
        Fetch a single value from a query.

        Args:
            query: SQL query
            *args: Query parameters
            column: Column index to return
            timeout: Optional timeout override

        Returns:
            Single value

        Example:
            count = await pool.fetchval("SELECT COUNT(*) FROM positions WHERE status = $1", "OPEN")
        """
        async with self.acquire() as conn:
            return await conn.fetchval(query, *args, column=column, timeout=timeout)

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on database connection.

        Returns:
            Health status dictionary with metrics

        Example:
            health = await pool.health_check()
            if not health["healthy"]:
                logger.error(f"Database unhealthy: {health['error']}")
        """
        if not self.is_initialized or not self.pool:
            return {
                "healthy": False,
                "error": "Pool not initialized",
                "timestamp": datetime.utcnow().isoformat()
            }

        try:
            start_time = asyncio.get_event_loop().time()

            async with self.pool.acquire() as conn:
                # Test basic query
                await conn.fetchval("SELECT 1")

                # Get pool stats
                pool_size = self.pool.get_size()
                pool_free = self.pool.get_idle_size()

            latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000

            return {
                "healthy": True,
                "latency_ms": round(latency_ms, 2),
                "pool_size": pool_size,
                "pool_free": pool_free,
                "pool_used": pool_size - pool_free,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "healthy": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    async def _periodic_health_check(self) -> None:
        """
        Periodic health check task (runs every 60 seconds).
        Logs warnings if database becomes unhealthy.
        """
        while self.is_initialized:
            try:
                await asyncio.sleep(60)
                health = await self.health_check()

                if not health["healthy"]:
                    logger.warning(f"Database health check failed: {health['error']}")
                elif health["latency_ms"] > 100:
                    logger.warning(f"Database latency high: {health['latency_ms']}ms")
                else:
                    logger.debug(f"Database healthy: {health['latency_ms']}ms latency")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check task error: {e}")

    async def close(self) -> None:
        """
        Close connection pool and cleanup resources.

        Should be called on application shutdown.
        """
        if not self.is_initialized:
            return

        logger.info("Closing database pool...")

        # Cancel health check task
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

        # Close pool
        if self.pool:
            await self.pool.close()

        self.is_initialized = False
        logger.info("Database pool closed")

    async def __aenter__(self):
        """Context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.close()


# Singleton instance for convenience
_global_pool: Optional[DatabasePool] = None


async def get_pool() -> DatabasePool:
    """
    Get global database pool instance.

    Returns:
        DatabasePool instance

    Raises:
        RuntimeError: If pool not initialized

    Example:
        pool = await get_pool()
        positions = await pool.fetch("SELECT * FROM positions")
    """
    global _global_pool
    if _global_pool is None or not _global_pool.is_initialized:
        raise RuntimeError(
            "Global database pool not initialized. "
            "Call init_pool() first or use DatabasePool() directly."
        )
    return _global_pool


async def init_pool(
    host: str = "localhost",
    port: int = 5432,
    database: str = "trading_system",
    user: str = "postgres",
    password: str = "",
    **kwargs
) -> DatabasePool:
    """
    Initialize global database pool.

    Args:
        host: Database host
        port: Database port
        database: Database name
        user: Database user
        password: Database password
        **kwargs: Additional pool configuration

    Returns:
        DatabasePool instance

    Example:
        import os
        pool = await init_pool(
            host=os.getenv("DB_HOST", "localhost"),
            database=os.getenv("DB_NAME", "trading_system"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", "")
        )
    """
    global _global_pool

    if _global_pool and _global_pool.is_initialized:
        logger.warning("Global database pool already initialized")
        return _global_pool

    _global_pool = DatabasePool(
        host=host,
        port=port,
        database=database,
        user=user,
        password=password,
        **kwargs
    )
    await _global_pool.initialize()

    return _global_pool


async def close_pool() -> None:
    """
    Close global database pool.

    Should be called on application shutdown.

    Example:
        # On shutdown
        await close_pool()
    """
    global _global_pool
    if _global_pool:
        await _global_pool.close()
        _global_pool = None


# CLI for testing connection
async def test_connection():
    """Test database connection and display info."""
    import os

    print("Testing database connection...")

    pool = DatabasePool(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME", "trading_system"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "")
    )

    try:
        await pool.initialize()

        # Health check
        health = await pool.health_check()
        print(f"\n✓ Database connection successful!")
        print(f"  Latency: {health['latency_ms']}ms")
        print(f"  Pool size: {health['pool_size']}")
        print(f"  Free connections: {health['pool_free']}")

        # Test query
        version = await pool.fetchval("SELECT version()")
        print(f"\n  PostgreSQL version: {version[:50]}...")

        # Check TimescaleDB
        timescaledb = await pool.fetchval(
            "SELECT extversion FROM pg_extension WHERE extname = 'timescaledb'"
        )
        if timescaledb:
            print(f"  TimescaleDB version: {timescaledb}")
        else:
            print("  ⚠ TimescaleDB extension not loaded")

        # Test table count
        table_count = await pool.fetchval(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'"
        )
        print(f"  Tables in database: {table_count}")

        await pool.close()
        print("\n✓ Connection test complete")

    except Exception as e:
        print(f"\n✗ Connection failed: {e}")
        raise


if __name__ == "__main__":
    # Run connection test
    asyncio.run(test_connection())
