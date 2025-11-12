# PowerShell script to apply Feast features on remote server
# This script uses plink (PuTTY) to handle SSH with password

$remoteHost = "154.53.166.231"
$remoteUser = "root"
$password = "MBcH5LubNVSK*"

Write-Host "=== Applying Feast Feature Definitions to Remote Server ===" -ForegroundColor Cyan
Write-Host ""

# Check if plink is available
$plinkPath = "plink"
try {
    $null = Get-Command plink -ErrorAction Stop
} catch {
    Write-Host "ERROR: plink not found. Please install PuTTY or use manual SSH." -ForegroundColor Red
    Write-Host ""
    Write-Host "Manual steps:" -ForegroundColor Yellow
    Write-Host "1. SSH to server: ssh root@154.53.166.231" -ForegroundColor Yellow
    Write-Host "2. Navigate to directory: cd ~/feast/feature_repo" -ForegroundColor Yellow
    Write-Host "3. Make script executable: chmod +x apply_features.sh" -ForegroundColor Yellow
    Write-Host "4. Run script: ./apply_features.sh" -ForegroundColor Yellow
    exit 1
}

Write-Host "Step 1: Making script executable..." -ForegroundColor Green
$command1 = "chmod +x ~/feast/feature_repo/apply_features.sh"
echo y | plink -ssh -pw $password "$remoteUser@$remoteHost" $command1

Write-Host ""
Write-Host "Step 2: Executing apply_features.sh..." -ForegroundColor Green
$command2 = "bash ~/feast/feature_repo/apply_features.sh"
echo y | plink -ssh -pw $password "$remoteUser@$remoteHost" $command2

Write-Host ""
Write-Host "=== Feature Application Complete ===" -ForegroundColor Cyan

