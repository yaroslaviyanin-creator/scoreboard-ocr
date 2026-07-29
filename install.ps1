# Scoreboard OCR Tracker v2 — Windows Installer
# Run: Right-click → "Run with PowerShell"
# Or: powershell -ExecutionPolicy Bypass -File install.ps1

$ErrorActionPreference = "Stop"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Scoreboard OCR Tracker v2 — Windows Installer" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  This will download and install everything automatically."
Write-Host "  Total: ~2 GB. Time: 5-15 minutes."
Write-Host ""
Write-Host "  Press Enter to start..."
Read-Host

$InstallDir = "$env:USERPROFILE\ScoreboardOCR"

# ==========================================================
# STEP 1 — DOWNLOAD SOURCE CODE
# ==========================================================
Write-Host ""
Write-Host "[1/4] Downloading source code..." -ForegroundColor Yellow

if (Test-Path $InstallDir) {
    Write-Host "  Removing old installation..."
    Remove-Item -Recurse -Force $InstallDir
}

$ZipPath = "$env:TEMP\sbocr.zip"
$ExtractPath = "$env:TEMP\sbocr_extract"

Write-Host "  Downloading..."
Invoke-WebRequest -UseBasicParsing -Uri "https://github.com/yaroslaviyanin-creator/scoreboard-ocr/archive/refs/heads/main.zip" -OutFile $ZipPath

Write-Host "  Extracting..."
Expand-Archive -Path $ZipPath -DestinationPath $ExtractPath -Force

Write-Host "  Installing to $InstallDir..."
$SourceDir = Get-ChildItem -Path $ExtractPath -Directory | Select-Object -First 1
Copy-Item -Recurse "$($SourceDir.FullName)\*" $InstallDir

if (-not (Test-Path "$InstallDir\install.bat")) {
    Write-Host "  ERROR: Download failed!" -ForegroundColor Red
    Read-Host
    exit 1
}
Write-Host "  OK" -ForegroundColor Green

# ==========================================================
# STEP 2 — PYTHON
# ==========================================================
Write-Host ""
Write-Host "[2/4] Checking Python..." -ForegroundColor Yellow

function Get-PythonExe {
    $try = @(
        (Get-Command python -ErrorAction SilentlyContinue),
        (Get-Command py -ErrorAction SilentlyContinue),
        "$env:LocalAppData\Programs\Python\Python312\python.exe",
        "$env:ProgramFiles\Python312\python.exe",
        "C:\Python312\python.exe"
    )
    foreach ($p in $try) {
        if ($p -and (Test-Path $p)) { return $p }
        if ($p -is [System.Management.Automation.CommandInfo]) {
            $exe = & $p -c "import sys; print(sys.executable)" 2>$null
            if ($exe -and (Test-Path $exe)) { return $exe }
        }
    }
    return $null
}

$Python = Get-PythonExe

if (-not $Python) {
    Write-Host "  Python not found. Downloading Python 3.12..."
    $PyInstaller = "$env:TEMP\python312.exe"
    Invoke-WebRequest -UseBasicParsing -Uri "https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe" -OutFile $PyInstaller
    Write-Host "  Installing Python..."
    Start-Process -FilePath $PyInstaller -ArgumentList "/quiet InstallAllUsers=0 PrependPath=1 Include_test=0" -Wait
    $Python = "$env:LocalAppData\Programs\Python\Python312\python.exe"
    if (-not (Test-Path $Python)) {
        $Python = "$env:ProgramFiles\Python312\python.exe"
    }
}

Write-Host "  Python: $Python"
& $Python --version
Write-Host "  OK" -ForegroundColor Green

# ==========================================================
# STEP 3 — PYTHON PACKAGES
# ==========================================================
Write-Host ""
Write-Host "[3/4] Installing Python packages (~1 GB)..." -ForegroundColor Yellow

Set-Location $InstallDir
if (Test-Path "$InstallDir\.venv") {
    Remove-Item -Recurse -Force "$InstallDir\.venv"
}

Write-Host "  Creating virtual environment..."
& $Python -m venv .venv
$Activate = "$InstallDir\.venv\Scripts\Activate.ps1"
. $Activate

Write-Host "  Upgrading pip..."
python -m pip install --upgrade pip --quiet 2>&1 | Out-Null

Write-Host "  Installing PyQt6..."
pip install PyQt6 --quiet
Write-Host "  Installing OpenCV..."
pip install opencv-python numpy --quiet
Write-Host "  Installing PaddleOCR (AI, ~1 GB, please wait)..."
pip install paddlepaddle paddleocr --quiet
Write-Host "  Installing Tesseract bindings..."
pip install pytesseract platformdirs --quiet

Write-Host "  OK" -ForegroundColor Green

# ==========================================================
# STEP 4 — LAUNCHER + SHORTCUT
# ==========================================================
Write-Host ""
Write-Host "[4/4] Creating launcher..." -ForegroundColor Yellow

$RunScript = @"
@echo off
cd /d "$InstallDir"
call .venv\Scripts\activate.bat
python -m scoreboard_ocr.app
if errorlevel 1 pause
"@
$RunScript | Out-File -FilePath "$InstallDir\run.bat" -Encoding ASCII

$Desktop = [Environment]::GetFolderPath("Desktop")
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$Desktop\ScoreboardOCR.lnk")
$Shortcut.TargetPath = "cmd.exe"
$Shortcut.Arguments = "/c `"$InstallDir\run.bat`""
$Shortcut.WorkingDirectory = $InstallDir
$Shortcut.Description = "Scoreboard OCR Tracker v2"
if (Test-Path "$InstallDir\assets\icon.ico") {
    $Shortcut.IconLocation = "$InstallDir\assets\icon.ico"
}
$Shortcut.Save()

Write-Host "  OK" -ForegroundColor Green
Write-Host ""
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  INSTALLATION COMPLETE!" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Launch from Desktop: ScoreboardOCR"
Write-Host "  Or run: $InstallDir\run.bat"
Write-Host ""
Write-Host "  Press Enter to exit..."
Read-Host
