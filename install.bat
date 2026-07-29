@echo off
setlocal enabledelayedexpansion
title Scoreboard OCR Tracker — Installer

echo ============================================
echo   Scoreboard OCR Tracker v2 — Installer
echo ============================================
echo.

:: 1. Check for Python
echo [1/5] Checking Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python not found. Downloading Python 3.12...
    curl -L -o "%TEMP%\python-installer.exe" "https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe"
    echo Installing Python (this will take a minute)...
    "%TEMP%\python-installer.exe" /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
    if %errorlevel% neq 0 (
        echo ERROR: Failed to install Python. Please install manually from https://python.org
        pause
        exit /b 1
    )
    echo Python installed. Restarting script with new PATH...
    set "PATH=%ProgramFiles%\Python312;%ProgramFiles%\Python312\Scripts;%PATH%"
)
python --version
echo   OK
echo.

:: 2. Clone repository
echo [2/5] Cloning repository...
set "INSTALL_DIR=%USERPROFILE%\ScoreboardOCR"
if exist "%INSTALL_DIR%" (
    echo Repository already exists at %INSTALL_DIR%
    cd /d "%INSTALL_DIR%"
    git pull
) else (
    git clone https://github.com/yaroslaviyanin-creator/scoreboard-ocr.git "%INSTALL_DIR%"
    if %errorlevel% neq 0 (
        echo ERROR: Failed to clone. Check your internet connection.
        pause
        exit /b 1
    )
    cd /d "%INSTALL_DIR%"
)
echo   OK
echo.

:: 3. Create virtual environment
echo [3/5] Setting up Python environment...
cd /d "%INSTALL_DIR%"
if not exist ".venv" (
    python -m venv .venv
)
call .venv\Scripts\activate.bat
echo   OK
echo.

:: 4. Install dependencies
echo [4/5] Installing dependencies (this may take 5-10 minutes)...
python -m pip install --upgrade pip >nul 2>&1
pip install -e ".[dev]" 2>&1
if %errorlevel% neq 0 (
    echo WARNING: Some packages failed. Trying basic install...
    pip install PyQt6 opencv-python numpy pytesseract paddlepaddle paddleocr platformdirs
)
echo   OK
echo.

:: 5. Download Tesseract (for Name mode with Russian)
echo [5/5] Setting up Tesseract...
set "TESS_DIR=%INSTALL_DIR%\Tesseract-OCR"
if not exist "%TESS_DIR%\tesseract.exe" (
    echo Downloading Tesseract OCR...
    curl -L -o "%TEMP%\tesseract.zip" "https://github.com/UB-Mannheim/tesseract/releases/download/v5.5.0/tesseract-ocr-w64-setup-5.5.0.20241111.exe"
    if %errorlevel% neq 0 (
        echo WARNING: Tesseract download failed. Name mode will use fallback.
        echo You can install Tesseract later from: https://github.com/UB-Mannheim/tesseract/wiki
    ) else (
        echo Installing Tesseract silently...
        "%TEMP%\tesseract.zip" /SILENT /DIR="%TESS_DIR%"
        echo Tesseract installed to %TESS_DIR%
    )
) else (
    echo Tesseract already installed.
)
echo   OK
echo.

:: Create launcher
echo @echo off > "%INSTALL_DIR%\ScoreboardOCR.bat"
echo cd /d "%INSTALL_DIR%" >> "%INSTALL_DIR%\ScoreboardOCR.bat"
echo call .venv\Scripts\activate.bat >> "%INSTALL_DIR%\ScoreboardOCR.bat"
echo start "" pythonw -m scoreboard_ocr.app >> "%INSTALL_DIR%\ScoreboardOCR.bat"

:: Create desktop shortcut
set "DESKTOP=%USERPROFILE%\Desktop"
if exist "%DESKTOP%" (
    powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%DESKTOP%\ScoreboardOCR.lnk'); $s.TargetPath = '%INSTALL_DIR%\ScoreboardOCR.bat'; $s.WorkingDirectory = '%INSTALL_DIR%'; $s.IconLocation = '%INSTALL_DIR%\assets\icon.ico'; $s.Save()" >nul 2>&1
)

echo.
echo ============================================
echo   Installation complete!
echo ============================================
echo.
echo   Launch from desktop shortcut: ScoreboardOCR
echo   Or run: %INSTALL_DIR%\ScoreboardOCR.bat
echo.
pause
