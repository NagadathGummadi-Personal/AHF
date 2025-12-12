# PowerShell script to start the STT server with ngrok for Twilio testing
# Usage: .\start_server.ps1 [-Provider <provider>] [-Port <port>] [-NoNgrok]

param(
    [ValidateSet("elevenlabs", "assemblyai", "deepgram")]
    [string]$Provider = "elevenlabs",
    [int]$Port = 8000,
    [switch]$NoNgrok
)

$ErrorActionPreference = "Stop"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  STT Server - Latency Comparison Tool  " -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Check for .env file
$envPath = Join-Path $PSScriptRoot "..\\.env"
if (Test-Path $envPath) {
    Write-Host "Loading environment from .env file..." -ForegroundColor Green
    Get-Content $envPath | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
    }
}

# Check API keys
Write-Host "`nAPI Key Status:" -ForegroundColor Yellow
$providers = @{
    "elevenlabs" = "ELEVENLABS_API_KEY"
    "assemblyai" = "ASSEMBLYAI_API_KEY"
    "deepgram" = "DEEPGRAM_API_KEY"
}

$availableProviders = @()
foreach ($p in $providers.GetEnumerator()) {
    $key = [Environment]::GetEnvironmentVariable($p.Value)
    if ($key) {
        $masked = $key.Substring(0, [Math]::Min(8, $key.Length)) + "..."
        Write-Host "  [OK] $($p.Key): $masked" -ForegroundColor Green
        $availableProviders += $p.Key
    } else {
        Write-Host "  [--] $($p.Key): NOT SET ($($p.Value))" -ForegroundColor Red
    }
}

if ($availableProviders.Count -eq 0) {
    Write-Host "`nERROR: No API keys configured!" -ForegroundColor Red
    Write-Host "Create a .env file with your API keys:"
    Write-Host "  ELEVENLABS_API_KEY=your_key"
    Write-Host "  ASSEMBLYAI_API_KEY=your_key"
    Write-Host "  DEEPGRAM_API_KEY=your_key"
    exit 1
}

# Set default provider
$env:STT_PROVIDER = $Provider

# Start ngrok if requested
$ngrokProcess = $null
$publicUrl = $null

if (-not $NoNgrok) {
    $ngrokPath = Join-Path $PSScriptRoot "..\ngrok.exe"
    
    if (Test-Path $ngrokPath) {
        Write-Host "`nStarting ngrok tunnel..." -ForegroundColor Yellow
        
        # Kill any existing ngrok processes
        Get-Process ngrok -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 1
        
        $ngrokProcess = Start-Process -FilePath $ngrokPath -ArgumentList "http", $Port -PassThru -WindowStyle Hidden
        Start-Sleep -Seconds 3
        
        # Get public URL from ngrok API
        try {
            $response = Invoke-RestMethod -Uri "http://127.0.0.1:4040/api/tunnels" -ErrorAction Stop
            $tunnel = $response.tunnels | Where-Object { $_.proto -eq "https" } | Select-Object -First 1
            if ($tunnel) {
                $publicUrl = $tunnel.public_url
                Write-Host "  ngrok tunnel: $publicUrl" -ForegroundColor Green
            }
        } catch {
            Write-Host "  Could not get ngrok URL. Check http://127.0.0.1:4040" -ForegroundColor Yellow
        }
    } else {
        Write-Host "`nngrok.exe not found at $ngrokPath" -ForegroundColor Yellow
        Write-Host "Running without ngrok tunnel (localhost only)" -ForegroundColor Yellow
    }
}

$host_url = if ($publicUrl) { $publicUrl } else { "http://localhost:$Port" }
$ws_host = $host_url -replace "https://", "wss://" -replace "http://", "ws://"

Write-Host "`n========================================"
Write-Host "TWILIO CONFIGURATION" -ForegroundColor Yellow
Write-Host "========================================`n"

Write-Host "Webhook URLs (set 'A Call Comes In' to one of these):" -ForegroundColor Cyan
Write-Host "  Default ($Provider):`n    $host_url/twiml`n" -ForegroundColor White
foreach ($p in $availableProviders) {
    Write-Host "  $($p):`n    $host_url/twiml/$p`n" -ForegroundColor Gray
}

Write-Host "`n========================================"
Write-Host "COMPARISON MODE (RECOMMENDED)" -ForegroundColor Yellow
Write-Host "========================================`n"

Write-Host "Use this endpoint to test ALL providers with the SAME audio:" -ForegroundColor Green
Write-Host "   $host_url/twiml/compare" -ForegroundColor Cyan
Write-Host ""
Write-Host "This sends your audio to all providers simultaneously and"
Write-Host "displays a side-by-side latency comparison in real-time!`n"

Write-Host "========================================"
Write-Host "SINGLE PROVIDER MODE" -ForegroundColor Yellow
Write-Host "========================================`n"

Write-Host "Test individual providers:"
foreach ($p in $availableProviders) {
    Write-Host "   - $host_url/twiml/$p" -ForegroundColor Gray
}
Write-Host ""

Write-Host "========================================`n"

Write-Host "Starting server on port $Port..." -ForegroundColor Green
Write-Host "Default provider: $Provider" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop`n" -ForegroundColor Yellow

try {
    Set-Location $PSScriptRoot
    python -m uvicorn app:app --host 0.0.0.0 --port $Port --log-level info
} finally {
    if ($ngrokProcess) {
        Write-Host "`nStopping ngrok..." -ForegroundColor Yellow
        Stop-Process -Id $ngrokProcess.Id -Force -ErrorAction SilentlyContinue
    }
    Write-Host "Server stopped." -ForegroundColor Green
}

