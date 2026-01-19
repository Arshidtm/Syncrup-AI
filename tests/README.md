# Test Configuration

## Running Tests

### Install Test Dependencies

```bash
pip install pytest pytest-cov requests
```

### Run All Tests

```bash
pytest tests/
```

### Run Unit Tests Only

```bash
pytest tests/unit/
```

### Run Integration Tests Only

```bash
pytest tests/integration/
```

### Run with Coverage

```bash
pytest --cov=src tests/
```

### Run Specific Test File

```bash
pytest tests/unit/test_parsers.py
```

### Run Specific Test

```bash
pytest tests/unit/test_parsers.py::TestPythonParser::test_parse_function_definition
```

## Test Requirements

### For Unit Tests
- Neo4j database running (for graph manager tests)
- Groq API key configured (for analyzer tests)

### For Integration Tests
- API server running (`python src/api_server.py`)
- Workers running (automatically started by API server)
- Neo4j database running

## Test Fixtures

Sample projects are located in `tests/fixtures/sample_projects/`:
- `simple_python/` - Minimal Python project for basic tests

## Writing New Tests

### Unit Tests
Place in `tests/unit/` and follow the naming convention `test_*.py`

### Integration Tests
Place in `tests/integration/` and follow the naming convention `test_*.py`

### Fixtures
Add sample projects to `tests/fixtures/sample_projects/`

## CI/CD Integration

To integrate with CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run tests
  run: |
    pytest tests/ --cov=src --cov-report=xml
```

## Test Coverage Goals

- Unit tests: >80% coverage
- Integration tests: All API endpoints covered
- Critical paths: 100% coverage (graph operations, impact analysis)
