# 7-Day Paper Trading Setup Guide

**Complete guide to setting up and running the 7-day paper trading validation test**

---

## Table of Contents
1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Quick Start](#quick-start)
4. [Detailed Setup](#detailed-setup)
5. [Monitoring & Metrics](#monitoring--metrics)
6. [Troubleshooting](#troubleshooting)
7. [Performance Analysis](#performance-analysis)

---

## Overview

The 7-day paper trading test validates system performance and LLM decision quality in real market conditions **without risking real capital**. The system will:

- Execute trades at configurable intervals (default: 3 minutes = 480 cycles/day)
  - Configurable via `TRADING_CYCLE_INTERVAL_SECONDS` environment variable
  - For testing: 60 seconds (1440 cycles/day for faster validation)
- Use simulated balance of CHF 2,627.00
- Track P&L, win rate, Sharpe ratio, and other metrics
- Monitor system health and performance
- Generate daily performance reports

**Timeline**: 7 consecutive days (168 hours)
**Expected Trades**: ~3,360 trading decisions
**Goal**: 99.5%+ uptime, stable performance

---

## Prerequisites

### 1. System Requirements
- **OS**: macOS (M1/M2/M3) or Linux
- **RAM**: 8GB minimum (16GB recommended)
- **Disk**: 20GB free space
- **Docker**: Docker Desktop 4.x+ or Docker Engine 20.x+
- **Network**: Stable internet connection

### 2. API Access Required
```bash
# Binance Testnet (for market data)
✓ API Key from https://testnet.binancefuture.com/
✓ API Secret
✓ Testnet funds (request from faucet)

# OpenRouter (for LLM decisions)
✓ API Key from https://openrouter.ai/
✓ Credits: ~$10-20 for 7 days
```

### 3. Pre-Deployment Checklist
- [ ] Testnet Phase 2-3 tests passed ✅ (already complete)
- [ ] Docker infrastructure tested ✅ (already complete)
- [ ] API keys obtained and verified
- [ ] Monitoring tools accessible (Grafana/Prometheus)
- [ ] Alert channels configured (Slack/Email optional)

---

## Quick Start

### Option 1: Automated Setup (Recommended for Mac)

```bash
# Navigate to docker directory
cd /Users/tobiprivat/Documents/GitProjects/personal/trader/deployment/docker

# Copy environment template
cp .env.example .env

# Edit .env with your API keys (see below)
nano .env  # or use your preferred editor

# Run the quick start script
chmod +x quick-start-mac.sh
./quick-start-mac.sh

# The script will:
# - Validate configuration
# - Build Docker images
# - Start all services
# - Run health checks
# - Display monitoring URLs
```

### Option 2: Manual Setup

```bash
# 1. Navigate to docker directory
cd deployment/docker

# 2. Create .env file
cp .env.example .env

# 3. Configure environment (see Configuration section)
nano .env

# 4. Build and start services
docker-compose build
docker-compose up -d

# 5. Enable monitoring (optional but recommended)
docker-compose --profile monitoring up -d

# 6. Verify all services are healthy
docker-compose ps
```

---

## Detailed Setup

### Step 1: Environment Configuration

Edit `.env` file with these **critical settings**:

```bash
# ============================================================================
# Environment Mode - SET THIS TO TESTNET
# ============================================================================
ENVIRONMENT=testnet

# ============================================================================
# Database Configuration
# ============================================================================
POSTGRES_DB=trader_testnet
POSTGRES_USER=trader
POSTGRES_PASSWORD=YOUR_SECURE_PASSWORD_HERE  # ⚠️ CHANGE THIS
POSTGRES_PORT=5432

# ============================================================================
# Redis Configuration
# ============================================================================
REDIS_PASSWORD=YOUR_REDIS_PASSWORD_HERE  # ⚠️ CHANGE THIS
REDIS_PORT=6379

# ============================================================================
# Trading Configuration - CRITICAL FOR PAPER TRADING
# ============================================================================
# Enable paper trading mode (DO NOT CHANGE)
PAPER_TRADING=true

# Enable trading cycles (SET TO TRUE to start)
TRADING_ENABLED=true

# Use Binance testnet (DO NOT CHANGE)
BINANCE_TESTNET=true

# Trading Cycle Interval (seconds)
# Default: 180 (3 minutes = 480 cycles/day)
# For testing: 60 (1 minute = 1440 cycles/day)
# Min: 10 | Max: 3600
TRADING_CYCLE_INTERVAL_SECONDS=60

# ============================================================================
# Binance Testnet API - GET KEYS FROM https://testnet.binancefuture.com/
# ============================================================================
BINANCE_TESTNET_API_KEY=your_testnet_api_key_here  # ⚠️ REQUIRED
BINANCE_TESTNET_API_SECRET=your_testnet_secret_here  # ⚠️ REQUIRED
BINANCE_TESTNET_ENABLED=true

# ============================================================================
# OpenRouter LLM API - GET KEY FROM https://openrouter.ai/
# ============================================================================
OPENROUTER_API_KEY=sk-or-v1-your-key-here  # ⚠️ REQUIRED
OPENROUTER_DEFAULT_MODEL=deepseek/deepseek-v3.2-exp

# Cost limits (adjust based on budget)
LLM_DAILY_COST_LIMIT=2.00
LLM_MONTHLY_COST_LIMIT=50.00

# ============================================================================
# Risk Management - PAPER TRADING SETTINGS
# ============================================================================
STARTING_CAPITAL_CHF=2627.00
CIRCUIT_BREAKER_THRESHOLD_PCT=7.0
MAX_POSITION_SIZE_PCT=10.0
MIN_LEVERAGE=5
MAX_LEVERAGE=40

# ============================================================================
# Monitoring (RECOMMENDED FOR 7-DAY TEST)
# ============================================================================
ENABLE_MONITORING=true
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000
GRAFANA_PASSWORD=admin  # Change this for production

# ============================================================================
# Alert Configuration (OPTIONAL BUT RECOMMENDED)
# ============================================================================
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

EMAIL_ENABLED=false
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_SMTP_USER=your-email@gmail.com
EMAIL_SMTP_PASSWORD=your-app-password
EMAIL_FROM=trading-alerts@yourdomain.com
EMAIL_TO=your-email@gmail.com
```

### Step 2: Validate API Keys

```bash
# Test Binance Testnet connectivity
docker-compose run --rm trader python -c "
import ccxt
exchange = ccxt.binance({
    'apiKey': 'YOUR_API_KEY',
    'secret': 'YOUR_SECRET',
    'options': {'defaultType': 'future'},
    'urls': {'api': {'public': 'https://testnet.binancefuture.com/fapi/v1'}}
})
exchange.load_markets()
print('✓ Binance testnet connected')
balance = exchange.fetch_balance()
print(f'Testnet balance: {balance}')
"

# Test OpenRouter LLM API
curl https://openrouter.ai/api/v1/auth/key \
  -H "Authorization: Bearer YOUR_OPENROUTER_KEY"
```

### Step 3: Start Services

```bash
# Build Docker images (first time only)
docker-compose build

# Start core services (without monitoring)
docker-compose up -d postgres redis trader celery-worker celery-beat

# OR start with monitoring (recommended)
docker-compose --profile monitoring up -d

# Check service health
docker-compose ps

# Expected output:
# NAME                    STATUS              PORTS
# trader-postgres         Up (healthy)        0.0.0.0:5432->5432/tcp
# trader-redis            Up (healthy)        0.0.0.0:6379->6379/tcp
# trader-app              Up (healthy)        0.0.0.0:8000->8000/tcp
# trader-celery-worker    Up                  -
# trader-celery-beat      Up                  -
# trader-prometheus       Up                  0.0.0.0:9090->9090/tcp
# trader-grafana          Up                  0.0.0.0:3000->3000/tcp
```

### Step 4: Verify System Health

```bash
# 1. Check API health endpoint
curl http://localhost:8000/health

# Expected: {"status": "healthy", "timestamp": "..."}

# 2. Check Prometheus metrics
curl http://localhost:9090/api/v1/query?query=up

# 3. Access Grafana dashboards
open http://localhost:3000
# Login: admin / admin (or your GRAFANA_PASSWORD)

# 4. Check logs
docker-compose logs -f trader          # Application logs
docker-compose logs -f celery-worker   # Background tasks
docker-compose logs -f celery-beat     # Scheduler
```

### Step 5: Initialize Database

```bash
# Run database migrations
docker-compose exec trader python -m alembic upgrade head

# Verify database schema
docker-compose exec postgres psql -U trader -d trader_testnet -c "\dt"

# Expected tables:
# - positions
# - orders
# - trades
# - performance_metrics
# - market_data
# - decisions
```

### Step 6: Enable Trading Cycles

The system uses **Celery Beat** to schedule trading decisions at configurable intervals (default: 3 minutes, configurable via `TRADING_CYCLE_INTERVAL_SECONDS` environment variable):

```python
# Create file: workspace/tasks/trading_cycle.py
"""
Trading cycle task - executes at configurable intervals
(default: 3 minutes, configured via TRADING_CYCLE_INTERVAL_SECONDS)
"""
from celery import shared_task
from workspace.features.decision_engine.engine import DecisionEngine
from workspace.features.paper_trading.paper_executor import PaperTradingExecutor
from workspace.features.market_data.service import MarketDataService
import logging

logger = logging.getLogger(__name__)


@shared_task
def execute_trading_cycle():
    """
    Execute one complete trading cycle:
    1. Fetch market data
    2. Generate LLM decision
    3. Execute trade (paper)
    4. Update metrics
    """
    try:
        logger.info("Starting trading cycle...")

        # Initialize services
        market_data = MarketDataService()
        decision_engine = DecisionEngine()
        executor = PaperTradingExecutor()

        # Fetch current market data
        symbol = "BTC/USDT:USDT"
        data = await market_data.get_ohlcv(symbol, "5m", limit=100)

        # Generate trading decision
        decision = await decision_engine.analyze_market(data)

        # Execute trade if signal present
        if decision.signal != "HOLD":
            await executor.execute_decision(decision)

        logger.info(f"Trading cycle complete. Decision: {decision.signal}")
        return {"status": "success", "decision": decision.signal}

    except Exception as e:
        logger.error(f"Trading cycle failed: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}
```

Then configure Celery Beat schedule in `workspace/celery_app.py`:

```python
# Update celery_app.py to include the schedule
from celery.schedules import crontab
from workspace.api.config import settings

app.conf.beat_schedule = {
    'trading-cycle-periodic': {
        'task': 'workspace.tasks.trading_cycle.execute_trading_cycle',
        'schedule': float(settings.trading_cycle_interval_seconds),  # From environment variable
        'options': {
            'expires': max(10, settings.trading_cycle_interval_seconds - 10),  # Expire before next run
        }
    },
    'daily-performance-report': {
        'task': 'workspace.tasks.reporting.generate_daily_report',
        'schedule': crontab(hour=0, minute=0),  # Midnight UTC
    },
}
```

### Step 7: Start Paper Trading

```bash
# 1. Restart services to load new tasks
docker-compose restart trader celery-worker celery-beat

# 2. Monitor first few cycles
docker-compose logs -f celery-worker

# You should see:
# [INFO] Starting trading cycle...
# [INFO] Fetching market data for BTC/USDT:USDT
# [INFO] Generating LLM decision...
# [INFO] Decision: BUY (confidence: 0.75)
# [INFO] Executing paper trade...
# [INFO] Trading cycle complete. Decision: BUY

# 3. Verify trades are being recorded
docker-compose exec postgres psql -U trader -d trader_testnet -c \
  "SELECT COUNT(*) FROM trades WHERE created_at > NOW() - INTERVAL '1 hour';"

# 4. Check performance metrics
curl http://localhost:8000/api/v1/performance/summary
```

---

## Monitoring & Metrics

### Access Monitoring Dashboards

```bash
# Grafana (Primary Dashboard)
open http://localhost:3000
# Login: admin / <GRAFANA_PASSWORD>
# Navigate to: Dashboards → Trading System Overview

# Prometheus (Raw Metrics)
open http://localhost:9090
# Useful queries:
# - up{job="trader"}  # Service health
# - trading_decisions_total  # Total decisions made
# - trading_pnl_total  # Cumulative P&L
# - trading_win_rate  # Win rate percentage
```

### Key Metrics to Monitor

| Metric | Target | Alert Threshold |
|--------|--------|----------------|
| **System Uptime** | 99.5%+ | < 99.0% |
| **Decision Latency (P95)** | < 2s | > 3s |
| **Win Rate** | > 45% | < 35% |
| **Sharpe Ratio** | > 1.0 | < 0.5 |
| **Max Drawdown** | < 10% | > 15% |
| **LLM Cost/Day** | < $2 | > $5 |
| **Cache Hit Rate** | > 80% | < 70% |
| **Error Rate** | < 0.1% | > 1% |

### Daily Check Commands

```bash
# Morning check routine (run once daily)
./deployment/docker/scripts/daily-check.sh

# Manual checks
# 1. System health
docker-compose ps

# 2. Today's P&L
docker-compose exec trader python -c "
from workspace.features.paper_trading.paper_executor import PaperTradingExecutor
executor = PaperTradingExecutor()
report = executor.get_performance_report()
print(f'P&L Today: ${report[\"daily_pnl\"]:.2f}')
print(f'Total P&L: ${report[\"total_pnl\"]:.2f}')
print(f'Win Rate: {report[\"win_rate\"]:.1f}%')
"

# 3. Recent trades
docker-compose exec postgres psql -U trader -d trader_testnet -c \
  "SELECT * FROM trades ORDER BY created_at DESC LIMIT 10;"

# 4. Error logs
docker-compose logs --since 1h trader | grep ERROR
```

### Automated Reporting

Daily reports will be:
1. **Saved to**: `deployment/docker/logs/reports/daily-YYYY-MM-DD.json`
2. **Sent to Slack** (if configured)
3. **Emailed** (if configured)
4. **Available via API**: `GET http://localhost:8000/api/v1/reports/daily/YYYY-MM-DD`

---

## Troubleshooting

### Common Issues

#### 1. Services Won't Start
```bash
# Check Docker resources
docker info

# Check logs
docker-compose logs

# Reset and rebuild
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

#### 2. Trading Cycles Not Running
```bash
# Check Celery Beat is running
docker-compose logs celery-beat | grep "beat"

# Check task schedule loaded
docker-compose exec celery-beat celery -A workspace.celery_app inspect scheduled

# Manually trigger a cycle
docker-compose exec trader python -c "
from workspace.tasks.trading_cycle import execute_trading_cycle
execute_trading_cycle.delay()
"
```

#### 3. LLM API Errors
```bash
# Check OpenRouter status
curl https://openrouter.ai/api/v1/auth/key \
  -H "Authorization: Bearer $OPENROUTER_API_KEY"

# Check daily cost limit
docker-compose exec trader python -c "
from workspace.features.decision_engine.cost_tracker import CostTracker
tracker = CostTracker()
print(f'Today: ${tracker.get_daily_cost():.2f}')
print(f'Limit: ${tracker.daily_limit:.2f}')
"

# Increase limit if needed (in .env)
LLM_DAILY_COST_LIMIT=5.00
```

#### 4. Database Connection Issues
```bash
# Check PostgreSQL is running
docker-compose exec postgres pg_isready

# Check connections
docker-compose exec postgres psql -U trader -d trader_testnet -c \
  "SELECT count(*) FROM pg_stat_activity WHERE datname='trader_testnet';"

# Reset connections
docker-compose restart postgres
docker-compose restart trader
```

#### 5. High Memory Usage
```bash
# Check resource usage
docker stats

# If memory > 6GB, increase Docker resources:
# Docker Desktop → Settings → Resources → Memory → 8GB+

# Or reduce worker concurrency in docker-compose.yml:
# celery-worker:
#   command: celery -A workspace.celery_app worker --concurrency=1
```

### Emergency Procedures

#### Circuit Breaker Triggered
```bash
# System will auto-pause if daily loss > 7%
# Check reason
docker-compose logs trader | grep "CIRCUIT BREAKER"

# Review trades
docker-compose exec postgres psql -U trader -d trader_testnet -c \
  "SELECT * FROM trades WHERE created_at > NOW() - INTERVAL '24 hours' ORDER BY pnl;"

# Reset if needed (CAREFUL!)
docker-compose exec trader python -c "
from workspace.features.risk_manager.circuit_breaker import reset_circuit_breaker
reset_circuit_breaker()
print('Circuit breaker reset')
"
```

#### System Crash Recovery
```bash
# 1. Check what failed
docker-compose ps
docker-compose logs trader --tail 100

# 2. Restart failed services
docker-compose restart trader celery-worker

# 3. Verify recovery
curl http://localhost:8000/health

# 4. Check for data loss
docker-compose exec postgres psql -U trader -d trader_testnet -c \
  "SELECT MAX(created_at) FROM trades;"
```

---

## Performance Analysis

### After 7 Days Complete

```bash
# Generate final report
docker-compose exec trader python -c "
from workspace.features.paper_trading.paper_executor import PaperTradingExecutor
from workspace.features.paper_trading.performance_tracker import PaperTradingPerformanceTracker

executor = PaperTradingExecutor()
tracker = PaperTradingPerformanceTracker()

# Full 7-day report
report = executor.get_performance_report()

print('=' * 60)
print('7-DAY PAPER TRADING FINAL REPORT')
print('=' * 60)
print(f'Initial Balance: ${executor.initial_balance:,.2f}')
print(f'Final Balance: ${executor.virtual_portfolio.balance:,.2f}')
print(f'Total Return: {report[\"portfolio\"][\"total_return\"]:.2f}%')
print(f'')
print(f'Trades Executed: {report[\"total_trades\"]}')
print(f'Win Rate: {report[\"win_rate\"]:.1f}%')
print(f'Average Win: ${report[\"avg_win\"]:.2f}')
print(f'Average Loss: ${report[\"avg_loss\"]:.2f}')
print(f'Win/Loss Ratio: {report[\"win_loss_ratio\"]:.2f}')
print(f'')
print(f'Sharpe Ratio: {report[\"sharpe_ratio\"]:.2f}')
print(f'Max Drawdown: {report[\"max_drawdown\"]:.2f}%')
print(f'Profit Factor: {report[\"profit_factor\"]:.2f}')
print(f'')
print(f'System Uptime: {report[\"uptime_pct\"]:.2f}%')
print(f'Avg Decision Latency: {report[\"avg_latency_ms\"]:.0f}ms')
print(f'Total LLM Cost: ${report[\"total_llm_cost\"]:.2f}')
print('=' * 60)
"

# Export trades to CSV
docker-compose exec postgres psql -U trader -d trader_testnet -c \
  "COPY (SELECT * FROM trades ORDER BY created_at) TO STDOUT WITH CSV HEADER" \
  > paper_trading_trades_7day.csv

# Generate charts (requires Python with matplotlib)
docker-compose exec trader python -m workspace.scripts.generate_performance_charts \
  --output /app/data/charts/

# Access charts
open deployment/docker/data/charts/equity_curve.png
open deployment/docker/data/charts/drawdown.png
open deployment/docker/data/charts/trade_distribution.png
```

### Success Criteria Checklist

- [ ] System uptime ≥ 99.5% (max 1.2 hours downtime)
- [ ] No critical errors or crashes
- [ ] Decision latency < 2s (P95)
- [ ] All trades executed successfully
- [ ] Circuit breaker did not trigger (or triggered correctly on 7% loss)
- [ ] LLM decisions show consistent quality
- [ ] Performance metrics within expected ranges
- [ ] Monitoring dashboards operational throughout
- [ ] Daily reports generated successfully

### Next Steps After Validation

1. **Review LLM decision quality** → Optimize prompts if needed
2. **Analyze performance patterns** → Identify strengths/weaknesses
3. **Document findings** → Create go/no-go recommendation
4. **If successful** → Proceed to production deployment (DER-20)
5. **If issues found** → Address and re-run validation

---

## Files and Directories

```
deployment/docker/
├── .env                        # Your configuration (DO NOT COMMIT)
├── .env.example                # Template
├── docker-compose.yml          # Service definitions
├── Dockerfile                  # Application image
├── quick-start-mac.sh         # Automated setup script
├── logs/                       # Application logs
│   ├── trader.log             # Main application
│   ├── celery-worker.log      # Background tasks
│   ├── celery-beat.log        # Scheduler
│   └── reports/               # Daily performance reports
├── data/                       # Persistent data
│   ├── postgres/              # Database files
│   ├── redis/                 # Cache files
│   ├── charts/                # Performance charts
│   └── exports/               # Data exports
└── prometheus.yml             # Prometheus configuration

workspace/
├── tasks/
│   ├── trading_cycle.py       # Trading cycle task (CREATE THIS)
│   └── reporting.py           # Daily report task (CREATE THIS)
├── features/
│   ├── paper_trading/
│   │   ├── paper_executor.py  # ✅ Already implemented
│   │   ├── virtual_portfolio.py
│   │   └── performance_tracker.py
│   ├── decision_engine/       # LLM decision making
│   ├── market_data/           # Market data fetching
│   └── risk_manager/          # Risk management
└── celery_app.py              # Celery configuration (UPDATE THIS)
```

---

## Quick Reference

### Essential Commands

```bash
# Start paper trading
cd deployment/docker && docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f trader

# Stop paper trading
docker-compose down

# Full reset (⚠️ DELETES ALL DATA)
docker-compose down -v && docker-compose up -d
```

### Important URLs

- **API Health**: http://localhost:8000/health
- **API Docs**: http://localhost:8000/docs
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090

### Support

- **Linear Project**: https://linear.app/derobiwan/project/trader-8990f52344cc
- **Issue DER-11**: Setup continuous paper trading environment
- **Documentation**: `docs/PAPER_TRADING_SETUP_GUIDE.md` (this file)
- **Session Summary**: `docs/sessions/SESSION_SUMMARY_2025-11-01-18-30.md`

---

**Last Updated**: 2025-11-01
**Status**: Ready for implementation
**Next Step**: Create trading cycle tasks and configure Celery Beat schedule
