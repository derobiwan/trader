#!/bin/bash
##
## Setup Script for Docker Deployment
##
## This script sets up the LLM Crypto Trading System on your local Ubuntu server
##

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

info() { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }
step() { echo -e "${BLUE}[STEP]${NC} $1"; }

echo ""
info "🚀 LLM Crypto Trading System - Docker Setup"
info "═══════════════════════════════════════════"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    warn "Running as root. It's recommended to run as a regular user with Docker permissions."
    read -p "Continue anyway? (y/n): " continue_root
    if [ "$continue_root" != "y" ]; then
        exit 0
    fi
fi

# Check prerequisites
step "1. Checking prerequisites..."
echo ""

# Check Docker
if ! command -v docker &> /dev/null; then
    error "Docker is not installed"
    echo ""
    echo "Install Docker with:"
    echo "  curl -fsSL https://get.docker.com -o get-docker.sh"
    echo "  sudo sh get-docker.sh"
    echo "  sudo usermod -aG docker $USER"
    echo "  newgrp docker"
    exit 1
fi

# Check Docker Compose
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    error "Docker Compose is not installed"
    echo ""
    echo "Install Docker Compose with:"
    echo "  sudo apt-get update"
    echo "  sudo apt-get install docker-compose-plugin"
    exit 1
fi

# Check if docker daemon is running
if ! docker info &> /dev/null; then
    error "Docker daemon is not running"
    echo ""
    echo "Start Docker with:"
    echo "  sudo systemctl start docker"
    echo "  sudo systemctl enable docker"
    exit 1
fi

info "✅ Docker installed: $(docker --version)"
info "✅ Docker Compose installed"
info "✅ Docker daemon running"
echo ""

# Check .env file
step "2. Checking environment configuration..."
echo ""

if [ ! -f .env ]; then
    warn ".env file not found"
    info "Creating .env from template..."
    cp .env.example .env
    echo ""
    error "❌ IMPORTANT: You must edit .env file with your API keys!"
    echo ""
    echo "Required configurations:"
    echo "  1. Database passwords (POSTGRES_PASSWORD, REDIS_PASSWORD)"
    echo "  2. Exchange API keys (BINANCE_API_KEY, BINANCE_API_SECRET)"
    echo "  3. LLM API key (OPENROUTER_API_KEY or OPENAI_API_KEY)"
    echo ""
    echo "Edit the file now:"
    echo "  nano .env"
    echo ""
    echo "Then run this script again."
    exit 1
fi

info "✅ .env file found"

# Check if required variables are set
check_env_var() {
    local var_name=$1
    local var_value=$(grep "^${var_name}=" .env | cut -d'=' -f2-)
    if [ -z "$var_value" ] || [[ "$var_value" == *"your_"* ]] || [[ "$var_value" == *"_here"* ]]; then
        return 1
    fi
    return 0
}

missing_vars=()

if ! check_env_var "POSTGRES_PASSWORD"; then missing_vars+=("POSTGRES_PASSWORD"); fi
if ! check_env_var "REDIS_PASSWORD"; then missing_vars+=("REDIS_PASSWORD"); fi
if ! check_env_var "BINANCE_API_KEY"; then missing_vars+=("BINANCE_API_KEY"); fi
if ! check_env_var "OPENROUTER_API_KEY" && ! check_env_var "OPENAI_API_KEY"; then
    missing_vars+=("OPENROUTER_API_KEY or OPENAI_API_KEY")
fi

if [ ${#missing_vars[@]} -gt 0 ]; then
    error "Missing or incomplete configuration:"
    for var in "${missing_vars[@]}"; do
        echo "  - $var"
    done
    echo ""
    echo "Edit .env file:"
    echo "  nano .env"
    echo ""
    exit 1
fi

info "✅ Required environment variables configured"
echo ""

# Create directories
step "3. Creating data directories..."
echo ""

mkdir -p logs data

info "✅ Created logs/ directory"
info "✅ Created data/ directory"
echo ""

# Create init-db.sql if it doesn't exist
if [ ! -f init-db.sql ]; then
    cat > init-db.sql <<'EOF'
-- Initialize trading database
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create tables will be handled by Alembic migrations
EOF
    info "✅ Created init-db.sql"
fi
echo ""

# Build Docker images
step "4. Building Docker images..."
echo ""

info "This may take a few minutes on first run..."
docker-compose build --no-cache

info "✅ Docker images built successfully"
echo ""

# Pull required images
step "5. Pulling additional Docker images..."
echo ""

docker-compose pull postgres redis

info "✅ Images pulled successfully"
echo ""

# Create volumes
step "6. Creating Docker volumes..."
echo ""

docker volume create trader_postgres_data
docker volume create trader_redis_data

info "✅ Volumes created"
echo ""

# Initialize database
step "7. Initializing database..."
echo ""

info "Starting PostgreSQL temporarily..."
docker-compose up -d postgres

info "Waiting for PostgreSQL to be ready..."
sleep 10

info "Running database migrations..."
docker-compose run --rm trader alembic upgrade head

info "✅ Database initialized"
echo ""

# Stop temporary services
docker-compose down
echo ""

# Final instructions
echo ""
info "🎉 Setup complete!"
echo ""
info "═══════════════════════════════════════════"
info "Next steps:"
info "═══════════════════════════════════════════"
echo ""
echo "1. Start the system:"
echo "   ${GREEN}./start.sh${NC}"
echo ""
echo "2. Check status:"
echo "   ${GREEN}docker-compose ps${NC}"
echo ""
echo "3. View logs:"
echo "   ${GREEN}docker-compose logs -f trader${NC}"
echo ""
echo "4. Access the API:"
echo "   ${GREEN}http://localhost:8000/docs${NC}"
echo ""
info "═══════════════════════════════════════════"
info "⚠️  IMPORTANT: Trading is in PAPER MODE"
info "═══════════════════════════════════════════"
echo ""
echo "The system is configured for paper trading by default."
echo "Run the system for 7 days and validate performance before"
echo "enabling live trading."
echo ""
echo "To enable live trading later:"
echo "  1. Edit .env: Set TRADING_ENABLED=true"
echo "  2. Edit .env: Set PAPER_TRADING=false"
echo "  3. Restart: ./restart.sh"
echo ""
info "═══════════════════════════════════════════"
echo ""
