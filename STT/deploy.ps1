# PowerShell deployment script for Twilio Stream Infrastructure

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Twilio Stream Deployment Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if AWS CLI is installed
try {
    $awsVersion = aws --version
    Write-Host "AWS CLI: $awsVersion" -ForegroundColor Green
} catch {
    Write-Host "ERROR: AWS CLI is not installed or not in PATH" -ForegroundColor Red
    exit 1
}

# Check if CDK is installed
try {
    $cdkVersion = cdk --version
    Write-Host "CDK Version: $cdkVersion" -ForegroundColor Green
} catch {
    Write-Host "CDK not found. Installing AWS CDK..." -ForegroundColor Yellow
    npm install -g aws-cdk
}

# Navigate to infrastructure directory
Push-Location infrastructure

# Create virtual environment if it doesn't exist
if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
.\.venv\Scripts\Activate.ps1

# Install dependencies
Write-Host "Installing dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt

# Bootstrap CDK (if needed)
Write-Host ""
Write-Host "Checking CDK bootstrap status..." -ForegroundColor Yellow
cdk bootstrap

# Synthesize the stack
Write-Host ""
Write-Host "Synthesizing CloudFormation template..." -ForegroundColor Yellow
cdk synth

# Deploy
Write-Host ""
Write-Host "Deploying stack..." -ForegroundColor Yellow
cdk deploy --require-approval never

# Return to original directory
Pop-Location

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Deployment Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Copy the TwiML Webhook URL from the output above" -ForegroundColor White
Write-Host "2. Go to Twilio Console -> Phone Numbers -> Your +1 number" -ForegroundColor White
Write-Host "3. Set the 'When a call comes in' webhook to the TwiML URL" -ForegroundColor White
Write-Host "4. Make a test call to your Twilio number!" -ForegroundColor White


