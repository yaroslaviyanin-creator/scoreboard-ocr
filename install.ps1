# Scoreboard OCR Tracker v2 - Windows Installer
# Usage: powershell -ExecutionPolicy Bypass -File install.ps1

$ErrorActionPreference = "Continue"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

Write-Host "=========================================================="
Write-Host "  Scoreboard OCR Tracker v2 - Windows Installer"
Write-Host "=========================================================="
Write-Host ""
Write-Host "  Install to: $env:USERPROFILE\ScoreboardOCR"
Write-Host "  Press Enter to start..."
Read-Host

$InstallDir = "$env:USERPROFILE\ScoreboardOCR"

# ==========================================================
# STEP 1 - Python (MUST be first)
# ==========================================================
Write-Host ""
Write-Host "[1/4] Python..."

$Python = $null

# Check for real Python (skip Microsoft Store stub)
$paths = @(
    "$env:LocalAppData\Programs\Python\Python312\python.exe",
    "$env:ProgramFiles\Python312\python.exe",
    "C:\Python312\python.exe"
)
foreach ($p in $paths) {
    if (Test-Path $p) {
        $result = & $p --version 2>&1
        if ($LASTEXITCODE -eq 0) { $Python = $p; break }
    }
}

# Also try PATH - but verify it's not the store stub
if (-not $Python) {
    try {
        $pythonPath = (Get-Command python -ErrorAction Stop).Source
        if ($pythonPath -notlike "*WindowsApps*") {
            $result = & python --version 2>&1
            if ($LASTEXITCODE -eq 0) { $Python = $pythonPath }
        }
    } catch {}
}

if (-not $Python) {
    Write-Host "  Python 3.12 not found. Installing via winget..."
    try {
        winget install Python.Python.3.12 --accept-source-agreements --accept-package-agreements
        Write-Host "  Python installed. Refreshing PATH..."
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        Start-Sleep -Seconds 5
        foreach ($p in $paths) {
            if (Test-Path $p) { $Python = $p; break }
        }
    } catch {
        Write-Host "  winget failed. Downloading Python directly..."
        $PyInstaller = "$env:TEMP\python312.exe"
        Invoke-WebRequest -UseBasicParsing -Uri "https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe" -OutFile $PyInstaller
        Start-Process -FilePath $PyInstaller -ArgumentList "/quiet InstallAllUsers=0 PrependPath=1 Include_test=0" -Wait
        foreach ($p in $paths) {
            if (Test-Path $p) { $Python = $p; break }
        }
    }
}

if (-not $Python -or -not (Test-Path $Python)) {
    Write-Host "  ERROR: Cannot install Python."
    Read-Host
    exit 1
}

Write-Host "  Python: $Python"
& $Python --version
Write-Host "  OK"

# ==========================================================
# STEP 2 - Source code
# ==========================================================
Write-Host ""
Write-Host "[2/4] Source code..."

# Skip download if already extracted properly
if ((Test-Path "$InstallDir\pyproject.toml") -and (Test-Path "$InstallDir\src")) {
    Write-Host "  Already installed, skipping download."
} else {
    if (Test-Path $InstallDir) {
        Remove-Item -Recurse -Force $InstallDir -ErrorAction SilentlyContinue
    }
    Write-Host "  Downloading from GitHub..."
    $ZipPath = "$env:TEMP\sbocr_source.zip"
    $ExtractPath = "$env:TEMP\sbocr_extract"
    if (Test-Path $ExtractPath) { Remove-Item -Recurse -Force $ExtractPath }

    try {
        Invoke-WebRequest -UseBasicParsing -Uri "https://codeload.github.com/yaroslaviyanin-creator/scoreboard-ocr/zip/refs/heads/main" -OutFile $ZipPath
        Write-Host "  Extracting..."
        Expand-Archive -Path $ZipPath -DestinationPath $ExtractPath -Force
        $SourceDir = Get-ChildItem -Path $ExtractPath -Directory | Select-Object -First 1
        New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
        Copy-Item -Recurse -Force "$($SourceDir.FullName)\*" $InstallDir
        Write-Host "  Source installed."
    } catch {
        Write-Host "  ERROR: Download failed. Check internet."
        Read-Host
        exit 1
    }
}
Write-Host "  OK"

# ==========================================================
# STEP 3 - Python packages
# ==========================================================
Write-Host ""
Write-Host "[3/4] Python packages (~1 GB, 5-10 min)..."

Set-Location $InstallDir
if (Test-Path "$InstallDir\.venv") {
    Write-Host "  Removing old venv..."
    Remove-Item -Recurse -Force "$InstallDir\.venv" -ErrorAction SilentlyContinue
}

Write-Host "  Creating virtual environment..."
& $Python -m venv .venv
$VenvPython = "$InstallDir\.venv\Scripts\python.exe"

Write-Host "  Upgrading pip..."
& $VenvPython -m pip install --upgrade pip --quiet 2>&1 | Out-Null

Write-Host "  PyQt6..."
& $VenvPython -m pip install PyQt6 --quiet
Write-Host "  OpenCV + NumPy..."
& $VenvPython -m pip install opencv-python numpy --quiet
Write-Host "  PaddleOCR (AI model, ~1 GB)..."
& $VenvPython -m pip install paddlepaddle paddleocr --quiet
Write-Host "  Tesseract bindings..."
& $VenvPython -m pip install pytesseract platformdirs --quiet
Write-Host "  OK"

# ==========================================================
# STEP 4 - Launcher
# ==========================================================
Write-Host ""
Write-Host "[4/4] Launcher..."

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

Write-Host "  Desktop shortcut: ScoreboardOCR"
Write-Host "  OK"
Write-Host ""
Write-Host "=========================================================="
Write-Host "  INSTALLATION COMPLETE!"
Write-Host "=========================================================="
Write-Host ""
Write-Host "  Launch: ScoreboardOCR on Desktop"
Write-Host "  Or: $InstallDir\run.bat"
Write-Host ""
Read-Host "Press Enter to exit"
