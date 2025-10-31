#!/bin/bash
#
# Quick Start Script for Mac - Testnet Trading System
# Usage: ./quick-start-mac.sh
#
# This script helps you set up the trading system on Mac for testnet testing
#

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}LLM Crypto Trading System - Mac Setup${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if Docker is installed and running
echo -e "${YELLOW}[1/7] Checking Docker...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed${NC}"
    echo "Please install Docker Desktop from: https://www.docker.com/products/docker-desktop"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo -e "${RED}❌ Docker is not running${NC}"
    echo "Please start Docker Desktop"
    exit 1
fi

echo -e "${GREEN}✅ Docker is installed and running${NC}"
echo ""

# Check if docker-compose is available
echo -e "${YELLOW}[2/7] Checking Docker Compose...${NC}"
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed${NC}"
    echo "Please install Docker Compose"
    exit 1
fi

echo -e "${GREEN}✅ Docker Compose is available${NC}"
echo ""

# Check if .env file exists
echo -e "${YELLOW}[3/7] Checking configuration...${NC}"
if [ ! -f .env ]; then
    echo -e "${YELLOW}📝 Creating .env from template...${NC}"
    cp .env.example .env
    echo -e "${RED}⚠️  IMPORTANT: Edit .env and add your API keys!${NC}"
    echo ""
    echo "Required:"
    echo "  - BINANCE_TESTNET_API_KEY"
    echo "  - BINANCE_TESTNET_API_SECRET"
    echo "  - OPENROUTER_API_KEY"
    echo "  - POSTGRES_PASSWORD"
    echo "  - REDIS_PASSWORD"
    echo ""
    echo -e "${YELLOW}Open .env now? (y/n)${NC}"
    read -r answer
    if [ "$answer" = "y" ]; then
        ${EDITOR:-nano} .env
    else
        echo "Please edit .env before continuing"
        exit 1
    fi
fi

echo -e "${GREEN}✅ Configuration file exists${NC}"
echo ""

# Build Docker images
echo -e "${YELLOW}[4/7] Building Docker images...${NC}"
echo "This may take 5-10 minutes on first run..."
docker-compose build
echo -e "${GREEN}✅ Docker images built${NC}"
echo ""

# Create necessary directories
echo -e "${YELLOW}[5/7] Creating directories...${NC}"
mkdir -p logs data
echo -e "${GREEN}✅ Directories created${NC}"
echo ""

# Start services
echo -e "${YELLOW}[6/7] Starting services...${NC}"
docker-compose up -d
echo -e "${GREEN}✅ Services started${NC}"
echo ""

# Wait for services to be healthy
echo -e "${YELLOW}[7/7] Waiting for services to be ready...${NC}"
sleep 10

# Check health
if curl -f http://localhost:8000/health &> /dev/null; then
    echo -e "${GREEN}✅ System is healthy!${NC}"
else
    echo -e "${RED}⚠️  System may not be fully ready yet${NC}"
    echo "Check logs with: docker-compose logs -f"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Next steps:"
echo ""
echo "1. Check system status:"
echo "   docker-compose ps"
echo ""
echo "2. View logs:"
echo "   docker-compose logs -f trader"
echo ""
echo "3. Test health:"
echo "   curl http://localhost:8000/health"
echo ""
echo "4. Access API docs:"
echo "   open http://localhost:8000/docs"
echo ""
echo "5. Stop system:"
echo "   docker-compose down"
echo ""
echo "For more information, see: ../../docs/DOCKER_SETUP_GUIDE.md"
echo ""
