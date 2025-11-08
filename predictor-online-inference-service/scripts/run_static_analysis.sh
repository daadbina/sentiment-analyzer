#!/bin/bash
# Run static analysis tools on the codebase

set -e

echo "Running static analysis..."
echo ""

# Run ruff for linting
echo "=== Running ruff ==="
ruff check src/ tests/
echo "✓ ruff passed"
echo ""

# Run black for code formatting check
echo "=== Running black ==="
black --check src/ tests/
echo "✓ black passed"
echo ""

# Run mypy for type checking
echo "=== Running mypy ==="
mypy src/
echo "✓ mypy passed"
echo ""

# Run bandit for security checks
echo "=== Running bandit ==="
bandit -r src/ -ll
echo "✓ bandit passed"
echo ""

echo "All static analysis checks passed!"

