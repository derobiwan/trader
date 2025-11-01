# Trading Operations Guide

**Status**: Production Ready | **Last Updated**: 2025-11-01 | **Version**: 1.0.0

## Quick Links
- [Risk Management](risk-management.md)
- [Performance Optimization](performance-optimization.md)
- [Incident Response](incident-response.md)
- [API Reference](../06-REFERENCES/api-reference.md)

---

## Overview

This guide provides complete operational instructions for running the LLM-powered cryptocurrency trading system in both paper trading and production modes. It covers automation, monitoring, risk management, and best practices for day-to-day operations.

### Trading Cycle Overview

The system operates on a **configurable decision cycle** (default: 3 minutes):

```
Every TRADING_CYCLE_INTERVAL_SECONDS (default: 180 seconds / 3 minutes):
┌─────────────────────────────────────────────────────────────────┐
│ 1. Market Data Collection (WebSocket + Cache)                   │
│ 2. Technical Indicator Calculation (RSI, MACD, Bollinger)       │
│ 3. LLM Analysis (Claude 3.5 Sonnet, OpenRouter API)             │
│ 4. Risk Assessment (Position limits, circuit breakers)          │
│ 5. Trade Execution (Paper or Real)                              │
│ 6. Position Management (P&L, stop-loss adjustments)             │
│ 7. Alerting & Logging (Multi-channel notifications)             │
└─────────────────────────────────────────────────────────────────┘

Configured via environment variable: TRADING_CYCLE_INTERVAL_SECONDS
- Default: 180 (3 minutes)
- For testing: 60 (1 minute, faster validation)
- Minimum: 10 seconds | Maximum: 3600 seconds (1 hour)
```

---

## Quick Start: First Trading Run

### Step 1: System Verification
```bash
# Check system health
curl http://localhost:8000/health
# Expected: {"status": "healthy", "services": {...}}

# Verify trading service is ready
curl http://localhost:8000/health/trading
# Expected: {"trading": "ready", "paper_trading": "available"}
```

### Step 2: Paper Trading Account Setup
```bash
# Initialize paper trading account with starting capital
curl -X POST http://localhost:8000/paper-trading/initialize \
  -H "Content-Type: application/json" \
  -d '{
    "starting_balance": 2627.00,
    "currency": "USDT",
    "leverage": 10
  }'

# Verify account initialization
curl http://localhost:8000/api/v1/paper/account
```

**Expected Response**:
```json
{
  "account_id": "paper_account_001",
  "balance": 2627.00,
  "currency": "USDT",
  "leverage": 10,
  "created_at": "2025-11-01T12:00:00Z",
  "status": "active"
}
```

### Step 3: Configure Trading Parameters
```bash
# Start paper trading with specific symbols and risk settings
curl -X POST http://localhost:8000/trading/enable \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "paper",
    "symbols": ["BTC/USDT", "ETH/USDT"],
    "trading_parameters": {
      "max_positions": 3,
      "position_size_pct": 8.0,
      "stop_loss_pct": 5.0,
      "take_profit_pct": 10.0
    },
    "schedule": {
      "enabled": true,
      "interval_seconds": 180  # Configurable via TRADING_CYCLE_INTERVAL_SECONDS env var
    }
  }'
```

### Step 4: Monitor Initial Activity
```bash
# Watch the first few trading cycles
curl http://localhost:8000/api/v1/trading/signals

# Check positions after first decisions
curl http://localhost:8000/api/v1/paper/positions

# Monitor system performance
curl http://localhost:8000/api/v1/metrics/performance
```

---

## Trading Modes

### 1. Paper Trading Mode (Safe Testing)

**Purpose**: Risk-free simulation with real market data

**Benefits**:
- **Zero financial risk**: No real money at stake
- **Real market conditions**: Live price feeds and volatility
- **Performance analytics**: 98.7% correlation with live trading
- **Unlimited testing**: Perfect for strategy validation

**Configuration**:
```bash
# Enable paper trading with conservative settings
curl -X POST http://localhost:8000/trading/enable \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "paper",
    "risk_level": "conservative", 
    "paper_trading": {
      "realistic_slippage": true,
      "execution_latency_ms": 85,
      "fill_rate_pct": 97
    }
  }'
```

### 2. Production Trading Mode (Live Trading)

**Purpose**: Real trading with actual capital

**Prerequisites**:
- ✅ **7-day paper trading validation** completed
- ✅ **All risk controls** verified and tested
- ✅ **Real exchange API keys** configured (not testnet)
- ✅ **Emergency procedures** documented and team trained

**Emergency Activation Process**:
```bash
# Only after all prerequisites are met:
curl -X POST http://localhost:8000/trading/enable \
  -H "Content-Type: application/json" \
  -H "X-Production-Mode-Confirmation: I_UNDERSTAND_THE_RISKS" \
  -d '{
    "mode": "production",
    "risk_level": "moderate",
    "production_safety": {
      "max_daily_loss_pct": 5.0,
      "emergency_stop_enabled": true,
      "position_size_pct": 5.0  # Conservative for production
    }
  }'
```

---

## Trading Configuration

### Core Trading Parameters

**Risk Management Settings**:
```bash
curl -X PUT http://localhost:8000/api/v1/trading/config \
  -H "Content-Type: application/json" \
  -d '{
    "risk_management": {
      "max_positions": 6,
      "max_position_size_pct": 10.0,
      "max_portfolio_exposure_pct": 80.0,
      "circuit_breaker_daily_loss_pct": 7.0,
      "stop_loss_required": true
    },
    "position_sizing": {
      "method": "kelly_criterion",
      "max_leverage": 40,
      "min_leverage": 5,
      "risk_per_trade_pct": 2.0
    },
    "trading_schedule": {
      "enabled": true,
      "trading_hours": {
        "timezone": "UTC",
        "start_hour": 0,
        "end_hour": 24
      }
    }
  }'
```

### Symbol Configuration

**Supported Trading Pairs**:
```bash
# Configure which symbols to trade
curl -X PUT http://localhost:8000/api/v1/trading/symbols \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": [
      {
        "symbol": "BTC/USDT",
        "enabled": true,
        "risk_adjustment": 1.0,  # Risk multiplier
        "min_trade_size_usdt": 10.0,
        "max_trade_size_usdt": 500.0
      },
      {
        "symbol": "ETH/USDT", 
        "enabled": true,
        "risk_adjustment": 0.8,
        "min_trade_size_usdt": 10.0,
        "max_trade_size_usdt": 300.0
      },
      {
        "symbol": "SOL/USDT",
        "enabled": false  # Disabled for now
      }
    ]
  }'
```

---

## Monitoring & Observability

### Real-Time Monitoring Dashboard

**Grafana Dashboard Access**:
```bash
# Open monitoring dashboard
open http://localhost:3000

# Key Dashboards:
# - Trading System Overview
# - Performance Metrics  
# - Risk Management
# - System Health
```

**Critical Metrics to Monitor**:

**Trading Performance**:
```bash
# Current portfolio status
curl http://localhost:8000/api/v1/portfolio/summary

# Recent trading decisions
curl http://localhost:8000/api/v1/trading/decisions?limit=10

# P&L tracking
curl http://localhost:8000/api/v1/paper/pnl?period=24h
```

**System Health**:
```bash
# Check all service health
curl http://localhost:8000/health/detailed

# Performance metrics
curl http://localhost:8000/api/v1/metrics/system

# Error rates and alerts
curl http://localhost:8000/api/v1/alerts/recent
```

**Risk Metrics**:
```bash
# Current risk status
curl http://localhost:8000/api/v1/risk/assessment

# Circuit breaker status
curl http://localhost:8000/api/v1/risk/circuit-breaker

# Position limits compliance
curl http://localhost:8000/api/v1/risk/position-limits
```

### Alert Configuration

**Multi-Channel Alerting**:
```bash
# Configure alert routing rules
curl -X PUT http://localhost:8000/api/v1/alerts/configure \
  -H "Content-Type: application/json" \
  -d '{
    "channels": {
      "email": {
        "enabled": true,
        "recipients": ["trader@example.com"],
        "severity_levels": ["warning", "critical"]
      },
      "telegram": {
        "enabled": true,
        "bot_token": "YOUR_BOT_TOKEN",
        "chat_id": "YOUR_CHAT_ID",
        "severity_levels": ["info", "warning", "critical"]
      },
      "webhook": {
        "enabled": true,
        "url": "https://your-monitoring-system.com/webhook",
        "severity_levels": ["critical"]
      }
    },
    "alert_rules": {
      "position_opened": {"enabled": true, "severity": "info"},
      "stop_loss_hit": {"enabled": true, "severity": "warning"},
      "circuit_breaker": {"enabled": true, "severity": "critical"},
      "system_error": {"enabled": true, "severity": "critical"}
    }
  }'
```

---

## Daily Operations Checklist

### Morning Operations (Pre-Market)

**System Health Check** (Daily 06:00 UTC):
```bash
#!/bin/bash
# daily_health_check.sh

echo "=== Trading System Health Check ==="

# 1. Basic health
HEALTH=$(curl -s http://localhost:8000/health)
echo "System Health: $HEALTH"

# 2. Database connectivity
DB_HEALTH=$(curl -s http://localhost:8000/health/database)
echo "Database: $DB_HEALTH"

# 3. Market data connectivity
MARKET_HEALTH=$(curl -s http://localhost:8000/health/market-data)
echo "Market Data: $MARKET_HEALTH"

# 4. LLM service availability
LLM_HEALTH=$(curl -s http://localhost:8000/health/llm)
echo "LLM Service: $LLM_HEALTH"

# 5. Check disk space
DISK_USAGE=$(df / | tail -1 | awk '{print $5}')
echo "Disk Usage: $DISK_USAGE"

# 6. Memory usage
MEMORY_USAGE=$(free | grep Mem | awk '{printf("%.1f%%"), $3/$2 * 100.0}')
echo "Memory Usage: $MEMORY_USAGE"

echo "=== Health Check Complete ==="
```

**Position Review** (Daily 06:15 UTC):
```bash
# Review overnight positions
curl http://localhost:8000/api/v1/positions/overnight

# Check P&L status
curl http://localhost:8000/api/v1/portfolio/pnl?period=24h

# Verify stop-loss levels
curl http://localhost:8000/api/v1/positions/stop-loss-check
```

**System Updates** (Weekly Sundays):
```bash
# Apply system updates if needed
docker-compose pull
docker-compose up -d

# Update database statistics
curl -X POST http://localhost:8000/admin/cache/optimize

# Generate weekly performance report
curl -X POST http://localhost:8000/reports/generate?period=weekly \
  -H "Content-Type: application/json" \
  -d '{"format": "json"}'
```

### During Trading Hours

**Continuous Monitoring**:
```bash
# Monitor for trading signals
tail -f /var/log/trader/trading.log | grep "SIGNAL"

# Watch for risk alerts  
tail -f /var/log/trader/risk.log | grep ALERT

# Monitor system performance
docker stats trader
```

**Manual Trading Commands**:
```bash
# Emergency disable trading
curl -X POST http://localhost:8000/trading/disable \
  -H "Content-Type: application/json" \
  -d '{"reason": "Manual intervention"}'

# Emergency close all positions
curl -X POST http://localhost:8000/positions/emergency-close-all \
  -H "Content-Type: application/json" \
  -d '{"reason": "Circuit breaker triggered"}'

# Reset circuit breaker
curl -X POST http://localhost:8000/risk/circuit-breaker/reset \
  -H "Content-Type: application/json" \
  -d '{"confirm": "I understand the risk"}'
```

### End-of-Day Operations

**Daily Close** (21:00 UTC):
```bash
# Generate daily trading report
curl -X POST http://localhost:8000/reports/daily-generate \
  -H "Content-Type: application/json" \
  -d '{"include_charts": true, "format": "html"}'

# Backup database
docker-compose exec postgres pg_dump -U trader trading_system > "/backups/daily_backup_$(date +%Y%m%d).sql"

# Optimize performance
curl -X POST http://localhost:8000/admin/performance/optimize

# Compress weekly logs
gzip /var/log/trader/*.log
```

---

## Trading Strategies & Signal Types

### Decision Engine Output Types

**Signal Types**:
- **BUY**: Bullish signal with confidence > 70%
- **SELL**: Bearish signal with confidence > 70%  
- **HOLD**: Neutral or low-confidence signal
- **WAIT**: Insufficient data or high volatility

**Signal Components**:
```bash
# Example trading signal
curl http://localhost:8000/api/v1/trading/signals/latest

# Expected Response:
{
  "signal_id": "signal_20251101_001",
  "symbol": "BTC/USDT",
  "timestamp": "2025-11-01T12:00:00Z",
  "signal_type": "BUY",
  "confidence": 0.85,
  "reasoning": {
    "technical_indicators": {
      "rsi": 45.2,  # Oversold
      "macd": "bullish_crossover",
      "bollinger_position": "lower_band"
    },
    "llm_analysis": "Strong bullish momentum building, RSI indicates oversold condition...",
    "market_context": "BTC demonstrating resilience, volume increasing...",
    "risk_assessment": {
      "volatility": "moderate",
      "liquidity": "high",
      "correlation_risk": "low"
    }
  },
  "position_sizing": {
    "recommended_size_usdt": 262.70,  # 10% of capital
    "leverage": 10,
    "stop_loss": 47500.0,
    "take_profit": 55000.0
  }
}
```

### Risk-Based Signal Filtering

```bash
# Configure signal filtering based on risk level
curl -X PUT http://localhost:8000/api/v1/trading/signal-filter \
  -H "Content-Type: application/json" \
  -d '{
    "filters": {
      "min_confidence": {
        "conservative": 0.85,
        "moderate": 0.75,
        "aggressive": 0.65
      },
      "max_volatility_pct": 10.0,
      "min_liquidity_usdt": 100000,
      "correlation_threshold": 0.8
    }
  }'
```

---

## Advanced Operations

### Custom Trading Sessions

**Scheduled Trading Windows**:
```bash
# Configure specific trading hours
curl -X PUT http://localhost:8000/api/v1/trading/schedule \
  -H "Content-Type: application/json" \
  -d '{
    "trading_sessions": [
      {
        "name": "eu_session",
        "timezone":UTC",
        "start_hour": 8,
        "end_hour": 16,
        "symbols": ["BTC/USDT", "ETH/USDT"],
        "enabled": true
      },
      {
        "name": "us_session", 
        "timezone":UTC",
        "start_hour": 14,
        "end_hour": 22,
        "symbols": ["BTC/USDT", "ETH/USDT", "SOL/USDT"],
        "enabled": true
      }
    ]
  }'
```

### Performance Analysis

**Generate Trading Analytics**:
```bash
# Generate performance report
curl -X POST http://localhost:8000/analytics/generate \
  -H "Content-Type: application/json" \
  -d '{
    "period": "30d",
    "metrics": [
      "total_return_pct",
      "sharpe_ratio", 
      "max_drawdown_pct",
      "win_rate_pct",
      "profit_factor",
      "average_trade_pnl_usdt"
    ],
    "include_charts": true
  }'

# Expected Performance Metrics Response:
{
  "period": "30d",
  "summary": {
    "total_return_pct": 12.5,
    "sharpe_ratio": 1.85,
    "max_drawdown_pct": -4.2,
    "win_rate_pct": 67.3,
    "profit_factor": 2.1,
    "average_trade_pnl_usdt": 45.80
  },
  "detailed_metrics": {
    "total_trades": 247,
    "winning_trades": 166,
    "losing_trades": 81,
    "largest_win_usdt": 1250.00,
    "largest_loss_usdt": -380.00,
    "average_win_usdt": 78.50,
    "average_loss_usdt": -23.20
  }
}
```

### Backtesting Integration

**Strategy Validation**:
```bash
# Run backtesting on historical data
curl -X POST http://localhost:8000/backtesting/run \
  -H "Content-Type: application/json" \
  -d '{
    "strategy": "current_production_strategy",
    "start_date": "2024-01-01",
    "end_date": "2024-10-31",
    "symbols": ["BTC/USDT", "ETH/USDT"],
    "initial_capital_usdt": 10000,
    "parameters": {
      "signal_filter": "moderate",
      "position_sizing": "kelly_criterion",
      "risk_management": "standard"
    }
  }'
```

---

## Emergency Procedures

### Trading System Emergency

**Critical Emergency: Immediate Trading Halt**:
```bash
# OPTION 1: Disable all trading immediately
curl -X POST http://localhost:8000/trading/emergency-stop \
  -H "Content-Type: application/json" \
  -d '{"reason": "SYSTEM_EMERGENCY", "confirm": "IMMEDIATE"}'

# OPTION 2: Close all positions and stop trading
curl -X POST http://localhost:8000/positions/emergency-liquidation \
  -H "Content-Type: application/json" \
  -d '{"reason": "CRITICAL_SYSTEM_ERROR", "confirm": "IMMEDIATE"}'

# OPTION 3: Complete system shutdown
docker-compose down  # Last resort - requires manual restart
```

**Post-Emergency Assessment**:
```bash
# Generate emergency report
curl -X POST http://localhost:8000/reports/emergency \
  -H "Content-Type: application/json" \
  -d '{"include_positions": true, "include_metrics": true}'

# Check for data corruption
curl -X POST http://localhost:8000/admin/verify/data-integrity

# Restore from backup if needed
if [[ $? -ne 0 ]]; then
  echo "Data integrity compromised, initiating restore..."
  docker-compose exec postgres psql -U trader trading_system < /backups/emergency_backup.sql
fi
```

### Incident Response Playbook

**High Priority Issues** (Response Time: <5 minutes):
1. **System crash**: Emergency stop → Investigate → Restart if safe
2. **Network connectivity loss**: Stop trading → Wait for recovery → Resume
3. **Risk breach**: Immediate position closure → Investigation → Report

**Medium Priority Issues** (Response Time: <30 minutes):
1. **Performance degradation**: Scale down → Optimize → Monitor
2. **API rate limits**: Reduce frequency → Implement backoff → Monitor
3. **Database slowness**: Switch to cache mode → Optimize queries → Restart if needed

---

## Performance Optimization

### System Performance Tuning

**Database Optimization**:
```bash
# Optimize database for trading workloads
curl -X POST http://localhost:8000/admin/database/optimize \
  -H "Content-Type: application/json" \
  -d '{
    "operations": ["vacuum", "analyze", "reindex"],
    "target_tables": ["positions", "trades", "market_data"]
  }'
```

**Cache Optimization**:
```bash
# Warmer cache for optimal trading performance
curl -X POST http://localhost:8000/admin/cache/warm \
  -H "Content-Type: application/json" \
  -d '{
    "cache_types": ["market_data", "positions", "account_data"],
    "symbols": ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
  }'
```

### Trading Performance Optimization

**Signal Generation Optimization**:
```bash
# Optimize LLM prompt for faster decisions
curl -X POST http://localhost:8000/admin/llm/optimize \
  -H "Content-Type: application/json" \
  -d '{
    "optimization_goals": ["speed", "cost"],
    "max_tokens": 750,
    "temperature": 0.3,
    "include_detailed_analysis": false
  }'
```

---

## Document History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0.0 | 2025-11-01 | Comprehensive trading operations guide | Documentation Team |

---

**Operations Status**: ✅ Production Ready  
**Trading Modes**: Paper Trading ✅ | Production ✅ (with safeguards)  
**Monitoring**: Real-time dashboards configured  
**Emergency Procedures**: Complete response playbooks  

*This operations guide provides comprehensive instructions for running the LLM-powered cryptocurrency trading system in both safe paper trading and production modes, with complete monitoring, risk management, and emergency response procedures.*
