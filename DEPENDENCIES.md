# Dependency Management Guide

This document explains the dependency management structure for the LLM Crypto Trading System.

## 📋 Requirements Files Overview

The project uses multiple requirements files for different environments and purposes:

| File | Purpose | Use Case |
|------|---------|----------|
| `requirements.txt` | **All dependencies** | Complete installation including dev tools |
| `requirements-prod.txt` | **Production only** | Minimal deps for Docker/Kubernetes |
| `requirements-dev.txt` | **Development** | Local development with debugging tools |
| `requirements-test.txt` | **Testing** | CI/CD test pipelines |

## 🚀 Installation Instructions

### Production Deployment

For Docker images and Kubernetes deployments:

```bash
pip install -r requirements-prod.txt
```

This installs only runtime dependencies, keeping the image size minimal.

### Development Environment

For local development with all tools:

```bash
# Option 1: Full installation
pip install -r requirements-dev.txt

# Option 2: Step-by-step
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Testing Only

For CI/CD pipelines or testing-focused environments:

```bash
pip install -r requirements-test.txt
```

### Quick Start (All Dependencies)

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install all dependencies
pip install -r requirements.txt
```

## 📦 Dependency Categories

### Core Framework
- **FastAPI**: REST API framework
- **Uvicorn**: ASGI server
- **Pydantic**: Data validation and settings management

### Trading System
- **ccxt**: Unified cryptocurrency exchange API
- **python-binance**: Binance-specific features
- **pandas-ta**: Technical analysis indicators

### LLM Integration
- **openai**: OpenRouter API client (OpenAI-compatible)
- **anthropic**: Claude API client (optional)
- **tiktoken**: Token counting for cost estimation

### Database & Caching
- **SQLAlchemy**: ORM and database toolkit
- **Alembic**: Database migrations
- **asyncpg**: Async PostgreSQL driver
- **redis**: Redis client for caching

### Task Queue
- **celery**: Distributed task queue
- **redis**: Message broker for Celery

### Monitoring & Logging
- **prometheus-client**: Metrics exposition
- **python-json-logger**: Structured logging

### Testing
- **pytest**: Testing framework
- **pytest-asyncio**: Async test support
- **pytest-cov**: Coverage reporting

### Code Quality
- **black**: Code formatting
- **flake8**: Linting
- **mypy**: Static type checking
- **bandit**: Security linting

## 🔒 Security Dependencies

The project includes several security-focused dependencies:

- **bandit**: Security vulnerability scanner for Python code
- **safety**: Checks dependencies for known security vulnerabilities
- **pip-audit**: Audits Python packages for vulnerabilities

Run security checks:

```bash
# Check code for security issues
bandit -r workspace/ -f json -o reports/bandit-report.json

# Check dependencies for vulnerabilities
safety check --json

# Audit packages
pip-audit --format json
```

## 🎯 Version Management

### Version Pinning Strategy

- **Production**: Use exact versions or narrow ranges for stability
- **Development**: Use minimum versions with `>=` for flexibility
- **Dependencies**: Pin transitive dependencies in `requirements.lock` (generated)

### Updating Dependencies

```bash
# Check for outdated packages
pip list --outdated

# Update a specific package
pip install --upgrade <package-name>

# Update requirements files
pip freeze > requirements.lock
```

### Creating Lock Files

For reproducible builds, generate lock files:

```bash
# Generate production lock file
pip install -r requirements-prod.txt
pip freeze > requirements-prod.lock

# Generate development lock file
pip install -r requirements-dev.txt
pip freeze > requirements-dev.lock
```

## 🐳 Docker Usage

The Dockerfile uses multi-stage builds to minimize image size:

```dockerfile
# Build stage
FROM python:3.12-slim as builder
COPY requirements-prod.txt .
RUN pip install --user -r requirements-prod.txt

# Runtime stage
FROM python:3.12-slim
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH
```

## 🔍 Dependency Verification

### Verifying Installation

```bash
# Verify all required packages are installed
pip check

# List installed packages
pip list

# Show package details
pip show <package-name>
```

### Testing Dependencies

Test that all imports work:

```python
# tests/test_dependencies.py
def test_core_dependencies():
    """Verify core dependencies are importable."""
    import fastapi
    import uvicorn
    import pydantic
    assert fastapi
    assert uvicorn
    assert pydantic

def test_trading_dependencies():
    """Verify trading dependencies are importable."""
    import ccxt
    import pandas
    import numpy
    assert ccxt
    assert pandas
    assert numpy

def test_llm_dependencies():
    """Verify LLM dependencies are importable."""
    import openai
    import tiktoken
    assert openai
    assert tiktoken
```

## 📊 Dependency Graph

Key dependency relationships:

```
Trading System
├── FastAPI (Web Framework)
│   ├── Pydantic (Validation)
│   └── Uvicorn (Server)
├── ccxt (Exchange APIs)
│   └── requests (HTTP)
├── SQLAlchemy (Database)
│   └── asyncpg (PostgreSQL)
├── Celery (Task Queue)
│   └── redis (Broker)
├── OpenAI (LLM API)
│   └── httpx (HTTP Client)
└── Prometheus Client (Metrics)
```

## ⚡ Performance Considerations

### Installation Speed

Use pip caching to speed up installations:

```bash
# Enable pip cache
export PIP_CACHE_DIR=$HOME/.pip/cache

# Use binary wheels when available
pip install --prefer-binary -r requirements-prod.txt
```

### Minimal Installation

For minimal Docker images, consider:

```bash
# Install without dev dependencies
pip install --no-dev -r requirements-prod.txt

# Install without cache
pip install --no-cache-dir -r requirements-prod.txt
```

## 🔧 Troubleshooting

### Common Issues

#### 1. Conflicting Dependencies

```bash
# Resolve conflicts
pip install pip-tools
pip-compile requirements.txt
```

#### 2. Platform-Specific Issues

Some packages require system libraries:

```bash
# Ubuntu/Debian
apt-get install -y \
    gcc \
    g++ \
    postgresql-client \
    libpq-dev

# macOS
brew install postgresql
```

#### 3. Slow Installation

```bash
# Use faster dependency resolver
pip install --use-feature=fast-deps -r requirements.txt

# Parallel downloads
pip install --no-cache-dir --upgrade pip setuptools wheel
```

### Import Errors

If you encounter import errors:

1. Verify virtual environment is activated
2. Reinstall dependencies: `pip install --force-reinstall -r requirements.txt`
3. Clear pip cache: `pip cache purge`

## 📝 Dependency Audit

Regular dependency maintenance tasks:

### Weekly
- [ ] Check for security vulnerabilities: `safety check`
- [ ] Review dependency updates: `pip list --outdated`

### Monthly
- [ ] Update patch versions: `pip install -U <package>`
- [ ] Run full test suite after updates
- [ ] Audit dependencies: `pip-audit`

### Quarterly
- [ ] Review all dependencies for necessity
- [ ] Update major/minor versions
- [ ] Update lock files
- [ ] Update this documentation

## 🔗 Related Files

- `pyproject.toml` - Python project configuration
- `setup.py` - Package installation script
- `Dockerfile` - Docker build configuration
- `.github/workflows/ci-cd.yml` - CI/CD pipeline using test requirements

## 📚 Additional Resources

- [pip documentation](https://pip.pypa.io/)
- [Python Packaging Guide](https://packaging.python.org/)
- [Dependency Management Best Practices](https://packaging.python.org/guides/tool-recommendations/)
- [Security Considerations](https://packaging.python.org/guides/analyzing-pypi-package-downloads/)

## 🆘 Support

For dependency-related issues:

1. Check this documentation
2. Review GitHub Actions CI/CD logs
3. Run `pip check` to verify installation
4. Create an issue with:
   - Python version: `python --version`
   - pip version: `pip --version`
   - OS and version
   - Full error message

---

**Last Updated**: 2025-10-29
**Version**: 1.0.0
**Maintainers**: Development Team
