# Multi-stage build for production-optimized trading engine

# Stage 1: Builder
FROM python:3.12-slim as builder

# Build arguments
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION

# Labels for metadata
LABEL org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.title="Trading Engine" \
      org.opencontainers.image.description="LLM-Powered Cryptocurrency Trading System"

# Set working directory
WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime
FROM python:3.12-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 -s /bin/bash trader && \
    mkdir -p /app/logs /app/cache && \
    chown -R trader:trader /app

# Set working directory
WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/trader/.local

# Copy application code
COPY --chown=trader:trader workspace/ /app/workspace/
COPY --chown=trader:trader PRD/ /app/PRD/
COPY --chown=trader:trader scripts/ /app/scripts/

# Set Python path
ENV PYTHONPATH=/app \
    PATH=/home/trader/.local/bin:$PATH \
    PYTHONUNBUFFERED=1

# Switch to non-root user
USER trader

# Expose ports
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["python", "-m", "uvicorn", "workspace.features.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
