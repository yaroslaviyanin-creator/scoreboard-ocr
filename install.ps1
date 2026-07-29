# Scoreboard OCR Tracker v2 - Windows Installer
# Usage: powershell -ExecutionPolicy Bypass -File install.ps1

$ErrorActionPreference = "Continue"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

Write-Host "=========================================================="
Write-Host "  Scoreboard OCR Tracker v2 - Windows Installer"
Write-Host "=========================================================="
Write-Host ""
Write-Host "  This will download and install everything automatically."
Write-Host "  Total: ~2 GB. Time: 5-15 minutes."
Write-Host ""

$InstallDir = "$env:USERPROFILE\ScoreboardOCR"
Write-Host "  Install to: $InstallDir"
Write-Host "  Press Enter to start..."
Read-Host

# ==========================================================
# STEP 1 - Download source code
# ==========================================================
Write-Host ""
Write-Host "[1/4] Downloading source code..."

if (Test-Path $InstallDir) {
    Write-Host "  Removing old installation..."
    Remove-Item -Recurse -Force $InstallDir -ErrorAction SilentlyContinue
}

$ZipPath = "$env:TEMP\sbocr_source.zip"
$ExtractPath = "$env:TEMP\sbocr_extract"

Write-Host "  Downloading from GitHub..."
try {
    Invoke-WebRequest -UseBasicParsing -Uri "https://codeload.github.com/yaroslaviyanin-creator/scoreboard-ocr/zip/refs/heads/main" -OutFile $ZipPath
    Write-Host "  Extracting..."
    Expand-Archive -Path $ZipPath -DestinationPath $ExtractPath -Force
    $SourceDir = Get-ChildItem -Path $ExtractPath -Directory | Select-Object -First 1
    Copy-Item -Recurse "$($SourceDir.FullName)\*" $InstallDir
    Write-Host "  Source installed to $InstallDir"
} catch {
    Write-Host "  ERROR: Download failed. Check internet."
    Read-Host
    exit 1
}
Write-Host "  OK"

# ==========================================================
# STEP 2 - Python
# ==========================================================
Write-Host ""
Write-Host "[2/4] Checking Python..."

$Python = $null
try { $Python = (Get-Command python -ErrorAction Stop).Source } catch {}
if (-not $Python) { $Python = "$env:LocalAppData\Programs\Python\Python312\python.exe" }
if (-not (Test-Path $Python)) { $Python = "$env:ProgramFiles\Python312\python.exe" }

if (Test-Path $Python) {
    Write-Host "  Found: $Python"
    & $Python --version
} else {
    Write-Host "  Python not found. Downloading Python 3.12..."
    $PyInstaller = "$env:TEMP\python312.exe"
    try {
        Invoke-WebRequest -UseBasicParsing -Uri "https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe" -OutFile $PyInstaller
        Write-Host "  Installing Python (please wait)..."
        Start-Process -FilePath $PyInstaller -ArgumentList "/quiet InstallAllUsers=0 PrependPath=1 Include_test=0" -Wait
        $Python = "$env:LocalAppData\Programs\Python\Python312\python.exe"
        if (-not (Test-Path $Python)) { $Python = "$env:ProgramFiles\Python312\python.exe" }
    } catch {
        Write-Host "  ERROR: Cannot download Python."
        Read-Host
        exit 1
    }
    Write-Host "  Python installed: $Python"
}
Write-Host "  OK"

# ==========================================================
# STEP 3 - Python packages
# ==========================================================
Write-Host ""
Write-Host "[3/4] Installing Python packages..."

Set-Location $InstallDir
if (Test-Path "$InstallDir\.venv") {
    Remove-Item -Recurse -Force "$InstallDir\.venv"
}

Write-Host "  Creating virtual environment..."
& $Python -m venv .venv
. "$InstallDir\.venv\Scripts\Activate.ps1"

Write-Host "  Upgrading pip..."
python -m pip install --upgrade pip --quiet 2>&1 | Out-Null

Write-Host "  Installing PyQt6..."
pip install PyQt6 --quiet
Write-Host "  Installing OpenCV..."
pip install opencv-python numpy --quiet
Write-Host "  Installing PaddleOCR (AI, ~1 GB)..."
pip install paddlepaddle paddleocr --quiet
Write-Host "  Installing Tesseract bindings..."
pip install pytesseract platformdirs --quiet
Write-Host "  OK"

# ==========================================================
# STEP 4 - Launcher + shortcut
# ==========================================================
Write-Host ""
Write-Host "[4/4] Creating launcher..."

$RunScript = "@echo off`r`ncd /d `"$InstallDir`"`r`ncall .venv\Scripts\activate.bat`r`npython -m scoreboard_ocr.app`r`nif errorlevel 1 pause"
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

Write-Host "  Desktop shortcut created: ScoreboardOCR"
Write-Host "  OK"

Write-Host ""
Write-Host "=========================================================="
Write-Host "  INSTALLATION COMPLETE!"
Write-Host "=========================================================="
Write-Host ""
Write-Host "  Launch from Desktop: ScoreboardOCR"
Write-Host "  Or run: $InstallDir\run.bat"
Write-Host ""
Write-Host "  Press Enter to exit..."
Read-Host
