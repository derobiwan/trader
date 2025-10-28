# FastAPI Application - LLM Crypto Trading System

Production-ready FastAPI application for the LLM-powered cryptocurrency trading system.

## Overview

This API provides endpoints for:
- **Trading Signals**: LLM-powered market analysis and trading signals
- **Position Management**: Active position tracking and management
- **Risk Management**: Stop-loss, position sizing, circuit breaker controls
- **Market Data**: Real-time and historical cryptocurrency data
- **System Monitoring**: Health checks, metrics, and performance monitoring

## Architecture

```
workspace/api/
├── main.py              # Application entry point
├── config.py            # Configuration management
├── middleware.py        # Middleware layer
├── routers/             # API endpoints
│   ├── __init__.py     # Router registration
│   └── health.py       # Health check endpoints
└── tests/              # Test suite
    ├── __init__.py
    └── test_api.py     # API tests
```

### Key Components

- **FastAPI Application**: Async web framework with OpenAPI documentation
- **Middleware Stack**: Request logging, error handling, CORS, rate limiting
- **Health Checks**: Liveness, readiness, and metrics endpoints
- **Configuration**: Pydantic-based settings with environment variable support
- **Testing**: Comprehensive test suite with FastAPI TestClient

## Getting Started

### Prerequisites

- Python 3.12+
- PostgreSQL 14+ (for position and market data storage)
- Redis 7+ (for caching and task queues)

### Installation

1. **Install dependencies**:
   ```bash
   cd /Users/tobiprivat/Documents/GitProjects/personal/trader
   pip install fastapi uvicorn[standard] pydantic pydantic-settings python-multipart psutil
   ```

2. **Create environment file**:
   ```bash
   cat > .env << 'EOF'
   # Application
   APP_NAME=trading-system
   ENVIRONMENT=development
   DEBUG=true
   LOG_LEVEL=INFO

   # API
   HOST=0.0.0.0
   PORT=8000

   # Database
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=trading_system
   DB_USER=postgres
   DB_PASSWORD=your_password_here

   # Redis
   REDIS_HOST=localhost
   REDIS_PORT=6379
   REDIS_DB=0

   # Trading
   CAPITAL_CHF=2626.96
   CIRCUIT_BREAKER_CHF=-183.89
   MAX_POSITION_SIZE_PCT=0.1

   # CORS
   CORS_ORIGINS=http://localhost:3000,http://localhost:8000

   # Rate Limiting
   RATE_LIMIT_REQUESTS=100
   RATE_LIMIT_WINDOW_SECONDS=60
   EOF
   ```

3. **Run the server**:
   ```bash
   # Development (auto-reload)
   uvicorn workspace.api.main:app --reload --host 0.0.0.0 --port 8000

   # Or use Python directly
   python -m workspace.api.main
   ```

### Verify Installation

1. **Check health**:
   ```bash
   curl http://localhost:8000/health/
   ```

2. **Access API documentation**:
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

3. **Check metrics**:
   ```bash
   curl http://localhost:8000/health/metrics
   ```

## API Endpoints

### Health & Monitoring

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health/` | GET | Basic health check (always returns 200) |
| `/health/ready` | GET | Readiness check (validates dependencies) |
| `/health/live` | GET | Liveness check (for load balancers) |
| `/health/metrics` | GET | System metrics (CPU, memory, disk) |

### API Documentation

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API information and links |
| `/docs` | GET | Swagger UI (dev only) |
| `/redoc` | GET | ReDoc documentation (dev only) |
| `/openapi.json` | GET | OpenAPI schema (dev only) |

### Future Endpoints (v1)

These will be added as features are implemented:

- `/v1/positions` - Position management
- `/v1/signals` - Trading signals
- `/v1/market-data` - Market data access
- `/v1/trading` - Trade execution
- `/v1/risk` - Risk management

## Configuration

All configuration is managed via environment variables. See `config.py` for full list.

### Critical Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DB_HOST` | Yes | localhost | PostgreSQL host |
| `DB_USER` | Yes | postgres | Database user |
| `DB_PASSWORD` | Yes | - | Database password |
| `REDIS_HOST` | No | localhost | Redis host |
| `CAPITAL_CHF` | No | 2626.96 | Trading capital |
| `CIRCUIT_BREAKER_CHF` | No | -183.89 | Loss limit |

### Environment-Specific Settings

**Development**:
```bash
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG
```

**Production**:
```bash
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
```

## Middleware

The application includes several middleware layers:

### 1. Request Context Middleware
- Adds unique request ID to all requests
- Tracks requests across async operations
- Includes request ID in response headers

### 2. Request Logging Middleware
- Logs all incoming requests
- Logs response status and duration
- Includes request ID for correlation

### 3. Error Handling Middleware
- Catches unhandled exceptions
- Returns structured JSON error responses
- Logs errors with full context

### 4. Rate Limiting Middleware
- In-memory rate limiting per IP
- Configurable limits via environment
- Returns 429 Too Many Requests when exceeded

### 5. CORS Middleware
- Configurable allowed origins
- Supports credentials
- Handles preflight requests

## Development Workflow

### Running Tests

```bash
# Run all tests
pytest workspace/api/tests/

# Run with coverage
pytest workspace/api/tests/ --cov=workspace.api --cov-report=html

# Run specific test file
pytest workspace/api/tests/test_api.py -v

# Run specific test
pytest workspace/api/tests/test_api.py::TestHealthEndpoints::test_basic_health_check -v
```

### Code Quality

```bash
# Type checking
mypy workspace/api/

# Linting
pylint workspace/api/

# Formatting
black workspace/api/
isort workspace/api/
```

### Adding New Endpoints

1. **Create router file**:
   ```python
   # workspace/api/routers/my_feature.py
   from fastapi import APIRouter

   router = APIRouter()

   @router.get("/my-endpoint")
   async def my_endpoint():
       return {"message": "Hello"}
   ```

2. **Register router**:
   ```python
   # workspace/api/routers/__init__.py
   from . import my_feature

   api_v1_router.include_router(
       my_feature.router,
       prefix="/my-feature",
       tags=["my-feature"]
   )
   ```

3. **Add tests**:
   ```python
   # workspace/api/tests/test_my_feature.py
   def test_my_endpoint(client):
       response = client.get("/v1/my-feature/my-endpoint")
       assert response.status_code == 200
   ```

## Deployment

### Production Server

```bash
# Multi-worker production server
uvicorn workspace.api.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --log-level info \
  --no-access-log  # Use middleware logging instead
```

### Docker

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY workspace/ workspace/

CMD ["uvicorn", "workspace.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Variables in Production

**DO NOT** commit secrets to `.env` file. Use:
- **Docker Secrets** (Docker Swarm)
- **Kubernetes Secrets** (Kubernetes)
- **AWS Secrets Manager** (AWS)
- **Azure Key Vault** (Azure)
- **Google Secret Manager** (GCP)

## Monitoring

### Health Checks

**Kubernetes Liveness Probe**:
```yaml
livenessProbe:
  httpGet:
    path: /health/live
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 5
```

**Kubernetes Readiness Probe**:
```yaml
readinessProbe:
  httpGet:
    path: /health/ready
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
```

### Metrics

The `/health/metrics` endpoint provides:
- Server uptime
- CPU usage
- Memory usage (MB and percentage)
- Disk usage percentage

Integrate with monitoring systems:
- **Prometheus**: Scrape metrics endpoint
- **Datadog**: Custom metrics via API
- **Grafana**: Visualize metrics

### Logging

Logs are written to stdout in structured format:
```
2025-10-27 12:00:00 - workspace.api.middleware - INFO - Request started
```

Integrate with logging systems:
- **ELK Stack** (Elasticsearch, Logstash, Kibana)
- **Datadog Logs**
- **CloudWatch Logs** (AWS)
- **Stackdriver Logging** (GCP)

## Troubleshooting

### Common Issues

**1. Connection Refused**
```
Error: Connection refused to localhost:8000
```
Solution: Check server is running with `uvicorn` command.

**2. Database Connection Failed**
```
Error: could not connect to server: Connection refused
```
Solution: Verify PostgreSQL is running and credentials are correct in `.env`.

**3. Rate Limit Exceeded**
```
Error: 429 Too Many Requests
```
Solution: Wait for rate limit window to reset, or increase limit in configuration.

**4. Import Errors**
```
Error: ModuleNotFoundError: No module named 'workspace'
```
Solution: Run from repository root, not from `workspace/api/` directory.

### Debug Mode

Enable debug mode for detailed error messages:
```bash
DEBUG=true
LOG_LEVEL=DEBUG
```

**WARNING**: Never enable debug mode in production!

## Security Considerations

### Current Implementation
- ✅ Rate limiting (basic, in-memory)
- ✅ CORS configuration
- ✅ Input validation (Pydantic)
- ✅ Error messages (sanitized in production)
- ✅ Request ID tracking

### Production Requirements
- ⚠️ Authentication/Authorization (TODO: OAuth2, JWT)
- ⚠️ API Keys (TODO: for external access)
- ⚠️ Request signing (TODO: for critical operations)
- ⚠️ IP whitelisting (TODO: for admin endpoints)
- ⚠️ Rate limiting with Redis (TODO: distributed)
- ⚠️ HTTPS/TLS (required in production)
- ⚠️ Security headers (TODO: helmet middleware)

### Best Practices
1. **Never commit secrets** to version control
2. **Use environment variables** for configuration
3. **Validate all inputs** with Pydantic
4. **Log security events** (authentication failures, rate limits)
5. **Keep dependencies updated** (security patches)
6. **Run with least privilege** (non-root user)

## Performance

### Current Performance Targets
- Health check: < 100ms
- Liveness check: < 50ms
- API endpoints: < 2s (target from PRD)

### Optimization Strategies
1. **Connection pooling**: Database and Redis
2. **Caching**: Redis for frequently accessed data
3. **Async operations**: All I/O operations use async/await
4. **Worker processes**: Multiple uvicorn workers
5. **Load balancing**: Nginx/HAProxy in front of workers

### Benchmarking

```bash
# Install load testing tool
pip install locust

# Create locustfile
cat > locustfile.py << 'EOF'
from locust import HttpUser, task

class APIUser(HttpUser):
    @task
    def health_check(self):
        self.client.get("/health/")
EOF

# Run load test
locust --host=http://localhost:8000
```

## Contributing

### Code Style
- Follow PEP 8
- Use type hints
- Document all functions
- Write tests for new features

### Git Workflow
1. Create feature branch
2. Implement feature
3. Add tests
4. Update documentation
5. Submit pull request

## Support

- **Documentation**: See `/docs` endpoint
- **Issues**: GitHub Issues
- **Email**: support@example.com

## License

Copyright © 2025. All rights reserved.

---

**Built with FastAPI** - High performance, easy to learn, fast to code, ready for production.
