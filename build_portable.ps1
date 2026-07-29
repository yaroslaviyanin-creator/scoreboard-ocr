# Scoreboard OCR Tracker v2 - Win64 Portable Bundle Builder
# Run on macOS with Python 3.12 to create a Windows self-extracting installer.
# Requires: pyinstaller, all deps installed in .venv

$ErrorActionPreference = "Stop"
Write-Host "Building Scoreboard OCR Windows portable bundle..." -ForegroundColor Cyan

# 1. Create a self-extracting ZIP with all project files
$ProjectRoot = "$PSScriptRoot"
$OutputDir = "$ProjectRoot\dist\windows-portable"
$BundleName = "ScoreboardOCR-Win64"

Write-Host "  Cleaning output..."
if (Test-Path $OutputDir) { Remove-Item -Recurse -Force $OutputDir }
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

# 2. We need a minimal embedded Python for Windows.
# Download python-embed-amd64 from python.org
$PythonEmbedURL = "https://www.python.org/ftp/python/3.12.8/python-3.12.8-embed-amd64.zip"
$PythonEmbedZip = "$env:TEMP\python-embed.zip"
$PythonEmbedDir = "$OutputDir\python"

Write-Host "  Downloading embedded Python 3.12..."
Invoke-WebRequest -UseBasicParsing -Uri $PythonEmbedURL -OutFile $PythonEmbedZip
Expand-Archive -Path $PythonEmbedZip -DestinationPath $PythonEmbedDir -Force

# Enable pip in embedded Python
$PythonPth = "$PythonEmbedDir\python312._pth"
(Get-Content $PythonPth) -replace '#import site', 'import site' | Set-Content $PythonPth

# Download get-pip.py
Write-Host "  Installing pip..."
$GetPip = "$env:TEMP\get-pip.py"
Invoke-WebRequest -UseBasicParsing -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile $GetPip
& "$PythonEmbedDir\python.exe" $GetPip --quiet

# 3. Install all dependencies into embedded Python
Write-Host "  Installing dependencies (this will take a while)..."
$PipExe = "$PythonEmbedDir\Scripts\pip.exe"

& $PipExe install PyQt6 --quiet
Write-Host "    PyQt6 OK"
& $PipExe install opencv-python numpy --quiet  
Write-Host "    OpenCV OK"
& $PipExe install paddlepaddle paddleocr --quiet
Write-Host "    PaddleOCR OK"
& $PipExe install pytesseract platformdirs --quiet
Write-Host "    Tesseract OK"

# 4. Copy project source code
Write-Host "  Copying source code..."
Copy-Item -Recurse "$ProjectRoot\src\scoreboard_ocr" "$OutputDir\scoreboard_ocr"
Copy-Item -Recurse "$ProjectRoot\assets" "$OutputDir\assets"
Copy-Item "$ProjectRoot\pyproject.toml" "$OutputDir"
Copy-Item "$ProjectRoot\setup.py" "$OutputDir"

# 5. Create launcher
Write-Host "  Creating launcher..."
$Launcher = @"
@echo off
cd /d "%~dp0"
python\python.exe -m scoreboard_ocr.app
if errorlevel 1 pause
"@
$Launcher | Out-File -FilePath "$OutputDir\run.bat" -Encoding ASCII

# 6. Create self-extracting EXE using 7-Zip or IExpress
# For simplicity, we'll create a batch-based installer that users just extract
Write-Host "  Creating archive..."
$ArchivePath = "$ProjectRoot\dist\$BundleName.zip"
if (Test-Path $ArchivePath) { Remove-Item $ArchivePath }
Compress-Archive -Path "$OutputDir\*" -DestinationPath $ArchivePath

Write-Host ""
Write-Host "Build complete: $ArchivePath" -ForegroundColor Green
Write-Host "Size: $((Get-Item $ArchivePath).Length / 1MB) MB"
Write-Host ""
Write-Host "To install on Windows:"
Write-Host "  1. Copy $BundleName.zip to Windows PC"
Write-Host "  2. Extract anywhere (e.g. C:\ScoreboardOCR)"
Write-Host "  3. Double-click run.bat"
