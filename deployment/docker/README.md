# Docker Deployment for LLM Crypto Trading System

Run the complete trading system on your home Ubuntu server using Docker. **No cloud costs!**

## 🎯 Why Docker on Home Server?

- **💰 Zero Cloud Costs**: No monthly AWS/GCP bills
- **🔒 Full Control**: Your data stays on your hardware
- **⚡ Simple Setup**: One command to deploy everything
- **🔄 Easy Updates**: Pull and restart to update
- **📊 Complete Stack**: App + Database + Redis + Monitoring

## 📋 Prerequisites

### Hardware Requirements

**Minimum**:
- CPU: 2 cores
- RAM: 4 GB
- Storage: 20 GB free space
- Network: Stable internet connection

**Recommended**:
- CPU: 4 cores
- RAM: 8 GB
- Storage: 50 GB free space (for logs and data)
- Network: Stable connection with low latency

### Software Requirements

- **Ubuntu 20.04+** (or any Linux with Docker support)
- **Docker** 20.10+
- **Docker Compose** 2.0+

## 🚀 Quick Start

### 1. Install Docker

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add your user to docker group
sudo usermod -aG docker $USER

# Apply group changes
newgrp docker

# Verify installation
docker --version
docker-compose --version
```

### 2. Clone Repository

```bash
cd ~
git clone https://github.com/YOUR_USERNAME/trader.git
cd trader/deployment/docker
```

### 3. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit configuration (IMPORTANT!)
nano .env
```

**Required Configuration**:

1. **Database Passwords**:
   ```bash
   POSTGRES_PASSWORD=your_secure_password_here
   REDIS_PASSWORD=your_secure_redis_password
   ```

2. **Exchange API Keys** (Get from Binance):
   ```bash
   BINANCE_API_KEY=your_api_key
   BINANCE_API_SECRET=your_api_secret
   BINANCE_TESTNET=true  # Use testnet initially!
   ```

3. **LLM API Key** (Choose one):
   ```bash
   # Option 1: OpenRouter (Recommended - flexible)
   OPENROUTER_API_KEY=your_key

   # Option 2: OpenAI
   OPENAI_API_KEY=your_key

   # Option 3: Anthropic
   ANTHROPIC_API_KEY=your_key
   ```

### 4. Run Setup

```bash
# Make scripts executable
chmod +x *.sh

# Run setup (installs and configures everything)
./setup.sh
```

This will:
- ✅ Check prerequisites
- ✅ Validate configuration
- ✅ Build Docker images
- ✅ Initialize database
- ✅ Create data directories

### 5. Start Trading System

```bash
./start.sh
```

System will start in **PAPER TRADING MODE** (safe by default).

### 6. Verify Installation

```bash
# Check status
./status.sh

# View logs
./logs.sh

# Check API
curl http://localhost:8000/health
```

Visit: **http://localhost:8000/docs** for API documentation

## 📊 System Architecture

```
┌─────────────────────────────────────────────────┐
│         Your Ubuntu Server (Home)               │
│                                                  │
│  ┌────────────┐  ┌──────────┐  ┌────────────┐ │
│  │ PostgreSQL │  │  Redis   │  │   Trader   │ │
│  │  Database  │  │  Cache   │  │    App     │ │
│  └────────────┘  └──────────┘  └────────────┘ │
│         │              │              │         │
│  ┌────────────┐  ┌──────────┐  ┌────────────┐ │
│  │   Celery   │  │  Celery  │  │Prometheus │ │
│  │   Worker   │  │   Beat   │  │(optional) │ │
│  └────────────┘  └──────────┘  └────────────┘ │
│                                                  │
│  Volumes:                                        │
│  - postgres_data (persistent database)          │
│  - redis_data (cache)                           │
│  - ./logs (application logs)                    │
│  - ./data (trading data)                        │
└─────────────────────────────────────────────────┘
                     │
                     ▼
              Internet (APIs)
     ┌──────────────────────────────┐
     │ Binance  │ LLM API  │ Others │
     └──────────────────────────────┘
```

## 🔧 Management Scripts

### Start/Stop/Restart

```bash
# Start system
./start.sh

# Stop system
./stop.sh

# Restart (after config changes)
./restart.sh
```

### Monitoring

```bash
# Check status
./status.sh

# View logs (all services)
./logs.sh

# View specific service logs
./logs.sh trader           # Trading application
./logs.sh postgres         # Database
./logs.sh celery-worker    # Background tasks

# Follow logs in real-time
docker-compose logs -f trader
```

### Maintenance

```bash
# Update to latest code
cd ~/trader
git pull
cd deployment/docker
docker-compose build
./restart.sh

# Database backup
docker exec trader-postgres pg_dump -U trader trader > backup_$(date +%Y%m%d).sql

# Database restore
cat backup_20241029.sql | docker exec -i trader-postgres psql -U trader -d trader

# Clean up old logs
find logs/ -name "*.log" -mtime +30 -delete

# View disk usage
docker system df
```

## 📈 Enabling Live Trading

**⚠️ IMPORTANT**: Only enable after 7 days of validated paper trading!

### Validation Checklist

Before enabling live trading, verify:

- [ ] System ran for 7+ days without crashes
- [ ] No critical errors in logs
- [ ] Paper trading shows positive performance
- [ ] Risk limits working correctly (check logs)
- [ ] Stop losses triggered appropriately
- [ ] Position sizing within limits
- [ ] API rate limits not exceeded
- [ ] Database backups configured

### Enable Live Trading

```bash
# 1. Edit configuration
nano .env

# 2. Change these settings:
PAPER_TRADING=false
TRADING_ENABLED=true

# 3. Restart system
./restart.sh

# 4. Monitor closely!
./logs.sh
```

## 🔐 Security Best Practices

### 1. Secure Your API Keys

```bash
# Set proper permissions on .env
chmod 600 .env

# Never commit .env to git
# (already in .gitignore)
```

### 2. Firewall Configuration

```bash
# Install UFW (Ubuntu Firewall)
sudo apt-get install ufw

# Allow SSH (important!)
sudo ufw allow 22/tcp

# Deny external access to services
sudo ufw deny 5432  # PostgreSQL
sudo ufw deny 6379  # Redis
sudo ufw deny 8000  # API (unless you need external access)

# Enable firewall
sudo ufw enable
```

### 3. Use Testnet First

Always start with exchange testnets:
```bash
BINANCE_TESTNET=true
BYBIT_TESTNET=true
```

### 4. Set Conservative Limits

```bash
# Start with small positions
MAX_POSITION_SIZE=0.05  # 5% per position
MAX_TOTAL_EXPOSURE=0.50  # 50% total
DAILY_LOSS_LIMIT=-0.05  # -5% circuit breaker
```

### 5. Enable Notifications

```bash
# Telegram (recommended)
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id

# Email
SMTP_HOST=smtp.gmail.com
SMTP_USER=your_email@gmail.com
ALERT_EMAIL=your_alert@gmail.com
```

## 💰 Cost Comparison

### Docker on Home Server

**Monthly Cost**:
- Electricity: ~$5-10 (24/7 running)
- Internet: $0 (existing connection)
- **Total: ~$10/month**

**One-time Cost**:
- Server hardware: $0 (using existing PC/server)
- OR
- Raspberry Pi 4 (8GB): ~$75 (one-time)
- OR
- Used mini PC: ~$150-300 (one-time)

### Cloud Comparison

| Option | Monthly Cost | Annual Cost | Savings vs Cloud |
|--------|--------------|-------------|------------------|
| **Home Docker** | $10 | $120 | **Baseline** |
| GCP GKE Staging | $140 | $1,680 | **92% more** |
| AWS EKS Staging | $210 | $2,520 | **95% more** |
| GCP GKE Production | $290 | $3,480 | **96% more** |
| AWS EKS Production | $370 | $4,440 | **97% more** |

**Savings**: **$2,400-4,320/year** vs cloud!

## 🐛 Troubleshooting

### Container Won't Start

```bash
# Check logs
docker-compose logs trader

# Common issues:
# 1. Missing .env file
cp .env.example .env

# 2. Port conflicts
# Edit docker-compose.yml and change ports
```

### Database Connection Error

```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Restart PostgreSQL
docker-compose restart postgres

# Check connection
docker exec -it trader-postgres psql -U trader -d trader
```

### Out of Disk Space

```bash
# Check disk usage
df -h
docker system df

# Clean up
docker system prune -a
docker volume prune
find logs/ -name "*.log" -mtime +7 -delete
```

### High Memory Usage

```bash
# Check resource usage
docker stats

# Reduce Celery workers
# Edit docker-compose.yml:
command: celery -A workspace.celery_app worker --concurrency=1
```

### API Key Errors

```bash
# Verify API keys in .env
cat .env | grep API_KEY

# Test API keys
docker-compose run --rm trader python -c "
import os
print('Binance:', bool(os.getenv('BINANCE_API_KEY')))
print('LLM:', bool(os.getenv('OPENROUTER_API_KEY') or os.getenv('OPENAI_API_KEY')))
"
```

## 📊 Monitoring (Optional)

Enable Prometheus and Grafana for dashboards:

```bash
# Start with monitoring
docker-compose --profile monitoring up -d

# Access dashboards
Prometheus: http://localhost:9090
Grafana: http://localhost:3000
```

## 🔄 Updates and Maintenance

### Update to Latest Version

```bash
cd ~/trader
git pull origin main
cd deployment/docker
docker-compose build --no-cache
./restart.sh
```

### Scheduled Maintenance

Add to crontab:

```bash
# Edit crontab
crontab -e

# Add daily backup at 3 AM
0 3 * * * cd ~/trader/deployment/docker && docker exec trader-postgres pg_dump -U trader trader > backup_$(date +\%Y\%m\%d).sql

# Add weekly log cleanup
0 4 * * 0 find ~/trader/deployment/docker/logs -name "*.log" -mtime +30 -delete
```

## 📚 Additional Resources

- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Docker Documentation**: https://docs.docker.com/
- **Project Repository**: https://github.com/YOUR_USERNAME/trader

## ⚠️ Important Notes

### Paper Trading Period

**Required**: Run in paper trading mode for at least 7 days before going live.

**What to Monitor**:
- System stability (no crashes)
- Performance metrics (win rate, Sharpe ratio)
- Risk management (position limits respected)
- Error handling (no unhandled exceptions)
- API rate limits (no throttling)

### Risk Management

**Always Start Conservative**:
- Small position sizes (5% max per position)
- Low leverage (1-3x maximum)
- Tight stop losses (2-3%)
- Limited total exposure (50%)

**Scale Up Gradually**:
- Increase position sizes after 2 weeks of profitable trading
- Monitor daily P&L closely
- Never exceed configured risk limits

### Backup Strategy

**Critical Backups**:
1. **Database**: Daily automated backups
2. **Configuration**: Keep .env backup (encrypted!)
3. **Logs**: Archive monthly for analysis

## 🆘 Support

### Getting Help

1. Check logs: `./logs.sh`
2. Check status: `./status.sh`
3. Review troubleshooting section above
4. Open GitHub issue with logs

### Common Issues

Most issues are due to:
- Missing or incorrect API keys
- Insufficient system resources
- Network connectivity problems
- Exchange API rate limits

---

## Quick Reference Card

```bash
# Setup
./setup.sh              # First-time setup

# Daily Operations
./start.sh              # Start system
./stop.sh               # Stop system
./restart.sh            # Restart after changes
./status.sh             # Check health
./logs.sh               # View logs

# Monitoring
docker-compose ps       # Container status
docker stats            # Resource usage
./logs.sh trader        # Application logs

# Maintenance
git pull && docker-compose build && ./restart.sh  # Update
docker exec trader-postgres pg_dump -U trader trader > backup.sql  # Backup
```

---

**Created**: 2025-10-29
**Status**: Production Ready
**Cost**: ~$10/month (vs $140-370/month cloud)
**Deployment Time**: 10 minutes
