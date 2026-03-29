# OracleGG Installer for Windows
# Run: powershell -ExecutionPolicy Bypass -File install.ps1

$ErrorActionPreference = "Stop"
$OracleDir = "$env:LOCALAPPDATA\OracleGG"
$DesktopShortcut = "$env:USERPROFILE\Desktop\OracleGG.lnk"

Write-Host ""
Write-Host "  ========================================" -ForegroundColor Yellow
Write-Host "  OracleGG Installer" -ForegroundColor Yellow
Write-Host "  League of Legends Real-Time Coach" -ForegroundColor Yellow
Write-Host "  ========================================" -ForegroundColor Yellow
Write-Host ""

# Check Python
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "[!] Python not found. Install Python 3.11+ from python.org" -ForegroundColor Red
    exit 1
}
$pyVersion = python --version 2>&1
Write-Host "[OK] $pyVersion" -ForegroundColor Green

# Check uv
$uv = Get-Command uv -ErrorAction SilentlyContinue
if (-not $uv) {
    Write-Host "[..] Installing uv package manager..." -ForegroundColor Cyan
    Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
}
Write-Host "[OK] uv installed" -ForegroundColor Green

# Create install directory
if (-not (Test-Path $OracleDir)) {
    New-Item -ItemType Directory -Path $OracleDir -Force | Out-Null
}

# Copy files
Write-Host "[..] Installing OracleGG..." -ForegroundColor Cyan
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir
Copy-Item -Path "$ProjectDir\*" -Destination $OracleDir -Recurse -Force -Exclude ".venv","data","__pycache__",".git"

# Install dependencies
Push-Location $OracleDir
Write-Host "[..] Installing dependencies..." -ForegroundColor Cyan
uv sync 2>&1 | Out-Null
Write-Host "[OK] Dependencies installed" -ForegroundColor Green

# Setup .env if not exists
if (-not (Test-Path "$OracleDir\.env")) {
    Copy-Item "$OracleDir\.env.example" "$OracleDir\.env"
    Write-Host ""
    Write-Host "[!] Edit $OracleDir\.env and set your RIOT_API_KEY" -ForegroundColor Yellow
    Write-Host "    Get one at: https://developer.riotgames.com/" -ForegroundColor Yellow
}

# Seed static data
Write-Host "[..] Downloading champion and item data..." -ForegroundColor Cyan
uv run python scripts/seed_static_data.py 2>&1 | Out-Null
Write-Host "[OK] Static data ready" -ForegroundColor Green

# Enable Live Client Data API in League config
$GameCfg = "C:\Riot Games\League of Legends\Config\game.cfg"
if (Test-Path $GameCfg) {
    $content = Get-Content $GameCfg -Raw
    if ($content -notmatch "EnableReplayApi") {
        $content = $content -replace "(\[General\])", "`$1`r`nEnableReplayApi=1"
        Set-Content $GameCfg $content
        Write-Host "[OK] Enabled Live Client Data API in League config" -ForegroundColor Green
    }
}

# Add firewall rule
Write-Host "[..] Adding firewall rule for Live Client API..." -ForegroundColor Cyan
netsh advfirewall firewall add rule name="OracleGG Live Client" dir=in action=allow protocol=TCP localport=2999 2>&1 | Out-Null
netsh advfirewall firewall add rule name="OracleGG Bridge" dir=in action=allow protocol=TCP localport=29990 2>&1 | Out-Null

# Create desktop shortcut
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($DesktopShortcut)
$Shortcut.TargetPath = "$OracleDir\launcher\OracleGG.bat"
$Shortcut.WorkingDirectory = $OracleDir
$Shortcut.Description = "OracleGG - League Coach"
$Shortcut.Save()
Write-Host "[OK] Desktop shortcut created" -ForegroundColor Green

Pop-Location

Write-Host ""
Write-Host "  ========================================" -ForegroundColor Green
Write-Host "  Installation complete!" -ForegroundColor Green
Write-Host "  ========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  1. Edit $OracleDir\.env with your Riot API key" -ForegroundColor White
Write-Host "  2. Double-click OracleGG on your Desktop" -ForegroundColor White
Write-Host ""
