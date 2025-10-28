# Sprint 1 - Stream A: Quick Wins & Monitoring

**Agent**: Quick Wins Specialist
**Duration**: 2-3 days
**Total Effort**: 7 hours
**Branch**: `sprint-1/stream-a-quick-wins`

---

## 🎯 Stream Objectives

Implement three high-priority quick wins:
1. Real-time balance fetching from exchange
2. Prometheus HTTP /metrics endpoint
3. Health check endpoints (/health, /ready, /live)

**Why These Tasks**: Unblock production deployment and enable monitoring

---

## 📋 Task Breakdown

### TASK-018: Real-time Balance Fetching (2 hours)

**Current State**: Hardcoded balance in trading_engine.py
```python
# Line 430 in workspace/features/trading_loop/trading_engine.py
account_balance_chf = Decimal("2626.96")  # TODO: Fetch real-time
chf_to_usd_rate = Decimal("1.10")
```

**Implementation Steps**:

1. **Add balance fetching to TradeExecutor** (30 min)
   - File: `workspace/features/trade_executor/executor_service.py`
   - Add method:
```python
async def get_account_balance(self) -> Decimal:
    """
    Fetch account balance from exchange

    Returns:
        Balance in CHF (or base currency)
    """
    try:
        balance = await self.exchange.fetch_balance()

        # Get total balance in USDT
        usdt_balance = Decimal(str(balance['USDT']['total']))

        # Convert to CHF (approximate, use real rate in production)
        # TODO: Fetch real CHF/USDT rate
        chf_balance = usdt_balance / Decimal("1.10")

        logger.info(f"Account balance: {chf_balance:.2f} CHF (~{usdt_balance:.2f} USDT)")

        return chf_balance

    except Exception as e:
        logger.error(f"Error fetching balance: {e}", exc_info=True)
        raise
```

2. **Update TradingEngine to use real balance** (30 min)
   - File: `workspace/features/trading_loop/trading_engine.py`
   - Update `_execute_signal()` method:
```python
# Replace hardcoded values
account_balance_chf = await self.trade_executor.get_account_balance()
# TODO: Fetch real CHF/USD rate from exchange
chf_to_usd_rate = Decimal("1.10")  # Use forex API in production
```

3. **Add caching for balance** (30 min)
   - Cache balance for 60 seconds to avoid API spam
   - File: `workspace/features/trade_executor/executor_service.py`
```python
self._balance_cache = None
self._balance_cache_time = 0

async def get_account_balance(self, cache_ttl_seconds: int = 60) -> Decimal:
    """Fetch with caching"""
    import time

    # Check cache
    if (self._balance_cache and
        time.time() - self._balance_cache_time < cache_ttl_seconds):
        return self._balance_cache

    # Fetch fresh balance
    balance = await self._fetch_balance_from_exchange()

    # Update cache
    self._balance_cache = balance
    self._balance_cache_time = time.time()

    return balance
```

4. **Write tests** (30 min)
   - File: `workspace/tests/unit/test_balance_fetching.py`
   - Test cases:
     - Balance fetching succeeds
     - Balance caching works
     - Balance fetch failure handling
     - Exchange response parsing

**Validation**:
```bash
# Run tests
pytest workspace/tests/unit/test_balance_fetching.py -v

# Test with real exchange (testnet)
python -c "
import asyncio
from workspace.features.trade_executor import TradeExecutor

async def test():
    executor = TradeExecutor(
        api_key='YOUR_TESTNET_KEY',
        api_secret='YOUR_TESTNET_SECRET',
        testnet=True
    )
    await executor.initialize()
    balance = await executor.get_account_balance()
    print(f'Balance: {balance} CHF')

asyncio.run(test())
"
```

---

### TASK-031: Prometheus HTTP Endpoint (3 hours)

**Current State**: MetricsService exports data, but no HTTP endpoint

**Implementation Steps**:

1. **Create FastAPI monitoring app** (1 hour)
   - File: `workspace/features/monitoring/metrics/metrics_api.py` (NEW)
```python
"""
Prometheus Metrics HTTP Endpoint

Exposes /metrics endpoint for Prometheus scraping.
"""

from fastapi import FastAPI, Response
from workspace.features.monitoring.metrics import MetricsService

# Global metrics service (shared across requests)
_metrics_service: MetricsService = None

app = FastAPI(title="Trading System Metrics API")


def init_metrics_service(metrics_service: MetricsService):
    """Initialize the global metrics service"""
    global _metrics_service
    _metrics_service = metrics_service


@app.get("/metrics")
async def prometheus_metrics():
    """
    Prometheus metrics endpoint

    Returns metrics in Prometheus text format
    """
    if _metrics_service is None:
        return Response(
            content="# Metrics service not initialized\n",
            media_type="text/plain"
        )

    # Get metrics in Prometheus format
    prometheus_text = _metrics_service.get_prometheus_text()

    return Response(
        content=prometheus_text,
        media_type="text/plain; version=0.0.4; charset=utf-8"
    )


@app.get("/health")
async def health_check():
    """Basic health check"""
    return {"status": "healthy"}
```

2. **Add metrics server to TradingEngine** (1 hour)
   - File: `workspace/features/trading_loop/trading_engine.py`
   - Add server initialization:
```python
import uvicorn
from workspace.features.monitoring.metrics.metrics_api import app, init_metrics_service

class TradingEngine:
    def __init__(self, ...):
        # ... existing code ...

        # Metrics server
        self.metrics_server_port = 8000
        self.metrics_server_task = None

    async def start(self):
        """Start trading engine and metrics server"""
        # Initialize metrics API with our metrics service
        init_metrics_service(self.trade_executor.metrics_service)

        # Start metrics server in background
        config = uvicorn.Config(
            app,
            host="0.0.0.0",
            port=self.metrics_server_port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        self.metrics_server_task = asyncio.create_task(server.serve())

        logger.info(f"Metrics server started on port {self.metrics_server_port}")

        # Start trading loop
        await self.run()

    async def stop(self):
        """Stop trading engine and metrics server"""
        if self.metrics_server_task:
            self.metrics_server_task.cancel()
```

3. **Test endpoint manually** (30 min)
```bash
# Start trading engine (with metrics server)
python -m workspace.features.trading_loop.trading_engine

# In another terminal, test endpoint
curl http://localhost:8000/metrics

# Should see output like:
# trading_trades_total 42
# trading_trades_successful 38
# trading_trades_failed 4
# ...
```

4. **Write integration tests** (30 min)
   - File: `workspace/tests/integration/test_metrics_endpoint.py`
```python
import pytest
import httpx
from workspace.features.monitoring.metrics import MetricsService
from workspace.features.monitoring.metrics.metrics_api import app, init_metrics_service


@pytest.mark.asyncio
async def test_metrics_endpoint_returns_prometheus_format():
    """Test /metrics endpoint returns Prometheus format"""
    # Initialize with test metrics
    metrics = MetricsService()
    metrics.record_trade(success=True, fees=Decimal("5.0"))
    init_metrics_service(metrics)

    # Test endpoint
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/metrics")

    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert "trading_trades_total" in response.text
```

**Validation**:
```bash
# Test endpoint
pytest workspace/tests/integration/test_metrics_endpoint.py -v

# Check Prometheus can scrape
curl http://localhost:8000/metrics | grep trading_
```

---

### TASK-043: Health Check Endpoints (2 hours)

**Current State**: No health checks

**Implementation Steps**:

1. **Add health check endpoints to metrics API** (1 hour)
   - File: `workspace/features/monitoring/metrics/metrics_api.py`
   - Add endpoints:
```python
from datetime import datetime
from typing import Dict, Any

@app.get("/health")
async def health_check():
    """
    Basic health check

    Returns 200 if service is alive
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/ready")
async def readiness_check():
    """
    Readiness check for orchestration

    Returns 200 if service is ready to accept traffic
    """
    if _metrics_service is None:
        return Response(
            content='{"status": "not ready", "reason": "metrics not initialized"}',
            status_code=503,
            media_type="application/json"
        )

    # Check if we have recent metrics
    stats = _metrics_service.get_stats()
    uptime = stats.get("uptime_seconds", 0)

    if uptime < 10:
        # Not ready yet, system just started
        return Response(
            content='{"status": "not ready", "reason": "system initializing"}',
            status_code=503,
            media_type="application/json"
        )

    return {
        "status": "ready",
        "uptime_seconds": uptime,
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/live")
async def liveness_check():
    """
    Liveness check for orchestration

    Returns 200 if service should not be restarted
    """
    if _metrics_service is None:
        # No metrics service = dead
        return Response(
            content='{"status": "dead", "reason": "metrics not initialized"}',
            status_code=503,
            media_type="application/json"
        )

    # Check if system is frozen (no trades in last 10 minutes)
    stats = _metrics_service.get_stats()
    last_trade = _metrics_service.metrics.last_trade_timestamp

    if last_trade:
        time_since_trade = (datetime.utcnow() - last_trade).total_seconds()
        if time_since_trade > 600:  # 10 minutes
            # System might be frozen
            return Response(
                content=f'{{"status": "unhealthy", "reason": "no trades for {time_since_trade:.0f}s"}}',
                status_code=503,
                media_type="application/json"
            )

    return {
        "status": "alive",
        "last_trade_seconds_ago": (
            (datetime.utcnow() - last_trade).total_seconds()
            if last_trade else None
        ),
        "timestamp": datetime.utcnow().isoformat(),
    }
```

2. **Test health endpoints** (30 min)
```python
# File: workspace/tests/integration/test_health_endpoints.py

@pytest.mark.asyncio
async def test_health_endpoint():
    """Test /health always returns 200"""
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_ready_endpoint_not_ready_initially():
    """Test /ready returns 503 when not initialized"""
    # Don't initialize metrics
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/ready")

    assert response.status_code == 503


@pytest.mark.asyncio
async def test_ready_endpoint_ready_after_init():
    """Test /ready returns 200 when initialized"""
    metrics = MetricsService()
    init_metrics_service(metrics)

    # Wait for uptime
    await asyncio.sleep(11)

    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/ready")

    assert response.status_code == 200
```

3. **Document health checks** (30 min)
   - File: `workspace/features/monitoring/README.md`
   - Document each endpoint:
```markdown
# Health Check Endpoints

## /health
**Purpose**: Basic aliveness check
**Use**: Load balancer health check
**Returns**: Always 200 if process is running

## /ready
**Purpose**: Readiness for traffic
**Use**: Kubernetes readiness probe
**Returns**:
- 200 if ready to accept traffic
- 503 if initializing or not ready

## /live
**Purpose**: Liveness check
**Use**: Kubernetes liveness probe (restart if failing)
**Returns**:
- 200 if system is functioning
- 503 if frozen or dead (should restart)
```

**Validation**:
```bash
# Test all health endpoints
curl http://localhost:8000/health
curl http://localhost:8000/ready
curl http://localhost:8000/live

# Run tests
pytest workspace/tests/integration/test_health_endpoints.py -v
```

---

## ✅ Definition of Done

- [ ] Real-time balance fetching works with testnet
- [ ] Balance is cached for 60 seconds
- [ ] Balance fetch failure is handled gracefully
- [ ] Prometheus /metrics endpoint returns valid data
- [ ] Prometheus endpoint includes all 60+ metrics
- [ ] Health endpoints (/health, /ready, /live) work
- [ ] Health checks have appropriate logic
- [ ] All unit tests passing (>90% coverage)
- [ ] Integration tests passing
- [ ] Documentation updated

---

## 🧪 Testing Checklist

```bash
# Unit tests
pytest workspace/tests/unit/test_balance_fetching.py -v

# Integration tests
pytest workspace/tests/integration/test_metrics_endpoint.py -v
pytest workspace/tests/integration/test_health_endpoints.py -v

# Manual validation
curl http://localhost:8000/metrics
curl http://localhost:8000/health
curl http://localhost:8000/ready
curl http://localhost:8000/live

# Verify balance fetching
python scripts/test_balance_fetch.py
```

---

## 📝 Commit Strategy

**Commit 1**: Real-time balance fetching
```
feat(executor): add real-time balance fetching from exchange

- Add get_account_balance() method to TradeExecutor
- Implement 60-second caching to reduce API calls
- Update TradingEngine to use real balance
- Add unit tests for balance fetching
```

**Commit 2**: Prometheus endpoint
```
feat(monitoring): add Prometheus HTTP /metrics endpoint

- Create FastAPI app for metrics serving
- Integrate metrics server into TradingEngine
- Expose all 60+ metrics in Prometheus format
- Add integration tests for metrics endpoint
```

**Commit 3**: Health check endpoints
```
feat(monitoring): add health check endpoints

- Add /health for basic aliveness check
- Add /ready for readiness probe (K8s)
- Add /live for liveness probe (K8s)
- Include logic to detect frozen system
- Add tests for all endpoints
```

---

## 🚀 Getting Started

1. **Setup**:
```bash
git checkout -b sprint-1/stream-a-quick-wins
cd /Users/tobiprivat/Documents/GitProjects/personal/trader
```

2. **Install dependencies** (if needed):
```bash
pip install fastapi uvicorn httpx
```

3. **Run existing tests** (baseline):
```bash
pytest workspace/tests/ -v
```

4. **Start implementation** - follow task order above

5. **Test continuously**:
```bash
# After each task
pytest workspace/tests/ -v
```

6. **Create PR when done**
