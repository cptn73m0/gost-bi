# GOST BI — Установка на Windows 10/11
#
# Требования: Windows 10 22H2+ или Windows 11, PowerShell 5.1+
# Права администратора НЕ требуются (установка в пользовательскую директорию)

param(
    [string]$InstallDir = "$env:LOCALAPPDATA\gost-bi",
    [string]$PythonVersion = "3.12"
)

$ErrorActionPreference = "Stop"
$Host.UI.RawUI.WindowTitle = "GOST BI — Установка на Windows"

Write-Host "=== GOST BI — Установка на Windows 10/11 ===" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check prerequisites
Write-Host "[1/6] Проверка предустановленных компонентов..." -ForegroundColor Yellow

$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    $pythonCmd = Get-Command py -ErrorAction SilentlyContinue
}

if ($pythonCmd) {
    $pyVer = & $pythonCmd.Source --version 2>&1
    Write-Host "  OK Python: $pyVer" -ForegroundColor Green
} else {
    Write-Host "  Python $PythonVersion не найден. Скачайте с https://python.org" -ForegroundColor Red
    Write-Host "  При установке отметьте 'Add Python to PATH'" -ForegroundColor Yellow
    exit 1
}

$gitCmd = Get-Command git -ErrorAction SilentlyContinue
if ($gitCmd) {
    Write-Host "  OK Git: $($gitCmd.Source)" -ForegroundColor Green
} else {
    Write-Host "  Git не найден. Скачайте с https://git-scm.com" -ForegroundColor Red
    exit 1
}

# Step 2: Create directories
Write-Host "[2/6] Создание директорий..." -ForegroundColor Yellow
New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
New-Item -ItemType Directory -Path "$InstallDir\venv" -Force | Out-Null

# Step 3: Create virtual environment
Write-Host "[3/6] Создание виртуального окружения..." -ForegroundColor Yellow
& $pythonCmd.Source -m venv "$InstallDir\venv"

$venvPython = "$InstallDir\venv\Scripts\python.exe"
$venvPip = "$InstallDir\venv\Scripts\pip.exe"

Write-Host "  OK Виртуальное окружение создано" -ForegroundColor Green

# Step 4: Install GOST BI
Write-Host "[4/6] Установка GOST BI и зависимостей..." -ForegroundColor Yellow
Set-Location -LiteralPath $PSScriptRoot\..
& $venvPip install --upgrade pip setuptools wheel 2>&1 | Out-Null
& $venvPip install -e ".[dev]" 2>&1 | ForEach-Object { Write-Host "  $_" }

Write-Host "  OK GOST BI установлен" -ForegroundColor Green

# Step 5: Verify compatibility
Write-Host "[5/6] Проверка совместимости..." -ForegroundColor Yellow
$verifyScript = @"
import sys, platform
print(f'  Python: {sys.version}')
print(f'  OS: {platform.platform()}')
print(f'  Arch: {platform.machine()}')
from gost_bi import __version__
print(f'  GOST BI: {__version__}')
print('  OK Совместимость подтверждена')
"@

& $venvPython -c $verifyScript

# Step 6: Create shortcuts
Write-Host "[6/6] Создание ярлыков..." -ForegroundColor Yellow

$WScriptShell = New-Object -ComObject WScript.Shell

# Desktop shortcut
$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = "$desktop\GOST BI.lnk"
$shortcut = $WScriptShell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = "powershell.exe"
$shortcut.Arguments = "-NoExit -Command `"Set-Location '$InstallDir'; & '$InstallDir\venv\Scripts\Activate.ps1'; Write-Host 'GOST BI dev env ready!' -ForegroundColor Green`""
$shortcut.WorkingDirectory = $InstallDir
$shortcut.IconLocation = "powershell.exe,0"
$shortcut.Save()

Write-Host "  OK Ярлык на рабочем столе: $shortcutPath" -ForegroundColor Green

Write-Host ""
Write-Host "=== Установка завершена ===" -ForegroundColor Green
Write-Host ""
Write-Host "Для запуска:" -ForegroundColor White
Write-Host "  1. Откройте ярлык 'GOST BI' на рабочем столе" -ForegroundColor Yellow
Write-Host "  2. Или выполните в PowerShell:" -ForegroundColor Yellow
Write-Host "     & '$InstallDir\venv\Scripts\Activate.ps1'" -ForegroundColor Cyan
Write-Host "     cd '$InstallDir'" -ForegroundColor Cyan
Write-Host ""
Write-Host "Проверка:" -ForegroundColor White
Write-Host "  make check-all" -ForegroundColor Cyan
Write-Host "  uvicorn gost_bi.core.app:app --reload" -ForegroundColor Cyan
Write-Host "  curl http://localhost:8088/api/health" -ForegroundColor Cyan
Write-Host ""
Write-Host "Примечание для Windows:" -ForegroundColor Yellow
Write-Host "  Docker Desktop рекомендуется для запуска Tantor/PostgreSQL." -ForegroundColor Yellow
Write-Host "  docker compose -f docker/docker-compose.yml up -d" -ForegroundColor Cyan
