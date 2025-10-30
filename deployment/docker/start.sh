#!/bin/bash
##
## Start Script for Docker Deployment
##

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info() { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

echo ""
info "🚀 Starting LLM Crypto Trading System..."
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "Error: .env file not found"
    echo "Run ./setup.sh first"
    exit 1
fi

# Start core services
info "Starting core services (Database, Redis, Application)..."
docker-compose up -d postgres redis trader celery-worker celery-beat

# Wait for services to be healthy
info "Waiting for services to be healthy..."
sleep 10

# Check health
info "Checking service health..."
docker-compose ps

echo ""
info "✅ System started successfully!"
echo ""
info "═══════════════════════════════════════════"
info "Access Points:"
info "═══════════════════════════════════════════"
echo ""
echo "  API Documentation: http://localhost:8000/docs"
echo "  API Health Check:  http://localhost:8000/health"
echo ""
info "═══════════════════════════════════════════"
info "Useful Commands:"
info "═══════════════════════════════════════════"
echo ""
echo "  View logs:      docker-compose logs -f trader"
echo "  Check status:   docker-compose ps"
echo "  Stop system:    ./stop.sh"
echo "  Restart:        ./restart.sh"
echo ""
info "═══════════════════════════════════════════"
echo ""

# Show if monitoring is available
if docker-compose ps | grep -q prometheus; then
    echo "  Prometheus:     http://localhost:9090"
    echo "  Grafana:        http://localhost:3000"
    echo ""
fi

warn "⚠️  Trading is in PAPER MODE by default"
echo "   Monitor performance for 7 days before enabling live trading"
echo ""
