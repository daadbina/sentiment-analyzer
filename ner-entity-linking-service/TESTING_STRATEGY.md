# NER Entity Linking Service Testing Strategy

## Overview

This document outlines the comprehensive testing strategy for the NER Entity Linking Service, covering unit tests, integration tests, performance tests, and end-to-end tests.

## Test Pyramid

```
        /\
       /  \        E2E Tests (5%)
      /    \       - Full pipeline tests
     /------\      - Kafka integration
    /        \     - Database integration
   /          \    - External API integration
  /            \
 /              \   Integration Tests (25%)
/________________\  - Kafka consumer/producer
                    - PostgreSQL repository
                    - Redis caching
                    - External APIs

                    Unit Tests (70%)
                    - NER extraction
                    - Entity normalization
                    - Entity linking
                    - Resilience patterns
                    - Optimization utilities
```

## Test Categories

### 1. Unit Tests (70%)

**Purpose:** Test individual components in isolation

**Coverage:**
- NER extraction (test_ner_orchestrator.py)
- Entity normalization (test_entity_normalizer.py)
- Entity linking (test_entity_linker.py)
- Advanced features (test_advanced_features.py)
- Optimization utilities (test_optimization.py)
- Resilience patterns (test_resilience.py)

**Target:** ≥90% code coverage

**Run Command:**
```bash
pytest tests/test_*.py -v --cov=src --cov-report=html
```

### 2. Integration Tests (25%)

**Purpose:** Test component interactions

**Coverage:**
- Kafka consumer/producer (test_kafka_integration.py)
- PostgreSQL repository (test_postgres_integration.py)
- Redis caching (test_redis_integration.py)
- End-to-end pipeline (test_e2e_pipeline.py)

**Requirements:**
- Docker containers (Kafka, PostgreSQL, Redis)
- Testcontainers library
- Network connectivity

**Run Command:**
```bash
pytest tests/test_*_integration.py -v -m integration
```

### 3. Performance Tests (3%)

**Purpose:** Verify performance targets

**Coverage:**
- Entity extraction latency
- Entity linking latency
- Batch processing throughput
- Memory efficiency
- Cache hit rates

**Targets:**
- Throughput: ≥200 articles/minute per replica
- Latency: ≤5 seconds average
- P95 Latency: ≤8 seconds
- Cache hit rate: ≥80%

**Run Command:**
```bash
pytest tests/test_performance.py -v -m performance
```

### 4. End-to-End Tests (2%)

**Purpose:** Test complete workflows

**Coverage:**
- Full message processing pipeline
- Entity extraction and linking
- Actor persistence
- Coverage calculation

**Run Command:**
```bash
pytest tests/test_e2e_pipeline.py -v -m integration
```

## Test Fixtures

### Available Fixtures

**Entity Fixtures:**
- `sample_entity` - Single entity
- `sample_entities` - Multiple entities
- `sample_entity_types` - Entities of different types
- `sample_confidence_levels` - Entities with different confidence levels

**Actor Fixtures:**
- `sample_actor` - Single actor

**Message Fixtures:**
- `sample_news_message` - News canonical message
- `sample_multilingual_texts` - Texts in 10 languages

**Factory:**
- `TestDataFactory` - Create custom test data

### Usage Example

```python
def test_entity_extraction(sample_entity):
    """Test entity extraction."""
    assert sample_entity.text == "John Smith"
    assert sample_entity.confidence == 0.95
```

## Test Data

### Multilingual Test Data

Supported languages:
- English (en)
- Persian (fa)
- Russian (ru)
- Chinese (zh)
- Arabic (ar)
- German (de)
- French (fr)
- Spanish (es)
- Japanese (ja)
- Korean (ko)

### Entity Types

- PERSON
- ORGANIZATION
- LOCATION
- GPE (Geopolitical Entity)
- CURRENCY
- DATE
- EVENT

## Coverage Requirements

### Minimum Coverage Targets

| Component | Target |
|-----------|--------|
| NER extraction | 95% |
| Entity normalization | 95% |
| Entity linking | 90% |
| Kafka integration | 85% |
| PostgreSQL repository | 90% |
| Redis caching | 85% |
| Resilience patterns | 95% |
| Optimization utilities | 90% |
| **Overall** | **≥90%** |

## Running Tests

### Run All Tests

```bash
pytest tests/ -v
```

### Run Specific Test Category

```bash
# Unit tests only
pytest tests/test_*.py -v --ignore=tests/test_*_integration.py

# Integration tests only
pytest tests/test_*_integration.py -v -m integration

# Performance tests only
pytest tests/test_performance.py -v -m performance
```

### Run with Coverage

```bash
pytest tests/ -v --cov=src --cov-report=html --cov-report=term
```

### Run with Markers

```bash
# Run only integration tests
pytest -m integration

# Run only performance tests
pytest -m performance

# Run all except integration tests
pytest -m "not integration"
```

## Continuous Integration

### GitHub Actions Workflow

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: 3.11
      - run: pip install -r requirements.txt
      - run: pytest tests/ -v --cov=src
```

## Test Maintenance

### Adding New Tests

1. Create test file in `tests/` directory
2. Follow naming convention: `test_*.py`
3. Use fixtures from `test_fixtures.py`
4. Add appropriate markers (@pytest.mark.integration, etc.)
5. Ensure ≥90% coverage for new code

### Updating Tests

1. Update test when API changes
2. Update fixtures when models change
3. Keep tests independent and isolated
4. Use mocking for external dependencies

## Troubleshooting

### Common Issues

**Issue:** Tests fail with "Connection refused"
- Ensure Docker containers are running
- Check Kafka, PostgreSQL, Redis connectivity

**Issue:** Tests timeout
- Increase timeout in pytest.ini
- Check system resources
- Reduce batch sizes for performance tests

**Issue:** Flaky tests
- Add explicit waits for async operations
- Use fixtures for setup/teardown
- Avoid time-dependent assertions

## Performance Benchmarks

### Expected Performance

| Operation | Latency | Throughput |
|-----------|---------|-----------|
| Entity extraction | <1s | >500 entities/s |
| Entity linking | <2s | >100 entities/s |
| Batch processing | <5s | >200 articles/min |
| Cache lookup | <10ms | >10k lookups/s |

## Test Reporting

### Generate Coverage Report

```bash
pytest tests/ --cov=src --cov-report=html
open htmlcov/index.html
```

### Generate Test Report

```bash
pytest tests/ -v --html=report.html
```

## Best Practices

1. **Isolation:** Each test should be independent
2. **Clarity:** Test names should describe what they test
3. **Fixtures:** Use fixtures for common setup
4. **Mocking:** Mock external dependencies
5. **Assertions:** Use clear, specific assertions
6. **Documentation:** Document complex test logic
7. **Performance:** Keep tests fast (<1s per test)
8. **Maintenance:** Update tests when code changes

