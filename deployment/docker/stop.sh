#!/bin/bash
##
## Stop Script for Docker Deployment
##

set -e

GREEN='\033[0;32m'
NC='\033[0m'

info() { echo -e "${GREEN}[INFO]${NC} $1"; }

echo ""
info "🛑 Stopping LLM Crypto Trading System..."
echo ""

# Stop all services
docker-compose down

echo ""
info "✅ System stopped successfully!"
echo ""
info "To start again: ./start.sh"
echo ""
