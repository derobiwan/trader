"""
Database Migration Runner

Simple migration tool for applying SQL schema changes.
Tracks applied migrations and prevents re-running.

Author: Infrastructure Specialist
Date: 2025-10-28

Usage:
    # Run all pending migrations
    python migration_runner.py

    # Run with custom database
    python migration_runner.py --database trading_system_prod

    # Dry run (show what would be executed)
    python migration_runner.py --dry-run
"""

import argparse
import asyncio
import logging
import os
from pathlib import Path
from typing import List, Tuple

import asyncpg

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class MigrationRunner:
    """
    Database migration runner

    Executes SQL migrations in order and tracks applied versions.
    """

    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        user: str,
        password: str,
    ):
        """
        Initialize migration runner

        Args:
            host: Database host
            port: Database port
            database: Database name
            user: Database user
            password: Database password
        """
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password

        self.migrations_dir = Path(__file__).parent

    async def ensure_migrations_table(self, conn: asyncpg.Connection) -> None:
        """
        Ensure schema_migrations table exists

        Args:
            conn: Database connection
        """
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                description TEXT
            )
        """
        )
        logger.info("Ensured schema_migrations table exists")

    async def get_applied_versions(self, conn: asyncpg.Connection) -> List[int]:
        """
        Get list of applied migration versions

        Args:
            conn: Database connection

        Returns:
            List of applied version numbers
        """
        rows = await conn.fetch(
            "SELECT version FROM schema_migrations ORDER BY version"
        )
        versions = [row["version"] for row in rows]
        logger.debug(f"Applied versions: {versions}")
        return versions

    def get_migration_files(self) -> List[Tuple[int, Path, str]]:
        """
        Get all migration files in order

        Returns:
            List of (version, filepath, description) tuples
        """
        migration_files = []

        for file_path in sorted(self.migrations_dir.glob("*.sql")):
            filename = file_path.name

            # Parse version from filename (e.g., "001_initial_schema.sql")
            try:
                version_str = filename.split("_")[0]
                version = int(version_str)
                description = filename[len(version_str) + 1 : -4].replace("_", " ")
                migration_files.append((version, file_path, description))
            except (ValueError, IndexError):
                logger.warning(f"Skipping invalid migration filename: {filename}")
                continue

        return migration_files

    async def apply_migration(
        self,
        conn: asyncpg.Connection,
        version: int,
        file_path: Path,
        description: str,
        dry_run: bool = False,
    ) -> bool:
        """
        Apply a single migration

        Args:
            conn: Database connection
            version: Migration version
            file_path: Path to SQL file
            description: Migration description
            dry_run: If True, don't execute (just log)

        Returns:
            True if successful
        """
        logger.info(f"Applying migration {version}: {description}")

        # Read SQL file
        sql = file_path.read_text()

        if dry_run:
            logger.info(f"[DRY RUN] Would execute {len(sql)} characters of SQL")
            logger.debug(f"SQL preview:\n{sql[:500]}...")
            return True

        try:
            # Execute migration in a transaction
            async with conn.transaction():
                # Execute the SQL
                await conn.execute(sql)

                # Record migration
                await conn.execute(
                    """
                    INSERT INTO schema_migrations (version, description)
                    VALUES ($1, $2)
                    ON CONFLICT (version) DO NOTHING
                    """,
                    version,
                    description,
                )

            logger.info(f"✓ Migration {version} applied successfully")
            return True

        except Exception as e:
            logger.error(f"✗ Migration {version} failed: {e}", exc_info=True)
            raise

    async def run_migrations(self, dry_run: bool = False) -> Tuple[int, int]:
        """
        Run all pending migrations

        Args:
            dry_run: If True, don't execute (just log)

        Returns:
            Tuple of (applied_count, total_count)
        """
        logger.info("=" * 70)
        logger.info("Database Migration Runner")
        logger.info(f"Database: {self.database}@{self.host}:{self.port}")
        logger.info(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
        logger.info("=" * 70)

        # Connect to database
        try:
            conn = await asyncpg.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
            )
            logger.info("✓ Connected to database")
        except Exception as e:
            logger.error(f"✗ Failed to connect to database: {e}")
            raise

        try:
            # Ensure migrations table exists
            await self.ensure_migrations_table(conn)

            # Get applied versions
            applied_versions = await self.get_applied_versions(conn)
            logger.info(f"Found {len(applied_versions)} applied migrations")

            # Get migration files
            migration_files = self.get_migration_files()
            logger.info(f"Found {len(migration_files)} migration files")

            # Find pending migrations
            pending_migrations = [
                (version, path, desc)
                for version, path, desc in migration_files
                if version not in applied_versions
            ]

            if not pending_migrations:
                logger.info("✓ No pending migrations - database is up to date")
                return 0, len(migration_files)

            logger.info(f"Found {len(pending_migrations)} pending migrations")
            logger.info("-" * 70)

            # Apply pending migrations
            applied_count = 0
            for version, file_path, description in pending_migrations:
                try:
                    await self.apply_migration(
                        conn, version, file_path, description, dry_run
                    )
                    applied_count += 1
                except Exception as e:
                    logger.error(f"Migration {version} failed, stopping: {e}")
                    break

            logger.info("-" * 70)

            if dry_run:
                logger.info(f"[DRY RUN] Would apply {applied_count} migrations")
            else:
                logger.info(
                    f"✓ Applied {applied_count}/{len(pending_migrations)} migrations successfully"
                )

            return applied_count, len(migration_files)

        finally:
            await conn.close()
            logger.info("✓ Database connection closed")


async def main():
    """Run migrations from command line"""
    # Check if DATABASE_URL is provided (standard format)
    database_url = os.getenv("DATABASE_URL")
    dry_run = False

    if database_url:
        # Parse DATABASE_URL (format: postgresql://user:password@host:port/database)
        from urllib.parse import urlparse

        parsed = urlparse(database_url)

        host = parsed.hostname or "localhost"
        port = parsed.port or 5432
        database = parsed.path.lstrip("/") if parsed.path else "trading_system"
        user = parsed.username or "trading_user"
        password = parsed.password or ""

        logger.info(f"Using DATABASE_URL: {user}@{host}:{port}/{database}")
    else:
        # Fall back to individual environment variables
        parser = argparse.ArgumentParser(description="Run database migrations")
        parser.add_argument(
            "--host",
            default=os.getenv("DB_HOST", "localhost"),
            help="Database host",
        )
        parser.add_argument(
            "--port",
            type=int,
            default=int(os.getenv("DB_PORT", "5432")),
            help="Database port",
        )
        parser.add_argument(
            "--database",
            default=os.getenv("DB_NAME", "trading_system"),
            help="Database name",
        )
        parser.add_argument(
            "--user",
            default=os.getenv("DB_USER", "trading_user"),
            help="Database user",
        )
        parser.add_argument(
            "--password",
            default=os.getenv("DB_PASSWORD", ""),
            help="Database password",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be executed without applying",
        )

        args = parser.parse_args()

        host = args.host
        port = args.port
        database = args.database
        user = args.user
        password = args.password
        dry_run = args.dry_run

    runner = MigrationRunner(
        host=host,
        port=port,
        database=database,
        user=user,
        password=password,
    )

    try:
        applied, total = await runner.run_migrations(dry_run=dry_run)

        if dry_run:
            logger.info("Dry run complete - no changes made")
        else:
            logger.info(f"Migration complete: {applied} applied, {total} total")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())
