# Team Fix-Bravo: Type Consistency Specialist Brief

## Mission
Fix all type consistency issues, especially Decimal vs float mismatches and Pydantic validation errors.

## Assigned Agent Type
Implementation Specialist with Python typing and Pydantic expertise

## Failure Analysis

### Primary Issue: Decimal vs Float Inconsistency
```python
# Current failing pattern
position_size = 0.1  # float
max_size = Decimal("0.10")  # Decimal
assert position_size <= max_size  # TypeError: '<=' not supported between float and Decimal
```

### Secondary Issues
1. Pydantic V1 to V2 migration warnings
2. Environment variable type validation
3. JSON serialization of Decimal values
4. Numeric precision in financial calculations

## Files to Fix

### Critical Files
1. **workspace/api/config.py**
   - Fix max_position_size_pct validation (currently failing with "10.0")
   - Update Pydantic field validators to V2 syntax
   - Ensure proper type coercion for env vars

2. **workspace/features/trade_executor/models.py**
   - Migrate @validator to @field_validator
   - Fix Decimal field serialization
   - Ensure consistent numeric types

3. **workspace/features/risk_manager/tests/**
   - Update all test fixtures to use Decimal consistently
   - Fix assertions comparing Decimal and float

4. **workspace/features/market_data/models.py**
   - Fix bandwidth validator
   - Ensure price/volume fields use Decimal

### Test Files Needing Updates
- workspace/features/trade_executor/tests/test_executor.py
- workspace/features/trade_executor/tests/test_models.py
- workspace/features/risk_manager/tests/test_risk_calculator.py
- workspace/features/market_data/tests/test_processor.py

## Specific Fixes Required

### Fix 1: Environment Configuration
```python
# workspace/api/config.py
from pydantic import Field, field_validator
from decimal import Decimal

class Settings(BaseSettings):
    # Before (failing)
    max_position_size_pct: float = Field(le=1.0)

    # After (fixed)
    max_position_size_pct: Decimal = Field(le=Decimal("1.0"))

    @field_validator('max_position_size_pct', mode='before')
    def validate_position_size(cls, v):
        if isinstance(v, str):
            return Decimal(v) / 100 if float(v) > 1 else Decimal(v)
        return Decimal(str(v))
```

### Fix 2: Pydantic V2 Migration
```python
# Before (V1 style - deprecated)
from pydantic import validator

class TradeOrder(BaseModel):
    quantity: Decimal

    @validator("remaining_quantity", always=True)
    def calculate_remaining(cls, v, values):
        return values.get("quantity", Decimal("0"))

# After (V2 style)
from pydantic import field_validator

class TradeOrder(BaseModel):
    quantity: Decimal

    @field_validator("remaining_quantity", mode="after")
    @classmethod
    def calculate_remaining(cls, v, info):
        return info.data.get("quantity", Decimal("0"))
```

### Fix 3: Test Decimal Consistency
```python
# Before (mixing types)
def test_risk_calculation():
    position_size = 1000.0  # float
    max_position = Decimal("5000")
    assert position_size < max_position  # Type error

# After (consistent Decimal usage)
def test_risk_calculation():
    position_size = Decimal("1000.0")
    max_position = Decimal("5000")
    assert position_size < max_position  # Works correctly
```

### Fix 4: JSON Serialization
```python
# Add Decimal encoder for API responses
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        return super().default(obj)

# Configure in Pydantic models
class Config:
    json_encoders = {
        Decimal: str
    }
```

## Type Consistency Standards

### Financial Values
- **Always use Decimal** for: prices, quantities, percentages, amounts
- **Use float only** for: metrics, ratios, non-financial calculations
- **Convert at boundaries**: API inputs/outputs, database storage

### Conversion Helpers
```python
# Utility functions to add
def to_decimal(value: Union[str, float, Decimal]) -> Decimal:
    """Safely convert any numeric type to Decimal."""
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))

def decimal_to_float(value: Decimal) -> float:
    """Convert Decimal to float for external APIs."""
    return float(value)
```

## Test Commands

```bash
# Test configuration loading
python -c "from workspace.api.config import settings; print(settings)"

# Run type-sensitive tests
python -m pytest workspace/features/trade_executor/tests/ -xvs
python -m pytest workspace/features/risk_manager/tests/ -xvs

# Check for Pydantic warnings
python -m pytest -W error::DeprecationWarning workspace/features/

# Verify Decimal consistency
grep -r "float.*price\|float.*amount\|float.*quantity" workspace/features/
```

## Success Criteria

- [ ] No Pydantic validation errors on startup
- [ ] All @validator decorators migrated to @field_validator
- [ ] Consistent Decimal usage in financial calculations
- [ ] No type comparison errors (Decimal vs float)
- [ ] JSON serialization handles Decimal properly
- [ ] Environment variables properly validated
- [ ] No deprecation warnings

## Common Pitfalls to Avoid

1. **Don't use float for money**: Always Decimal for financial values
2. **Don't compare mixed types**: Convert before comparison
3. **Don't use Decimal in type hints without imports**: Import from decimal
4. **Don't forget string conversion**: Decimal(str(float_val)) not Decimal(float_val)
5. **Don't ignore precision**: Set proper decimal context for calculations

## Recommended Approach

1. **Fix configuration first** - Resolve startup validation errors
2. **Migrate Pydantic validators** - Update to V2 syntax
3. **Standardize model types** - Ensure Decimal for all financial fields
4. **Update test fixtures** - Use Decimal consistently in tests
5. **Add conversion utilities** - Create helpers for type conversion
6. **Verify serialization** - Ensure JSON encoding works

## Time Allocation

- 30 min: Fix configuration validation errors
- 30 min: Migrate Pydantic validators
- 45 min: Update model field types
- 45 min: Fix test type inconsistencies
- 30 min: Final verification

## Handoff Protocol

When complete:
1. Verify no Pydantic validation errors
2. Run full test suite for affected modules
3. Document type conversion patterns used
4. Create type consistency guidelines
5. Tag Team Fix-Delta for verification

---

**Status**: Ready for Activation
**Estimated Time**: 1-2 hours
**Priority**: Critical (blocking API startup)
