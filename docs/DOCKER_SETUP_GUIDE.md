# Docker Setup Guide - LLM Crypto Trading System

Complete guide for setting up the trading system using Docker on Mac (testnet testing) and Ubuntu (production deployment).

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Mac Setup - Testnet Testing](#mac-setup---testnet-testing)
3. [Ubuntu Setup - Production Deployment](#ubuntu-setup---production-deployment)
4. [Configuration](#configuration)
5. [Running the System](#running-the-system)
6. [Monitoring & Logs](#monitoring--logs)
7. [Troubleshooting](#troubleshooting)
8. [Maintenance](#maintenance)

---

## Prerequisites

### Required Software

**For Mac:**
- Docker Desktop for Mac (https://www.docker.com/products/docker-desktop)
- Git
- Code editor (VS Code recommended)

**For Ubuntu:**
- Docker Engine
- Docker Compose
- Git

### System Requirements

**Minimum:**
- 4 GB RAM
- 2 CPU cores
- 20 GB disk space

**Recommended:**
- 8 GB RAM
- 4 CPU cores
- 50 GB disk space (for logs and data)

---

## Mac Setup - Testnet Testing

This section covers setting up the trading system on your Mac for testnet testing with Binance.

### Step 1: Install Docker Desktop

```bash
# Download Docker Desktop from:
# https://www.docker.com/products/docker-desktop

# Or install via Homebrew:
brew install --cask docker

# Start Docker Desktop
open -a Docker

# Verify installation
docker --version
docker-compose --version
```

Expected output:
```
Docker version 24.0.x
Docker Compose version v2.x.x
```

### Step 2: Clone the Repository

```bash
# Navigate to your projects directory
cd ~/Documents/GitProjects/personal

# If not already cloned:
git clone https://github.com/derobiwan/trader.git
cd trader

# Pull latest changes
git checkout main
git pull origin main
```

### Step 3: Set Up Environment Files

```bash
# Navigate to Docker deployment directory
cd deployment/docker

# Copy environment template
cp .env.example .env

# Edit the .env file
nano .env  # or: code .env
```

**Important Configuration for Testnet:**

```bash
# ============================================================================
# Docker Environment Configuration - TESTNET MODE
# ============================================================================

# Database Configuration
POSTGRES_DB=trader_testnet
POSTGRES_USER=trader
POSTGRES_PASSWORD=your_secure_password_here_change_me
POSTGRES_PORT=5432

# Redis Configuration
REDIS_PASSWORD=your_redis_password_here_change_me
REDIS_PORT=6379

# Application Configuration
ENVIRONMENT=testnet
LOG_LEVEL=INFO
APP_PORT=8000

# Trading Configuration (TESTNET MODE)
PAPER_TRADING=true
TRADING_ENABLED=false  # Keep false until you're ready
BINANCE_TESTNET=true

# Binance Testnet API Keys (from testnet.binance.vision)
BINANCE_TESTNET_API_KEY=your_testnet_api_key_here
BINANCE_TESTNET_API_SECRET=your_testnet_secret_here
BINANCE_TESTNET_ENABLED=true

# OpenRouter LLM API
OPENROUTER_API_KEY=sk-or-v1-your-key-here
OPENROUTER_DEFAULT_MODEL=deepseek/deepseek-v3.2-exp

# Risk Management (Testnet - More Relaxed)
STARTING_CAPITAL_CHF=10000.00
CIRCUIT_BREAKER_THRESHOLD_PCT=10.0
MAX_POSITION_SIZE_PCT=20.0
MIN_LEVERAGE=5
MAX_LEVERAGE=20

# LLM Cost Limits
LLM_DAILY_COST_LIMIT=10.00
LLM_MONTHLY_COST_LIMIT=200.00

# Monitoring (Optional - Set to false to save resources on Mac)
ENABLE_MONITORING=false
```

### Step 4: Create Required Files

```bash
# Create init-db.sql for database initialization
cat > init-db.sql << 'EOF'
-- Initialize trading database
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create schema
CREATE SCHEMA IF NOT EXISTS trading;

-- Grant permissions
GRANT ALL PRIVILEGES ON SCHEMA trading TO trader;
EOF

# Create docker network (if not exists)
docker network create trader-network 2>/dev/null || true
```

### Step 5: Build Docker Images

```bash
# Build the images
docker-compose build

# Expected output:
# [+] Building 120.5s (25/25) FINISHED
# => [trader internal] load build definition
# => => transferring dockerfile: 2.10kB
# ...
```

This may take 5-10 minutes on first run.

### Step 6: Start Testnet Environment

```bash
# Start all services (without monitoring)
docker-compose up -d

# Check status
docker-compose ps

# Expected output:
# NAME                    STATUS    PORTS
# trader-app              Up        0.0.0.0:8000->8000/tcp
# trader-postgres         Up        0.0.0.0:5432->5432/tcp
# trader-redis            Up        0.0.0.0:6379->6379/tcp
# trader-celery-worker    Up
# trader-celery-beat      Up
```

### Step 7: Verify Testnet Connection

```bash
# Check logs
docker-compose logs -f trader

# You should see:
# INFO:     Started server process
# INFO:     Waiting for application startup.
# INFO:     Application startup complete.
# INFO:     Uvicorn running on http://0.0.0.0:8000

# Test health endpoint
curl http://localhost:8000/health

# Expected: {"status":"healthy","timestamp":"..."}

# Test Binance testnet connection
docker-compose exec trader python -c "
from workspace.features.testnet_integration import TestnetConfig, TestnetExchangeAdapter, ExchangeType
import asyncio

async def test():
    config = TestnetConfig.from_env(ExchangeType.BINANCE)
    adapter = TestnetExchangeAdapter(config)
    await adapter.initialize()
    balance = await adapter.get_balance()
    print(f'✅ Connected! USDT Balance: {balance[\"total\"].get(\"USDT\", 0)}')
    await adapter.close()

asyncio.run(test())
"
```

### Step 8: Access the System

```bash
# Open in browser:
open http://localhost:8000/docs  # API documentation

# View logs in real-time
docker-compose logs -f trader

# Stop system when done
docker-compose down
```

---

## Ubuntu Setup - Production Deployment

This section covers deploying the trading system on Ubuntu for production use.

### Step 1: Install Docker on Ubuntu

```bash
# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install dependencies
sudo apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Add Docker's official GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Set up stable repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Verify installation
sudo docker --version
sudo docker compose version
```

### Step 2: Install Docker Compose (standalone)

```bash
# Download Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.23.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

# Apply executable permissions
sudo chmod +x /usr/local/bin/docker-compose

# Verify
docker-compose --version
```

### Step 3: Configure Docker for Non-Root User

```bash
# Create docker group (if not exists)
sudo groupadd docker

# Add your user to docker group
sudo usermod -aG docker $USER

# Activate changes
newgrp docker

# Test without sudo
docker run hello-world
```

### Step 4: Clone Repository on Ubuntu

```bash
# Install git if not present
sudo apt-get install -y git

# Clone repository
cd ~
git clone https://github.com/derobiwan/trader.git
cd trader

# Checkout main branch
git checkout main
git pull origin main
```

### Step 5: Production Environment Configuration

```bash
# Navigate to deployment directory
cd deployment/docker

# Create production environment file
nano .env
```

**Production Configuration:**

```bash
# ============================================================================
# Docker Environment Configuration - PRODUCTION MODE
# ============================================================================

# Database Configuration (Use strong passwords!)
POSTGRES_DB=trader_production
POSTGRES_USER=trader_prod
POSTGRES_PASSWORD=$(openssl rand -base64 32)  # Generate strong password
POSTGRES_PORT=5432

# Redis Configuration
REDIS_PASSWORD=$(openssl rand -base64 32)  # Generate strong password
REDIS_PORT=6379

# Application Configuration
ENVIRONMENT=production
LOG_LEVEL=INFO
APP_PORT=8000

# Trading Configuration (PRODUCTION MODE)
PAPER_TRADING=false  # Set to true initially for testing
TRADING_ENABLED=false  # Enable only after thorough testing
BINANCE_TESTNET=false  # Production uses real Binance

# Binance Production API Keys
# ⚠️ CRITICAL: Use API keys with TRADING permissions enabled
# ⚠️ Whitelist your server IP on Binance
BINANCE_API_KEY=your_production_api_key
BINANCE_API_SECRET=your_production_api_secret

# OpenRouter LLM API
OPENROUTER_API_KEY=your_production_key
OPENROUTER_DEFAULT_MODEL=deepseek/deepseek-v3.2-exp

# Risk Management (Production - STRICT)
STARTING_CAPITAL_CHF=2627.00
CIRCUIT_BREAKER_THRESHOLD_PCT=7.0
MAX_POSITION_SIZE_PCT=10.0
MIN_LEVERAGE=5
MAX_LEVERAGE=40

# LLM Cost Limits
LLM_DAILY_COST_LIMIT=5.00
LLM_MONTHLY_COST_LIMIT=100.00

# Monitoring (Recommended for production)
ENABLE_MONITORING=true
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000
GRAFANA_PASSWORD=$(openssl rand -base64 16)
```

### Step 6: Set Up Firewall (Ubuntu)

```bash
# Configure UFW firewall
sudo ufw enable
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 8000/tcp  # Trading API
sudo ufw allow 3000/tcp  # Grafana (optional)
sudo ufw allow 9090/tcp  # Prometheus (optional)
sudo ufw status
```

### Step 7: Create Systemd Service (Production)

```bash
# Create systemd service file
sudo nano /etc/systemd/system/trader.service
```

**Service file content:**

```ini
[Unit]
Description=LLM Crypto Trading System
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/YOUR_USERNAME/trader/deployment/docker
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
User=YOUR_USERNAME
Group=docker

[Install]
WantedBy=multi-user.target
```

Replace `YOUR_USERNAME` with your actual username.

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable trader.service

# Start service
sudo systemctl start trader.service

# Check status
sudo systemctl status trader.service
```

### Step 8: Set Up Log Rotation (Production)

```bash
# Create logrotate configuration
sudo nano /etc/logrotate.d/trader
```

**Logrotate config:**

```
/home/YOUR_USERNAME/trader/deployment/docker/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 YOUR_USERNAME docker
    sharedscripts
    postrotate
        /usr/local/bin/docker-compose -f /home/YOUR_USERNAME/trader/deployment/docker/docker-compose.yml restart trader
    endscript
}
```

### Step 9: Production Health Monitoring

```bash
# Create health check script
cat > ~/trader/scripts/health_check.sh << 'EOF'
#!/bin/bash
# Health check script for trading system

HEALTH_URL="http://localhost:8000/health"
LOG_FILE="/var/log/trader/health.log"

# Check API health
response=$(curl -s -o /dev/null -w "%{http_code}" $HEALTH_URL)

if [ $response -eq 200 ]; then
    echo "$(date): ✅ System healthy" >> $LOG_FILE
else
    echo "$(date): ❌ System unhealthy (HTTP $response)" >> $LOG_FILE
    # Send alert (implement your notification method)
    # Example: mail -s "Trading System Alert" admin@example.com < $LOG_FILE
fi
EOF

chmod +x ~/trader/scripts/health_check.sh

# Add to crontab (check every 5 minutes)
(crontab -l 2>/dev/null; echo "*/5 * * * * ~/trader/scripts/health_check.sh") | crontab -
```

---

## Configuration

### Environment Variables Reference

| Variable | Mac/Testnet | Ubuntu/Prod | Description |
|----------|-------------|-------------|-------------|
| `ENVIRONMENT` | `testnet` | `production` | Runtime environment |
| `PAPER_TRADING` | `true` | `false` | Use paper trading mode |
| `TRADING_ENABLED` | `false` | `false`* | Enable live trading |
| `BINANCE_TESTNET` | `true` | `false` | Use Binance testnet |
| `LOG_LEVEL` | `INFO` | `INFO` | Logging verbosity |
| `STARTING_CAPITAL_CHF` | `10000` | `2627.00` | Initial capital |

*Enable only after thorough testing!

### Security Best Practices

**For Mac (Testnet):**
- Use separate API keys for testnet
- Never use production keys on Mac
- Keep testnet funds minimal

**For Ubuntu (Production):**
- Use strong, unique passwords (32+ characters)
- Enable firewall (UFW)
- Whitelist server IP on Binance
- Use API keys with minimal required permissions
- Enable 2FA on all exchange accounts
- Regularly rotate API keys
- Monitor logs for suspicious activity

---

## Running the System

### Starting the System

**Mac (Testnet):**
```bash
cd ~/Documents/GitProjects/personal/trader/deployment/docker

# Start all services
docker-compose up -d

# Start with monitoring (optional)
docker-compose --profile monitoring up -d
```

**Ubuntu (Production):**
```bash
# Via systemd (recommended)
sudo systemctl start trader

# Or manually
cd ~/trader/deployment/docker
docker-compose up -d
```

### Stopping the System

**Mac:**
```bash
# Stop all services
docker-compose down

# Stop and remove volumes (⚠️ deletes data)
docker-compose down -v
```

**Ubuntu:**
```bash
# Via systemd
sudo systemctl stop trader

# Or manually
cd ~/trader/deployment/docker
docker-compose down
```

### Restarting Services

```bash
# Restart specific service
docker-compose restart trader

# Restart all services
docker-compose restart

# Or via systemd (Ubuntu)
sudo systemctl restart trader
```

---

## Monitoring & Logs

### Viewing Logs

**Real-time logs:**
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f trader
docker-compose logs -f postgres
docker-compose logs -f redis

# Last 100 lines
docker-compose logs --tail=100 trader
```

### Accessing Grafana (if monitoring enabled)

```bash
# Open Grafana
# Mac: http://localhost:3000
# Ubuntu: http://your-server-ip:3000

# Default credentials:
# Username: admin
# Password: (from .env GRAFANA_PASSWORD)
```

### System Metrics

```bash
# Check container stats
docker stats

# Check disk usage
docker system df

# Clean up unused resources
docker system prune -a
```

### Database Access

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U trader -d trader_testnet

# Run SQL queries
\dt  # List tables
SELECT * FROM trades LIMIT 10;
\q   # Quit
```

### Redis Access

```bash
# Connect to Redis
docker-compose exec redis redis-cli -a YOUR_REDIS_PASSWORD

# Check keys
KEYS *

# Get value
GET some_key

# Exit
quit
```

---

## Troubleshooting

### Common Issues

#### 1. Port Already in Use

**Error:**
```
Error: Bind for 0.0.0.0:8000 failed: port is already allocated
```

**Solution:**
```bash
# Find process using the port
sudo lsof -i :8000

# Kill the process
kill -9 PID

# Or change port in .env
APP_PORT=8001
```

#### 2. Database Connection Failed

**Error:**
```
ERROR: connection to server failed: FATAL: password authentication failed
```

**Solution:**
```bash
# Verify credentials in .env
cat .env | grep POSTGRES

# Restart database
docker-compose restart postgres

# Check database logs
docker-compose logs postgres
```

#### 3. Out of Memory

**Error:**
```
Container killed: Out of memory
```

**Solution:**
```bash
# Check memory usage
docker stats

# Increase Docker memory limit (Mac):
# Docker Desktop → Preferences → Resources → Memory

# Ubuntu: Add swap space
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

#### 4. Binance API Connection Failed

**Error:**
```
ERROR: Failed to connect to Binance API: Invalid API key
```

**Solution:**
```bash
# Verify API keys in .env
cat .env | grep BINANCE

# Test connection manually
docker-compose exec trader python -c "
from workspace.features.testnet_integration import TestnetConfig
import os
print('API Key:', os.getenv('BINANCE_TESTNET_API_KEY')[:10] + '...')
"

# Check Binance API status
curl https://api.binance.com/api/v3/ping
```

#### 5. Container Won't Start

```bash
# Check container status
docker-compose ps

# View error logs
docker-compose logs trader

# Rebuild container
docker-compose build --no-cache trader
docker-compose up -d trader
```

### Debug Mode

```bash
# Run container in debug mode
docker-compose run --rm trader /bin/bash

# Inside container:
python -c "from workspace.features.testnet_integration import TestnetConfig; print(TestnetConfig.from_env())"
```

### Complete System Reset

**⚠️ WARNING: This deletes all data!**

```bash
# Stop all containers
docker-compose down -v

# Remove all images
docker-compose down --rmi all

# Clean Docker system
docker system prune -a --volumes -f

# Rebuild
docker-compose build
docker-compose up -d
```

---

## Maintenance

### Regular Maintenance Tasks

**Daily:**
- Check system health: `curl http://localhost:8000/health`
- Review logs for errors: `docker-compose logs --tail=100 trader`
- Monitor disk space: `df -h`

**Weekly:**
- Check Docker resource usage: `docker stats`
- Review trading performance
- Backup database (see below)
- Update images: `docker-compose pull`

**Monthly:**
- Rotate API keys
- Review and clean logs
- Update Docker images
- Security audit

### Backup & Restore

**Backup Database:**
```bash
# Create backup directory
mkdir -p ~/trader/backups

# Backup PostgreSQL
docker-compose exec -T postgres pg_dump -U trader trader_production > ~/trader/backups/trader_$(date +%Y%m%d_%H%M%S).sql

# Compress backup
gzip ~/trader/backups/trader_*.sql
```

**Restore Database:**
```bash
# Decompress backup
gunzip ~/trader/backups/trader_YYYYMMDD_HHMMSS.sql.gz

# Restore
docker-compose exec -T postgres psql -U trader trader_production < ~/trader/backups/trader_YYYYMMDD_HHMMSS.sql
```

**Automated Backups (Ubuntu):**
```bash
# Create backup script
cat > ~/trader/scripts/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR=~/trader/backups
DATE=$(date +%Y%m%d_%H%M%S)
cd ~/trader/deployment/docker
docker-compose exec -T postgres pg_dump -U trader trader_production | gzip > $BACKUP_DIR/trader_$DATE.sql.gz
# Keep only last 30 days
find $BACKUP_DIR -name "trader_*.sql.gz" -mtime +30 -delete
EOF

chmod +x ~/trader/scripts/backup.sh

# Add to crontab (daily at 2 AM)
(crontab -l 2>/dev/null; echo "0 2 * * * ~/trader/scripts/backup.sh") | crontab -
```

### Updating the System

```bash
# Pull latest code
cd ~/trader  # or ~/Documents/GitProjects/personal/trader
git pull origin main

# Rebuild images
cd deployment/docker
docker-compose build

# Restart services
docker-compose down
docker-compose up -d

# Verify
docker-compose ps
docker-compose logs -f trader
```

---

## Quick Reference

### Essential Commands

```bash
# Status
docker-compose ps
docker-compose logs -f
curl http://localhost:8000/health

# Start/Stop
docker-compose up -d
docker-compose down
docker-compose restart

# Monitoring
docker stats
docker system df
docker-compose logs --tail=100 trader

# Database
docker-compose exec postgres psql -U trader -d trader_production
docker-compose exec redis redis-cli -a PASSWORD

# Maintenance
docker-compose pull
docker-compose build --no-cache
docker system prune -a
```

### File Locations

**Mac:**
- Repository: `~/Documents/GitProjects/personal/trader`
- Docker configs: `~/Documents/GitProjects/personal/trader/deployment/docker`
- Logs: `~/Documents/GitProjects/personal/trader/deployment/docker/logs`

**Ubuntu:**
- Repository: `~/trader`
- Docker configs: `~/trader/deployment/docker`
- Logs: `~/trader/deployment/docker/logs`
- Backups: `~/trader/backups`
- Systemd service: `/etc/systemd/system/trader.service`

---

## Next Steps

### After Initial Setup (Mac Testnet)

1. **Test Binance Connection:**
   ```bash
   docker-compose exec trader python scripts/test_testnet_connection.py
   ```

2. **Run Integration Tests:**
   ```bash
   docker-compose exec trader pytest workspace/tests/integration/testnet/ -v
   ```

3. **Monitor First Trades:**
   ```bash
   docker-compose logs -f trader | grep "TRADE"
   ```

### Before Production (Ubuntu)

1. **Run Full Test Suite:**
   ```bash
   docker-compose exec trader pytest workspace/tests/ -v --cov
   ```

2. **Paper Trading Test (24-48 hours):**
   ```
   - Set PAPER_TRADING=true
   - Set TRADING_ENABLED=true
   - Monitor for 24-48 hours
   - Verify no errors
   ```

3. **Enable Live Trading:**
   ```
   - Set PAPER_TRADING=false
   - Keep TRADING_ENABLED=false
   - Review all logs
   - Enable TRADING_ENABLED=true
   - Monitor closely for first 24 hours
   ```

---

**Last Updated:** 2025-10-31
**Author:** Documentation Curator
**Version:** 1.0.0
