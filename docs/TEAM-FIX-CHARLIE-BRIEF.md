# Team Fix-Charlie: Mock & Integration Specialist Brief

## Mission
Fix all mock setup issues, database fixtures, and integration test failures.

## Assigned Agent Type
Validation Engineer with integration testing and mock expertise

## Failure Analysis

### Primary Issues
1. Database session mocks not properly configured
2. API client fixtures missing or misconfigured
3. Import errors and circular dependencies
4. External service mocks (exchanges, LLM providers)
5. Test isolation failures

### Common Error Patterns
```python
# Import errors
ImportError: cannot import name 'app' from 'workspace.api'

# Session errors
AttributeError: 'NoneType' object has no attribute 'query'

# Mock configuration
Failed: DID NOT RAISE <class 'Exception'>
```

## Files to Fix

### Critical Fixtures
1. **workspace/tests/conftest.py**
   - Add root-level fixtures
   - Configure test database
   - Setup mock providers

2. **workspace/api/tests/conftest.py**
   - Fix TestClient setup
   - Configure database override
   - Mock external services

3. **workspace/features/*/tests/conftest.py**
   - Feature-specific fixtures
   - Proper fixture inheritance
   - Mock dependencies

### Integration Test Files
- workspace/tests/integration/test_api_integration.py
- workspace/tests/integration/test_database_integration.py
- workspace/tests/integration/test_exchange_integration.py
- workspace/tests/integration/test_workflow_integration.py

## Specific Fixes Required

### Fix 1: Database Session Mock
```python
# workspace/tests/conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

@pytest.fixture
def db_session():
    """Create a test database session."""
    # Use in-memory SQLite for tests
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create tables
    Base.metadata.create_all(engine)

    # Create session
    TestSessionLocal = sessionmaker(bind=engine)
    session = TestSessionLocal()

    yield session

    # Cleanup
    session.close()
    engine.dispose()
```

### Fix 2: API TestClient Setup
```python
# workspace/api/tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

@pytest.fixture
def client(db_session):
    """Create test client with mocked dependencies."""

    # Override database dependency
    def get_test_db():
        yield db_session

    # Import app after patching
    with patch("workspace.api.database.get_db", get_test_db):
        from workspace.api.main import app

        # Create test client
        client = TestClient(app)
        yield client
```

### Fix 3: External Service Mocks
```python
# workspace/tests/fixtures/external_mocks.py
import pytest
from unittest.mock import MagicMock, AsyncMock

@pytest.fixture
def mock_exchange():
    """Mock exchange client."""
    exchange = MagicMock()
    exchange.fetch_ticker = AsyncMock(return_value={"last": 50000.0})
    exchange.fetch_balance = AsyncMock(return_value={"USDT": {"free": 10000}})
    exchange.create_order = AsyncMock(return_value={"id": "123", "status": "closed"})
    return exchange

@pytest.fixture
def mock_llm_provider():
    """Mock LLM provider."""
    provider = MagicMock()
    provider.generate = AsyncMock(return_value={
        "decision": "BUY",
        "confidence": 0.85,
        "reasoning": "Test reasoning"
    })
    return provider

@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    import fakeredis.aioredis
    return fakeredis.aioredis.FakeRedis()
```

### Fix 4: Import Error Resolution
```python
# Fix circular imports by using lazy imports
# workspace/api/__init__.py
def get_app():
    """Lazy load app to avoid circular imports."""
    from .main import app
    return app

# In tests
@pytest.fixture
def app():
    from workspace.api import get_app
    return get_app()
```

### Fix 5: Test Isolation
```python
# Ensure proper test isolation
@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singleton instances between tests."""
    # Reset any global state
    from workspace.shared.infrastructure import redis_manager
    redis_manager._instance = None

    yield

    # Cleanup after test
    redis_manager._instance = None

@pytest.fixture(autouse=True)
def clean_environment():
    """Clean environment variables."""
    import os
    original = os.environ.copy()

    # Set test environment
    os.environ["ENVIRONMENT"] = "test"
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"

    yield

    # Restore original
    os.environ.clear()
    os.environ.update(original)
```

### Fix 6: WebSocket Mock
```python
# Mock WebSocket connections
@pytest.fixture
def mock_websocket():
    """Mock WebSocket for market data."""
    ws = MagicMock()
    ws.recv = AsyncMock(side_effect=[
        '{"type": "ticker", "symbol": "BTC/USDT", "price": 50000}',
        '{"type": "orderbook", "symbol": "BTC/USDT", "bids": [], "asks": []}'
    ])
    ws.send = AsyncMock()
    ws.close = AsyncMock()
    return ws
```

## Test Commands

```bash
# Test fixture loading
python -m pytest --fixtures workspace/tests/

# Run integration tests
python -m pytest workspace/tests/integration/ -xvs

# Test API endpoints
python -m pytest workspace/api/tests/ -xvs

# Check for import errors
python -c "from workspace.api.main import app; print('Import successful')"

# Verify mock usage
python -m pytest workspace/tests/ -k "mock" -xvs
```

## Success Criteria

- [ ] All import errors resolved
- [ ] Database fixtures working properly
- [ ] API TestClient successfully created
- [ ] External service mocks configured
- [ ] Test isolation ensured
- [ ] WebSocket tests passing
- [ ] No fixture scope issues
- [ ] Integration tests running

## Common Pitfalls to Avoid

1. **Don't share database sessions**: Each test needs isolation
2. **Don't forget async mocks**: Use AsyncMock for async methods
3. **Don't hardcode test data**: Use fixtures and factories
4. **Don't mock too deep**: Mock at service boundaries
5. **Don't ignore cleanup**: Always cleanup resources

## Recommended Approach

1. **Fix imports first** - Resolve all ImportError issues
2. **Setup root conftest** - Create shared fixtures
3. **Configure database mocks** - Use in-memory SQLite
4. **Add external mocks** - Mock exchanges, LLM, Redis
5. **Ensure isolation** - Add cleanup fixtures
6. **Test incrementally** - Verify each fix works

## Integration Test Patterns

### Database Testing
```python
def test_database_operation(db_session):
    # Given
    user = User(name="test")
    db_session.add(user)
    db_session.commit()

    # When
    result = db_session.query(User).first()

    # Then
    assert result.name == "test"
```

### API Testing
```python
def test_api_endpoint(client, mock_exchange):
    # Given
    with patch("workspace.api.routes.get_exchange", return_value=mock_exchange):
        # When
        response = client.get("/api/v1/market/ticker/BTC-USDT")

        # Then
        assert response.status_code == 200
        assert response.json()["price"] == 50000.0
```

## Time Allocation

- Hour 1: Fix import errors and circular dependencies
- Hour 2: Setup database and API fixtures
- Hour 3: Configure external service mocks
- 30 min: Ensure test isolation and cleanup

## Handoff Protocol

When complete:
1. Verify all imports work
2. Run integration test suite
3. Document mock patterns used
4. Create fixture usage guide
5. Tag Team Fix-Delta for verification

---

**Status**: Ready for Activation
**Estimated Time**: 2-3 hours
**Priority**: High (blocking all integration tests)
