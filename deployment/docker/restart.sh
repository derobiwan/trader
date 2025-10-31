#!/bin/bash
##
## Restart Script for Docker Deployment
##

set -e

GREEN='\033[0;32m'
NC='\033[0m'

info() { echo -e "${GREEN}[INFO]${NC} $1"; }

echo ""
info "🔄 Restarting LLM Crypto Trading System..."
echo ""

# Stop services
./stop.sh

# Wait a moment
sleep 2

# Start services
./start.sh
