# PowerShell script to test the training data endpoint
# Usage examples for /crawl/training-data endpoint

$CRAWLER_URL = "http://localhost:8000"

Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "TRAINING DATA ENDPOINT EXAMPLES" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""

# Example 1: Fetch ALL available training datasets (no filters)
Write-Host "Example 1: Fetch ALL available training datasets" -ForegroundColor Yellow
Write-Host "Command:" -ForegroundColor Green
Write-Host 'Invoke-RestMethod -Uri "http://localhost:8000/crawl/training-data" -Method Post' -ForegroundColor White
Write-Host ""
Write-Host "Executing..." -ForegroundColor Cyan

try {
    $response1 = Invoke-RestMethod -Uri "$CRAWLER_URL/crawl/training-data" -Method Post -ContentType "application/json"
    Write-Host "Success!" -ForegroundColor Green
    Write-Host "Job ID: $($response1.job_id)" -ForegroundColor White
    Write-Host "Articles Crawled: $($response1.articles_crawled)" -ForegroundColor White
    Write-Host "Articles Published: $($response1.articles_published)" -ForegroundColor White
    Write-Host "Articles Failed: $($response1.articles_failed)" -ForegroundColor White
    Write-Host "Status: $($response1.status)" -ForegroundColor White
} catch {
    Write-Host "Error: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "-" * 80 -ForegroundColor Gray
Write-Host ""

# Example 2: Fetch specific categories (War/Conflict and Politics)
Write-Host "Example 2: Fetch specific categories (War/Conflict and Politics)" -ForegroundColor Yellow
Write-Host "Command:" -ForegroundColor Green
$command2 = @'
$body = @{
    categories = @("War, Conflict and Unrest", "Politics")
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/crawl/training-data" `
    -Method Post `
    -Body $body `
    -ContentType "application/json"
'@
Write-Host $command2 -ForegroundColor White
Write-Host ""
Write-Host "Executing..." -ForegroundColor Cyan

try {
    $body2 = @{
        categories = @("War, Conflict and Unrest", "Politics")
    } | ConvertTo-Json
    
    $response2 = Invoke-RestMethod -Uri "$CRAWLER_URL/crawl/training-data" `
        -Method Post `
        -Body $body2 `
        -ContentType "application/json"
    
    Write-Host "Success!" -ForegroundColor Green
    Write-Host "Job ID: $($response2.job_id)" -ForegroundColor White
    Write-Host "Articles Crawled: $($response2.articles_crawled)" -ForegroundColor White
    Write-Host "Articles Published: $($response2.articles_published)" -ForegroundColor White
} catch {
    Write-Host "Error: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "-" * 80 -ForegroundColor Gray
Write-Host ""

# Example 3: Fetch only negative sentiment articles
Write-Host "Example 3: Fetch only NEGATIVE sentiment articles" -ForegroundColor Yellow
Write-Host "Command:" -ForegroundColor Green
$command3 = @'
$body = @{
    sentiments = @("negative")
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/crawl/training-data" `
    -Method Post `
    -Body $body `
    -ContentType "application/json"
'@
Write-Host $command3 -ForegroundColor White
Write-Host ""
Write-Host "Executing..." -ForegroundColor Cyan

try {
    $body3 = @{
        sentiments = @("negative")
    } | ConvertTo-Json
    
    $response3 = Invoke-RestMethod -Uri "$CRAWLER_URL/crawl/training-data" `
        -Method Post `
        -Body $body3 `
        -ContentType "application/json"
    
    Write-Host "Success!" -ForegroundColor Green
    Write-Host "Job ID: $($response3.job_id)" -ForegroundColor White
    Write-Host "Articles Crawled: $($response3.articles_crawled)" -ForegroundColor White
    Write-Host "Articles Published: $($response3.articles_published)" -ForegroundColor White
} catch {
    Write-Host "Error: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "-" * 80 -ForegroundColor Gray
Write-Host ""

# Example 4: Fetch both positive and negative with max limit
Write-Host "Example 4: Fetch BOTH sentiments with max 3 datasets" -ForegroundColor Yellow
Write-Host "Command:" -ForegroundColor Green
$command4 = @'
$body = @{
    sentiments = @("positive", "negative")
    max_datasets = 3
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/crawl/training-data" `
    -Method Post `
    -Body $body `
    -ContentType "application/json"
'@
Write-Host $command4 -ForegroundColor White
Write-Host ""
Write-Host "Executing..." -ForegroundColor Cyan

try {
    $body4 = @{
        sentiments = @("positive", "negative")
        max_datasets = 3
    } | ConvertTo-Json
    
    $response4 = Invoke-RestMethod -Uri "$CRAWLER_URL/crawl/training-data" `
        -Method Post `
        -Body $body4 `
        -ContentType "application/json"
    
    Write-Host "Success!" -ForegroundColor Green
    Write-Host "Job ID: $($response4.job_id)" -ForegroundColor White
    Write-Host "Articles Crawled: $($response4.articles_crawled)" -ForegroundColor White
    Write-Host "Articles Published: $($response4.articles_published)" -ForegroundColor White
} catch {
    Write-Host "Error: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "-" * 80 -ForegroundColor Gray
Write-Host ""

# Example 5: Comprehensive - Multiple categories, both sentiments, limited datasets
Write-Host "Example 5: COMPREHENSIVE - Multiple categories + both sentiments + limit" -ForegroundColor Yellow
Write-Host "Command:" -ForegroundColor Green
$command5 = @'
$body = @{
    categories = @(
        "War, Conflict and Unrest",
        "Politics",
        "Health",
        "Environment",
        "Sport"
    )
    sentiments = @("positive", "negative")
    max_datasets = 10
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/crawl/training-data" `
    -Method Post `
    -Body $body `
    -ContentType "application/json"
'@
Write-Host $command5 -ForegroundColor White
Write-Host ""
Write-Host "Executing..." -ForegroundColor Cyan

try {
    $body5 = @{
        categories = @(
            "War, Conflict and Unrest",
            "Politics",
            "Health",
            "Environment",
            "Sport"
        )
        sentiments = @("positive", "negative")
        max_datasets = 10
    } | ConvertTo-Json
    
    $response5 = Invoke-RestMethod -Uri "$CRAWLER_URL/crawl/training-data" `
        -Method Post `
        -Body $body5 `
        -ContentType "application/json"
    
    Write-Host "Success!" -ForegroundColor Green
    Write-Host "Job ID: $($response5.job_id)" -ForegroundColor White
    Write-Host "Articles Crawled: $($response5.articles_crawled)" -ForegroundColor White
    Write-Host "Articles Published: $($response5.articles_published)" -ForegroundColor White
} catch {
    Write-Host "Error: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "AVAILABLE CATEGORIES" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""
Write-Host "- Arts, Culture, and Entertainment" -ForegroundColor White
Write-Host "- Crime, Law and Justice" -ForegroundColor White
Write-Host "- Disaster and Accident" -ForegroundColor White
Write-Host "- Economy, Business and Finance" -ForegroundColor White
Write-Host "- Education" -ForegroundColor White
Write-Host "- Environment" -ForegroundColor White
Write-Host "- Health" -ForegroundColor White
Write-Host "- Human Interest" -ForegroundColor White
Write-Host "- Labor" -ForegroundColor White
Write-Host "- Lifestyle and Leisure" -ForegroundColor White
Write-Host "- Politics" -ForegroundColor White
Write-Host "- Religion and Belief" -ForegroundColor White
Write-Host "- Science and Technology" -ForegroundColor White
Write-Host "- Social Issue" -ForegroundColor White
Write-Host "- Sport" -ForegroundColor White
Write-Host "- War, Conflict and Unrest" -ForegroundColor White
Write-Host "- Weather" -ForegroundColor White
Write-Host ""
Write-Host "AVAILABLE SENTIMENTS" -ForegroundColor Cyan
Write-Host "- positive" -ForegroundColor White
Write-Host "- negative" -ForegroundColor White
Write-Host ""

