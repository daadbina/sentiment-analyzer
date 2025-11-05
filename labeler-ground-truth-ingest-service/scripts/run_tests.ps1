# Run tests with coverage

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Running Labeler Service Tests" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check if pytest is installed
try {
    pytest --version | Out-Null
} catch {
    Write-Host "pytest not found. Installing dependencies..." -ForegroundColor Yellow
    pip install -r requirements.txt
}

Write-Host "Running pytest with coverage..." -ForegroundColor Green
Write-Host ""

# Run tests with coverage
pytest tests/ `
    -v `
    --strict-markers `
    --tb=short `
    --cov=src `
    --cov-report=term-missing `
    --cov-report=html `
    --cov-report=xml `
    --cov-fail-under=90 `
    -m "unit or integration or contract"

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Test Results" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check if coverage report exists
if (Test-Path "htmlcov/index.html") {
    Write-Host "✓ Coverage report generated: htmlcov/index.html" -ForegroundColor Green
}

if (Test-Path ".coverage") {
    Write-Host "✓ Coverage data saved: .coverage" -ForegroundColor Green
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Test Summary" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Print coverage summary
try {
    coverage report --skip-covered
} catch {
    Write-Host "Coverage report not available" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "✓ All tests completed!" -ForegroundColor Green

