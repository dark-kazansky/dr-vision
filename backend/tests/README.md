# Backend Tests

## Test Structure

```
tests/
├── test_schema_generation.py    # Schema generation tests
├── test_split_integration.py    # Split integration tests
└── test_split_route.py          # Split route tests
```

## Running Tests

```bash
# Run all tests
cd backend
pytest

# Run specific test file
pytest tests/test_schema_generation.py

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=. --cov-report=html
```

## Test Categories

### Schema Generation Tests
Tests for dynamic schema generation engine.

### Split Tests
Tests for document splitting functionality:
- Integration tests
- Route tests

## Adding New Tests

When adding new features, create corresponding test files:

```
backend/tests/
├── test_api/              # API client tests (TODO)
├── test_processors/       # Processor tests (TODO)
├── test_models/           # Model validation tests (TODO)
└── test_routes/           # Route tests (TODO)
```

## Test Best Practices

1. **Use fixtures** for common setup
2. **Mock external APIs** (LM Studio, vLLM, POE)
3. **Test edge cases** and error handling
4. **Keep tests isolated** and independent
5. **Use descriptive test names**
