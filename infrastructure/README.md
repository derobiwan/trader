# Trading System Infrastructure

Sprint 1 Stream C: Database & Redis Infrastructure

## Overview

This directory contains infrastructure configuration for the trading system:

- **PostgreSQL 15** with **TimescaleDB** extension for time-series data
- **Redis 7** for distributed caching
- **Grafana** for monitoring dashboards
- **Prometheus** for metrics collection

## Quick Start

### 1. Prerequisites

- Docker & Docker Compose installed
- 4GB RAM minimum
- Ports available: 5432 (PostgreSQL), 6379 (Redis), 3000 (Grafana), 9090 (Prometheus)

### 2. Environment Setup

```bash
# Copy environment template
cp .env.example .env

# Edit .env and set secure passwords
nano .env
```

**Critical**: Change these in `.env`:
- `DB_PASSWORD`
- `GRAFANA_PASSWORD`

### 3. Start Infrastructure

```bash
# Start all services
docker-compose up -d

# Check service health
docker-compose ps

# View logs
docker-compose logs -f postgres
docker-compose logs -f redis
```

### 4. Run Database Migrations

```bash
# Run migrations
python workspace/shared/database/migrations/migration_runner.py

# Or dry-run first
python workspace/shared/database/migrations/migration_runner.py --dry-run
```

### 5. Verify Setup

```bash
# Test database connection
python workspace/shared/database/connection.py

# Test Redis connection
python workspace/infrastructure/cache/redis_manager.py

# Run integration tests
pytest workspace/tests/integration/test_database_integration.py -v
pytest workspace/tests/integration/test_redis_integration.py -v
```

## Services

### PostgreSQL (TimescaleDB)

- **Port**: 5432
- **Database**: `trading_system`
- **User**: `trading_user`
- **Features**:
  - Time-series hypertables for trades, metrics, logs
  - Automatic data retention policies (90 days trades, 30 days metrics)
  - Continuous aggregates for fast queries
  - Connection pooling (10-50 connections)

**Connect**:
```bash
docker exec -it trading_postgres psql -U trading_user -d trading_system
```

### Redis

- **Port**: 6379
- **Features**:
  - AOF persistence (appendonly)
  - LRU eviction policy
  - 2GB max memory
  - Connection pooling (50 max connections)

**Connect**:
```bash
docker exec -it trading_redis redis-cli
```

### Grafana

- **URL**: http://localhost:3000
- **Default credentials**: admin / (set in .env)
- **Features**:
  - Pre-configured datasources
  - Trading system dashboards

### Prometheus

- **URL**: http://localhost:9090
- **Features**:
  - Scrapes metrics from FastAPI /metrics endpoint
  - 30-day retention
  - Custom alerts (to be configured)

## Database Schema

### Main Tables

1. **trades** (hypertable)
   - Historical trade records
   - Indexed by timestamp, symbol
   - 1-day chunks
   - 90-day retention

2. **positions**
   - Current and historical positions
   - Updated in real-time
   - Indexed by symbol, status

3. **metrics_snapshots** (hypertable)
   - System performance metrics
   - 1-hour chunks
   - 30-day retention

4. **system_logs** (hypertable)
   - Application logs
   - 1-day chunks
   - 14-day retention

5. **llm_requests**
   - LLM API request audit trail
   - Cost tracking
   - Performance metrics

### Continuous Aggregates

- **daily_trade_stats**: Pre-computed daily statistics per symbol
- **hourly_metrics_rollup**: Hourly system performance metrics

## Performance Targets

### Database

- Query latency: **<10ms p95**
- Connection pool: **10-50 connections**
- Bulk inserts: **>1000 trades/second**
- Query throughput: **>100 queries/second**

### Redis

- GET operation: **<1ms p95**
- SET operation: **<2ms p95**
- Hit rate target: **>70% after 1 hour**
- Memory limit: **2GB**

## Backup Strategy

### PostgreSQL

```bash
# Backup database
docker exec trading_postgres pg_dump -U trading_user trading_system > backup.sql

# Restore database
cat backup.sql | docker exec -i trading_postgres psql -U trading_user trading_system
```

### Redis

```bash
# Redis AOF persists automatically
# Backup AOF file
docker cp trading_redis:/data/appendonly.aof ./redis_backup.aof

# Restore (stop Redis first)
docker-compose stop redis
docker cp ./redis_backup.aof trading_redis:/data/appendonly.aof
docker-compose start redis
```

## Monitoring

### Health Checks

```bash
# Check all services
docker-compose ps

# Database health
curl http://localhost:8000/health/database

# Redis health
curl http://localhost:8000/health/redis
```

### Metrics

- FastAPI metrics: http://localhost:8000/metrics
- Prometheus UI: http://localhost:9090
- Grafana dashboards: http://localhost:3000

## Troubleshooting

### PostgreSQL won't start

```bash
# Check logs
docker-compose logs postgres

# Reset if needed
docker-compose down -v  # WARNING: Deletes all data
docker-compose up -d
```

### Redis connection refused

```bash
# Check Redis is running
docker-compose ps redis

# Test connection
docker exec trading_redis redis-cli ping

# Should return: PONG
```

### Slow queries

```bash
# Connect to database
docker exec -it trading_postgres psql -U trading_user -d trading_system

# Check slow queries
SELECT query, calls, mean_exec_time, max_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

### High memory usage

```bash
# Check container stats
docker stats

# Reduce Redis maxmemory in docker-compose.yml
# Reduce PostgreSQL shared_buffers if needed
```

## Scaling Considerations

### Horizontal Scaling

- Redis: Use Redis Cluster for multi-node setup
- PostgreSQL: Use read replicas for read-heavy workloads

### Vertical Scaling

Edit `docker-compose.yml`:

```yaml
services:
  postgres:
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: '2.0'
```

## Security

### Production Checklist

- [ ] Change all default passwords in .env
- [ ] Enable PostgreSQL SSL connections
- [ ] Enable Redis AUTH
- [ ] Set up firewall rules (only allow internal IPs)
- [ ] Enable Grafana OAuth/LDAP
- [ ] Set up automated backups
- [ ] Configure log shipping to central location
- [ ] Enable audit logging

### Network Security

```yaml
# In docker-compose.yml, bind to localhost only:
ports:
  - "127.0.0.1:5432:5432"  # PostgreSQL
  - "127.0.0.1:6379:6379"  # Redis
```

## Maintenance

### Daily

- [ ] Check service health
- [ ] Monitor disk usage
- [ ] Review error logs

### Weekly

- [ ] Run database vacuum
- [ ] Check backup integrity
- [ ] Review slow queries
- [ ] Update dashboards

### Monthly

- [ ] Update Docker images
- [ ] Review retention policies
- [ ] Analyze growth trends
- [ ] Capacity planning

## Support

For issues:
1. Check logs: `docker-compose logs [service]`
2. Check health: `docker-compose ps`
3. Review this README
4. Check integration tests

---

**Author**: Infrastructure Specialist
**Date**: 2025-10-28
**Sprint**: Sprint 1 Stream C
