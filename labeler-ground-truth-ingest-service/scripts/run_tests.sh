#!/bin/bash

# Run tests with coverage

set -e

echo "=========================================="
echo "Running Labeler Service Tests"
echo "=========================================="
echo ""

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo "pytest not found. Installing dependencies..."
    pip install -r requirements.txt
fi

echo "Running pytest with coverage..."
echo ""

# Run tests with coverage
pytest tests/ \
    -v \
    --strict-markers \
    --tb=short \
    --cov=src \
    --cov-report=term-missing \
    --cov-report=html \
    --cov-report=xml \
    --cov-fail-under=90 \
    -m "unit or integration or contract"

echo ""
echo "=========================================="
echo "Test Results"
echo "=========================================="
echo ""

# Check if coverage report exists
if [ -f "htmlcov/index.html" ]; then
    echo "✓ Coverage report generated: htmlcov/index.html"
fi

if [ -f ".coverage" ]; then
    echo "✓ Coverage data saved: .coverage"
fi

echo ""
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo ""

# Print coverage summary
if command -v coverage &> /dev/null; then
    coverage report --skip-covered
fi

echo ""
echo "✓ All tests completed!"

