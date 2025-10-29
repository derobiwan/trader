.PHONY: help install install-dev install-prod install-test verify clean test lint format security check docker-build docker-run

# Default target
.DEFAULT_GOAL := help

# Variables
PYTHON := python3
PIP := $(PYTHON) -m pip
PYTEST := $(PYTHON) -m pytest
BLACK := $(PYTHON) -m black
ISORT := $(PYTHON) -m isort
FLAKE8 := $(PYTHON) -m flake8
MYPY := $(PYTHON) -m mypy
BANDIT := $(PYTHON) -m bandit
SAFETY := $(PYTHON) -m safety

# Directories
SRC_DIR := workspace
TEST_DIR := tests
DOCS_DIR := docs

# ============================================================================
# Help
# ============================================================================

help: ## Show this help message
	@echo "LLM Crypto Trading System - Make Commands"
	@echo "=========================================="
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""

# ============================================================================
# Installation
# ============================================================================

install: ## Install all dependencies (development + production)
	@echo "Installing all dependencies..."
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -r requirements.txt
	@echo "✓ Installation complete!"
	@$(MAKE) verify

install-dev: ## Install development dependencies
	@echo "Installing development dependencies..."
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -r requirements-dev.txt
	@echo "✓ Development installation complete!"
	@$(MAKE) verify

install-prod: ## Install production dependencies only
	@echo "Installing production dependencies..."
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -r requirements-prod.txt
	@echo "✓ Production installation complete!"
	@$(MAKE) verify

install-test: ## Install testing dependencies
	@echo "Installing testing dependencies..."
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -r requirements-test.txt
	@echo "✓ Testing installation complete!"

verify: ## Verify all dependencies are installed correctly
	@echo "Verifying dependencies..."
	@$(PYTHON) scripts/verify-dependencies.py
	@echo ""

# ============================================================================
# Development
# ============================================================================

format: ## Format code with black and isort
	@echo "Formatting code..."
	$(BLACK) $(SRC_DIR) $(TEST_DIR) scripts/
	$(ISORT) $(SRC_DIR) $(TEST_DIR) scripts/
	@echo "✓ Code formatted!"

lint: ## Run linting checks (flake8, mypy)
	@echo "Running linting checks..."
	$(FLAKE8) $(SRC_DIR) $(TEST_DIR) scripts/
	$(MYPY) $(SRC_DIR) --ignore-missing-imports
	@echo "✓ Linting complete!"

check: format lint ## Format code and run linting

security: ## Run security checks (bandit, safety)
	@echo "Running security checks..."
	$(BANDIT) -r $(SRC_DIR) -f json -o reports/bandit-report.json || true
	$(SAFETY) check --json > reports/safety-report.json || true
	@echo "✓ Security checks complete! Check reports/ directory."

# ============================================================================
# Testing
# ============================================================================

test: ## Run all tests
	@echo "Running tests..."
	$(PYTEST) $(TEST_DIR) -v --cov=$(SRC_DIR) --cov-report=html --cov-report=term

test-unit: ## Run unit tests only
	@echo "Running unit tests..."
	$(PYTEST) $(TEST_DIR) -v -m "not integration"

test-integration: ## Run integration tests only
	@echo "Running integration tests..."
	$(PYTEST) $(TEST_DIR) -v -m integration

test-coverage: ## Run tests with coverage report
	@echo "Running tests with coverage..."
	$(PYTEST) $(TEST_DIR) -v --cov=$(SRC_DIR) --cov-report=html --cov-report=term-missing
	@echo "✓ Coverage report generated in htmlcov/"

test-fast: ## Run tests in parallel (fast)
	@echo "Running tests in parallel..."
	$(PYTEST) $(TEST_DIR) -n auto -v

# ============================================================================
# Cleaning
# ============================================================================

clean: ## Clean up generated files
	@echo "Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache .coverage htmlcov/ dist/ build/
	@echo "✓ Cleanup complete!"

clean-all: clean ## Deep clean including virtual environment
	@echo "Deep cleaning..."
	rm -rf venv/ .venv/
	@echo "✓ Deep cleanup complete!"

# ============================================================================
# Docker
# ============================================================================

docker-build: ## Build Docker image
	@echo "Building Docker image..."
	docker build -t llm-crypto-trading:latest .
	@echo "✓ Docker image built!"

docker-run: ## Run Docker container
	@echo "Running Docker container..."
	docker run -d \
		--name trading-bot \
		-p 8000:8000 \
		--env-file .env \
		llm-crypto-trading:latest
	@echo "✓ Container started! Access at http://localhost:8000"

docker-stop: ## Stop Docker container
	@echo "Stopping Docker container..."
	docker stop trading-bot
	docker rm trading-bot
	@echo "✓ Container stopped!"

docker-logs: ## Show Docker container logs
	docker logs -f trading-bot

# ============================================================================
# Database
# ============================================================================

db-migrate: ## Run database migrations
	@echo "Running database migrations..."
	alembic upgrade head
	@echo "✓ Migrations complete!"

db-rollback: ## Rollback last database migration
	@echo "Rolling back migration..."
	alembic downgrade -1
	@echo "✓ Rollback complete!"

db-revision: ## Create new database migration
	@echo "Creating new migration..."
	@read -p "Migration message: " msg; \
	alembic revision --autogenerate -m "$$msg"
	@echo "✓ Migration created!"

# ============================================================================
# Kubernetes
# ============================================================================

k8s-deploy: ## Deploy to Kubernetes
	@echo "Deploying to Kubernetes..."
	kubectl apply -f deployment/kubernetes/
	@echo "✓ Deployment complete!"

k8s-status: ## Check Kubernetes deployment status
	kubectl get pods -n crypto-trading
	kubectl get services -n crypto-trading

k8s-logs: ## Show Kubernetes pod logs
	kubectl logs -n crypto-trading -l app=trading-bot -f

k8s-delete: ## Delete Kubernetes deployment
	@echo "Deleting deployment..."
	kubectl delete -f deployment/kubernetes/
	@echo "✓ Deletion complete!"

# ============================================================================
# Development Server
# ============================================================================

run: ## Run development server
	@echo "Starting development server..."
	uvicorn main:app --reload --host 0.0.0.0 --port 8000

run-prod: ## Run production server
	@echo "Starting production server..."
	uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

# ============================================================================
# Documentation
# ============================================================================

docs: ## Build documentation
	@echo "Building documentation..."
	mkdocs build
	@echo "✓ Documentation built in site/"

docs-serve: ## Serve documentation locally
	@echo "Serving documentation at http://localhost:8000..."
	mkdocs serve

# ============================================================================
# CI/CD Helpers
# ============================================================================

ci-test: install-test test-coverage lint security ## Run full CI test suite
	@echo "✓ CI test suite complete!"

ci-build: ## Build for CI/CD
	@echo "Building for CI/CD..."
	$(MAKE) install-prod
	$(MAKE) docker-build
	@echo "✓ CI build complete!"

# ============================================================================
# Utilities
# ============================================================================

requirements-update: ## Update requirements files from pyproject.toml
	@echo "Updating requirements..."
	pip-compile requirements.in -o requirements.txt
	@echo "✓ Requirements updated!"

version: ## Show version information
	@echo "LLM Crypto Trading System"
	@echo "========================"
	@echo "Python version: $$($(PYTHON) --version)"
	@echo "pip version: $$($(PIP) --version)"
	@echo ""

env: ## Create virtual environment
	@echo "Creating virtual environment..."
	$(PYTHON) -m venv venv
	@echo "✓ Virtual environment created!"
	@echo "Activate with: source venv/bin/activate"

# ============================================================================
# Quick Start
# ============================================================================

setup: env install ## Quick setup (create venv and install dependencies)
	@echo ""
	@echo "✓ Setup complete!"
	@echo ""
	@echo "To activate the virtual environment, run:"
	@echo "  source venv/bin/activate"
	@echo ""
	@echo "Then you can use:"
	@echo "  make run        - Start development server"
	@echo "  make test       - Run tests"
	@echo "  make help       - Show all commands"
	@echo ""
