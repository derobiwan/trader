"""
Configuration Management for LLM Crypto Trading System

This module handles all application configuration using Pydantic Settings.
Configuration is loaded from environment variables with sensible defaults.

Environment Variables:
    - APP_NAME: Application name (default: trading-system)
    - ENVIRONMENT: dev/staging/production (default: development)
    - DEBUG: Enable debug mode (default: true)
    - HOST: API host (default: 0.0.0.0)
    - PORT: API port (default: 8000)
    - DB_HOST: PostgreSQL host
    - DB_PORT: PostgreSQL port (default: 5432)
    - DB_NAME: Database name (default: trading_system)
    - DB_USER: Database user
    - DB_PASSWORD: Database password
    - REDIS_HOST: Redis host (default: localhost)
    - REDIS_PORT: Redis port (default: 6379)
    - CAPITAL_CHF: Initial capital in CHF (default: 2626.96)
    - CIRCUIT_BREAKER_CHF: Circuit breaker loss limit (default: -183.89)
    - LOG_LEVEL: Logging level (default: INFO)
    - CORS_ORIGINS: Allowed CORS origins (comma-separated)
"""

from decimal import Decimal
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application Settings

    All settings are loaded from environment variables with fallback defaults.
    Secrets should NEVER be committed to code - use .env file or environment.
    """

    # ==================== Application Settings ====================
    app_name: str = Field(
        default="trading-system",
        description="Application name for logging and identification",
    )

    environment: str = Field(
        default="development",
        description="Environment: development, staging, production",
    )

    debug: bool = Field(
        default=True, description="Enable debug mode with verbose logging"
    )

    log_level: str = Field(
        default="INFO",
        description="Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL",
    )

    # ==================== API Settings ====================
    host: str = Field(default="0.0.0.0", description="API host address")

    port: int = Field(default=8000, ge=1024, le=65535, description="API port number")

    api_version: str = Field(default="v1", description="API version prefix")

    # ==================== Database Settings ====================
    db_host: str = Field(default="localhost", description="PostgreSQL host address")

    db_port: int = Field(default=5432, ge=1, le=65535, description="PostgreSQL port")

    db_name: str = Field(
        default="trading_system", description="PostgreSQL database name"
    )

    db_user: str = Field(default="postgres", description="PostgreSQL username")

    db_password: str = Field(default="", description="PostgreSQL password")

    db_pool_size: int = Field(
        default=10, ge=1, le=100, description="Database connection pool size"
    )

    db_max_overflow: int = Field(
        default=20, ge=0, le=100, description="Database connection pool overflow"
    )

    # ==================== Redis Settings ====================
    redis_host: str = Field(default="localhost", description="Redis host address")

    redis_port: int = Field(default=6379, ge=1, le=65535, description="Redis port")

    redis_db: int = Field(default=0, ge=0, le=15, description="Redis database number")

    redis_password: Optional[str] = Field(
        default=None, description="Redis password (if required)"
    )

    # ==================== Trading Settings ====================
    capital_chf: Decimal = Field(
        default=Decimal("2626.96"), description="Initial trading capital in CHF"
    )

    circuit_breaker_chf: Decimal = Field(
        default=Decimal("-183.89"),
        description="Circuit breaker loss limit in CHF (negative value)",
    )

    max_position_size_pct: Decimal = Field(
        default=Decimal("0.1"),
        ge=Decimal("0.01"),
        le=Decimal("1.0"),
        description="Maximum position size as percentage of capital",
    )

    # ==================== CORS Settings ====================
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="Allowed CORS origins",
    )

    cors_allow_credentials: bool = Field(
        default=True, description="Allow credentials in CORS requests"
    )

    cors_allow_methods: List[str] = Field(
        default=["*"], description="Allowed HTTP methods for CORS"
    )

    cors_allow_headers: List[str] = Field(
        default=["*"], description="Allowed headers for CORS"
    )

    # ==================== Rate Limiting ====================
    rate_limit_requests: int = Field(
        default=100, ge=1, description="Maximum requests per window"
    )

    rate_limit_window_seconds: int = Field(
        default=60, ge=1, description="Rate limit window in seconds"
    )

    # ==================== Monitoring ====================
    enable_metrics: bool = Field(default=True, description="Enable metrics collection")

    enable_request_logging: bool = Field(
        default=True, description="Enable request/response logging"
    )

    # ==================== Pydantic Config ====================
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # ==================== Validators ====================
    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment is one of allowed values."""
        allowed = ["development", "staging", "production"]
        if v.lower() not in allowed:
            raise ValueError(f"Environment must be one of: {allowed}")
        return v.lower()

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is one of allowed values."""
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in allowed:
            raise ValueError(f"Log level must be one of: {allowed}")
        return v_upper

    @field_validator("circuit_breaker_chf")
    @classmethod
    def validate_circuit_breaker(cls, v: Decimal) -> Decimal:
        """Ensure circuit breaker is negative (loss limit)."""
        if v > 0:
            raise ValueError("Circuit breaker must be negative (loss limit)")
        return v

    @field_validator("capital_chf")
    @classmethod
    def validate_capital(cls, v: Decimal) -> Decimal:
        """Ensure capital is positive."""
        if v <= 0:
            raise ValueError("Capital must be positive")
        return v

    # ==================== Computed Properties ====================
    @property
    def database_url(self) -> str:
        """Generate PostgreSQL connection URL."""
        return (
            f"postgresql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def redis_url(self) -> str:
        """Generate Redis connection URL."""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment == "development"

    def get_cors_config(self) -> dict:
        """Get CORS middleware configuration."""
        return {
            "allow_origins": self.cors_origins,
            "allow_credentials": self.cors_allow_credentials,
            "allow_methods": self.cors_allow_methods,
            "allow_headers": self.cors_allow_headers,
        }


# Global settings instance
# This is instantiated once at module load time
settings = Settings()


def get_settings() -> Settings:
    """
    Dependency injection helper for FastAPI.

    Usage in endpoints:
        @app.get("/config")
        async def get_config(settings: Settings = Depends(get_settings)):
            return {"environment": settings.environment}
    """
    return settings
