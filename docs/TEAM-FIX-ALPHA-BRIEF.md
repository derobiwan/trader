# Team Fix-Alpha: Async & Redis Specialist Brief

## Mission
Fix all async/Redis test failures to achieve 100% pass rate for Redis-related tests.

## Assigned Agent Type
Implementation Specialist with async/await and Redis expertise

## Failure Analysis

### Primary Issue: Async Context Manager Protocol
```python
# Current failing pattern
async with redis_manager as manager:  # TypeError: 'async_generator' object does not support context manager
    await manager.set("key", "value")

# Root cause: Fixture returns async generator instead of context manager
```

### Secondary Issues
1. pytest-asyncio fixture scope warnings
2. fakeredis initialization in async context
3. Missing await statements in test methods
4. Incorrect fixture decorators

## Files to Fix

### Critical Files
1. **workspace/tests/unit/test_redis_manager.py** (37 failures)
   - Fix async context manager usage
   - Update fixture decorators to @pytest_asyncio.fixture
   - Correct async/await patterns

2. **workspace/tests/integration/test_redis_integration.py** (15 failures)
   - Fix fakeredis async initialization
   - Correct connection pool management
   - Fix async cleanup methods

3. **workspace/shared/infrastructure/redis_manager.py**
   - Ensure proper async context manager implementation
   - Fix __aenter__ and __aexit__ methods if needed

### Supporting Files
- workspace/tests/conftest.py (fixture definitions)
- workspace/shared/infrastructure/cache.py (if Redis-dependent)

## Specific Fixes Required

### Fix 1: Async Fixture Decorator
```python
# Before (incorrect)
@pytest.fixture
async def redis_manager():
    manager = RedisManager()
    await manager.initialize()
    yield manager
    await manager.cleanup()

# After (correct)
@pytest_asyncio.fixture
async def redis_manager():
    manager = RedisManager()
    await manager.initialize()
    yield manager
    await manager.cleanup()
```

### Fix 2: Context Manager Support
```python
# Add proper async context manager support
class RedisManager:
    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()
```

### Fix 3: Test Method Patterns
```python
# Ensure all test methods properly use async/await
@pytest.mark.asyncio
async def test_redis_operation():
    async with redis_manager() as manager:
        result = await manager.get("key")
        assert result is not None
```

### Fix 4: Fakeredis Configuration
```python
# Proper fakeredis async setup
import fakeredis.aioredis

@pytest_asyncio.fixture
async def redis_client():
    client = fakeredis.aioredis.FakeRedis()
    yield client
    await client.close()
```

## Test Commands

```bash
# Verify Redis manager tests
python -m pytest workspace/tests/unit/test_redis_manager.py -xvs

# Check integration tests
python -m pytest workspace/tests/integration/test_redis_integration.py -xvs

# Run all async tests
python -m pytest -k "async" -xvs

# Check for warnings
python -m pytest workspace/tests/unit/test_redis_manager.py -W error::DeprecationWarning
```

## Success Criteria

- [ ] All 37 Redis manager unit tests pass
- [ ] All 15 Redis integration tests pass
- [ ] No pytest-asyncio deprecation warnings
- [ ] No async/await syntax errors
- [ ] Context managers work properly
- [ ] Fakeredis properly initialized in all tests
- [ ] Test execution time < 10 seconds

## Common Pitfalls to Avoid

1. **Don't mix sync and async**: Ensure consistency
2. **Don't forget await**: Every async call needs await
3. **Don't use @pytest.fixture for async**: Use @pytest_asyncio.fixture
4. **Don't forget cleanup**: Always close connections
5. **Don't ignore warnings**: They often indicate real issues

## Recommended Approach

1. **Start with fixtures** - Fix all fixture decorators first
2. **Fix context managers** - Ensure RedisManager supports async context
3. **Update test methods** - Add proper async/await patterns
4. **Handle cleanup** - Ensure all resources are properly released
5. **Run comprehensive tests** - Verify no regressions

## Time Allocation

- Hour 1: Fix fixture decorators and context managers
- Hour 2: Update test methods with proper async patterns
- Hour 3: Fix fakeredis initialization and cleanup
- Hour 4: Final verification and edge cases

## Handoff Protocol

When complete:
1. Run full test suite for Redis components
2. Document all changes in changelog
3. Create summary of patterns fixed
4. Tag Team Fix-Delta for verification
5. Update this brief with completion status

---

**Status**: Ready for Activation
**Estimated Time**: 3-4 hours
**Priority**: High (blocking other async tests)
