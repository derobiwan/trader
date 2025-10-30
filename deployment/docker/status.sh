#!/bin/bash
##
## Status Check for Docker Deployment
##

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info() { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo ""
info "📊 LLM Crypto Trading System Status"
info "═══════════════════════════════════════════"
echo ""

# Check if any containers are running
if ! docker-compose ps | grep -q "Up"; then
    error "System is not running"
    echo ""
    echo "Start the system with: ./start.sh"
    echo ""
    exit 1
fi

# Show container status
info "Container Status:"
echo ""
docker-compose ps

echo ""
info "═══════════════════════════════════════════"
info "Resource Usage:"
info "═══════════════════════════════════════════"
echo ""

# Show resource usage
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" \
    $(docker-compose ps -q) 2>/dev/null || echo "Unable to fetch stats"

echo ""
info "═══════════════════════════════════════════"
info "Health Checks:"
info "═══════════════════════════════════════════"
echo ""

# Check API health
if curl -s -f http://localhost:8000/health > /dev/null 2>&1; then
    info "✅ API is healthy"
else
    warn "⚠️  API health check failed"
fi

# Check PostgreSQL
if docker-compose exec -T postgres pg_isready -U trader > /dev/null 2>&1; then
    info "✅ PostgreSQL is ready"
else
    warn "⚠️  PostgreSQL is not ready"
fi

# Check Redis
if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
    info "✅ Redis is responding"
else
    warn "⚠️  Redis is not responding"
fi

echo ""
info "═══════════════════════════════════════════"
info "Trading Status:"
info "═══════════════════════════════════════════"
echo ""

# Check trading configuration
PAPER_TRADING=$(grep "^PAPER_TRADING=" .env | cut -d'=' -f2)
TRADING_ENABLED=$(grep "^TRADING_ENABLED=" .env | cut -d'=' -f2)

echo "  Paper Trading:   $PAPER_TRADING"
echo "  Trading Enabled: $TRADING_ENABLED"

if [ "$PAPER_TRADING" = "true" ]; then
    info "  Mode: PAPER TRADING (Safe)"
else
    if [ "$TRADING_ENABLED" = "true" ]; then
        warn "  Mode: LIVE TRADING (Active)"
    else
        info "  Mode: Trading Disabled"
    fi
fi

echo ""
info "═══════════════════════════════════════════"
echo ""
