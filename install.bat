@echo off
title Scoreboard OCR Tracker v2 - Installer
setlocal enabledelayedexpansion

echo ==========================================================
echo   Scoreboard OCR Tracker v2 - Windows Installer
echo ==========================================================
echo.
echo   Installing to: %USERPROFILE%\ScoreboardOCR
echo.
echo   Press any key to start...
pause >nul

set "DIR=%USERPROFILE%\ScoreboardOCR"

:: ==========================================================
:: STEP 1: Check Python
:: ==========================================================
echo.
echo [1/4] Checking Python...
set "PYTHON="

:: Try common locations first (skip Microsoft Store stub)
for %%d in (
    "%LocalAppData%\Programs\Python\Python312"
    "%LocalAppData%\Programs\Python\Python311"
    "%ProgramFiles%\Python312"
    "C:\Python312"
) do (
    if exist "%%d\python.exe" (
        "%%d\python.exe" --version >nul 2>&1
        if !errorlevel! equ 0 set "PYTHON=%%d\python.exe"
    )
)

if defined PYTHON goto :python_ok

:: Try PATH but verify it's real
where python >nul 2>&1
if !errorlevel! equ 0 (
    for /f "delims=" %%i in ('where python 2^>nul') do (
        echo %%i | findstr /i "WindowsApps" >nul
        if !errorlevel! neq 0 set "PYTHON=%%i"
    )
)

if defined PYTHON goto :python_ok

:: Install Python via winget if available
echo   Python not found. Trying winget...
where winget >nul 2>&1
if !errorlevel! equ 0 (
    echo   Running: winget install Python.Python.3.12
    winget install Python.Python.3.12 --accept-source-agreements --accept-package-agreements
    for %%d in (
        "%LocalAppData%\Programs\Python\Python312"
        "%ProgramFiles%\Python312"
        "C:\Python312"
    ) do (
        if exist "%%d\python.exe" set "PYTHON=%%d\python.exe"
    )
    if defined PYTHON goto :python_ok
)

:: Download Python directly
echo   Downloading Python 3.12...
powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -UseBasicParsing -Uri 'https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe' -OutFile '$env:TEMP\python312.exe'" 2>nul
if exist "%TEMP%\python312.exe" (
    echo   Installing Python...
    "%TEMP%\python312.exe" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0
    for %%d in (
        "%LocalAppData%\Programs\Python\Python312"
        "%ProgramFiles%\Python312"
        "C:\Python312"
    ) do (
        if exist "%%d\python.exe" set "PYTHON=%%d\python.exe"
    )
)

:python_ok
if not defined PYTHON (
    echo   ERROR: Cannot install Python. Please install manually from https://python.org
    pause
    exit /b 1
)
%PYTHON% --version
set "PYTHON=%PYTHON:\=\\%"
echo   OK: %PYTHON%
echo.

:: ==========================================================
:: STEP 2: Source code
:: ==========================================================
echo [2/4] Source code...

if exist "%DIR%\pyproject.toml" (
    echo   Already downloaded, skipping...
) else (
    if exist "%DIR%" rmdir /s /q "%DIR%" 2>nul
    echo   Downloading from GitHub...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -UseBasicParsing -Uri 'https://codeload.github.com/yaroslaviyanin-creator/scoreboard-ocr/zip/refs/heads/main' -OutFile '$env:TEMP\sbocr.zip'" 2>nul
    if not exist "%TEMP%\sbocr.zip" (
        echo   ERROR: Download failed. Check internet.
        pause
        exit /b 1
    )
    echo   Extracting...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -Path '$env:TEMP\sbocr.zip' -DestinationPath '$env:TEMP\sbocr_extract' -Force" 2>nul
    for /d %%d in ("%TEMP%\sbocr_extract\*") do xcopy /E /I /Y "%%d\*" "%DIR%" >nul
)
echo   OK
echo.

:: ==========================================================
:: STEP 3: Python packages
:: ==========================================================
echo [3/4] Python packages (~1 GB, 5-10 min)...

cd /d "%DIR%"
if exist ".venv" rmdir /s /q ".venv" 2>nul
%PYTHON% -m venv .venv
call .venv\Scripts\activate.bat

echo   Upgrading pip...
python -m pip install --upgrade pip --quiet 2>nul

echo   Installing packages...
python -m pip install PyQt6 opencv-python numpy pytesseract platformdirs --quiet 2>nul
echo   Installing PaddleOCR (AI model, ~1 GB)...
python -m pip install paddlepaddle paddleocr --quiet 2>nul
echo   OK
echo.

:: ==========================================================
:: STEP 4: Launcher
:: ==========================================================
echo [4/4] Creating launcher...

echo @echo off > "%DIR%\run.bat"
echo cd /d "%DIR%" >> "%DIR%\run.bat"
echo call .venv\Scripts\activate.bat >> "%DIR%\run.bat"
echo python -m scoreboard_ocr.app >> "%DIR%\run.bat"
echo if errorlevel 1 pause >> "%DIR%\run.bat"

powershell -NoProfile -ExecutionPolicy Bypass -Command "$w=New-Object -ComObject WScript.Shell; $s=$w.CreateShortcut('%USERPROFILE%\Desktop\ScoreboardOCR.lnk'); $s.TargetPath='%SystemRoot%\System32\cmd.exe'; $s.Arguments='/c \"%DIR%\run.bat\"'; $s.WorkingDirectory='%DIR%'; $ico='%DIR%\assets\icon.ico'; if(Test-Path $ico){$s.IconLocation=$ico}; $s.Save()" 2>nul

echo   OK
echo.
echo ==========================================================
echo   INSTALLATION COMPLETE!
echo ==========================================================
echo   Launch: ScoreboardOCR on Desktop
echo   Or: %DIR%\run.bat
echo.
pause
