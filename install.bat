@echo off
title Scoreboard OCR Tracker — Installation
setlocal enabledelayedexpansion

echo ==========================================================
echo   Scoreboard OCR Tracker v2  -  Windows Installer
echo ==========================================================
echo.

:: Force the window to stay open no matter what
if not defined STAY_OPEN (
    set "STAY_OPEN=1"
    start "" /WAIT cmd /c "%~f0" %*
    exit /b
)

echo   This script will automatically install everything.
echo   Total: ~2 GB download, 5-15 minutes.
echo.
echo   Press any key to begin...
pause >nul
echo.

:: ==========================================================
:: STEP 1 — PYTHON
:: ==========================================================
echo [1/4] Python...
set "PY="

:: Try PATH
python --version >nul 2>&1 && set "PY=python" && goto :py_ok
py -3 --version >nul 2>&1 && set "PY=py -3" && goto :py_ok

:: Try known folders
for %%d in (
    "%LocalAppData%\Programs\Python\Python312"
    "%LocalAppData%\Programs\Python\Python311"
    "%ProgramFiles%\Python312"
    "C:\Python312"
) do (
    if exist "%%d\python.exe" (set "PY=%%d\python.exe" && goto :py_ok)
)

echo   Python not found, downloading...
echo   This window will stay open during download.
powershell -NoProfile -Command ^
  "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12;^
   Write-Host '  Downloading Python 3.12...';^
   Invoke-WebRequest -UseBasicParsing -Uri 'https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe' -OutFile '$env:TEMP\py312.exe'"
if errorlevel 1 goto :die

echo   Installing Python silently...
"%TEMP%\py312.exe" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0 >nul 2>&1
set "PY=%LocalAppData%\Programs\Python\Python312\python.exe"
if not exist "!PY!" set "PY=%ProgramFiles%\Python312\python.exe"
echo   Python installed.

:py_ok
!PY! --version
if errorlevel 1 goto :die
echo   OK
echo.

:: ==========================================================
:: STEP 2 — SOURCE CODE
:: ==========================================================
echo [2/4] Source code...
set "DIR=%USERPROFILE%\ScoreboardOCR"
if exist "%DIR%" rmdir /s /q "%DIR%" 2>nul

:: Download as ZIP via PowerShell (works on any Windows 10+)
powershell -NoProfile -Command ^
  "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12;^
   Write-Host '  Downloading...';^
   Invoke-WebRequest -UseBasicParsing -Uri 'https://github.com/yaroslaviyanin-creator/scoreboard-ocr/archive/refs/heads/main.zip' -OutFile '$env:TEMP\sbocr.zip';^
   Write-Host '  Extracting...';^
   Expand-Archive -Path '$env:TEMP\sbocr.zip' -DestinationPath '$env:TEMP\sbocr' -Force;^
   Write-Host '  Copying files...'"
if errorlevel 1 goto :die

xcopy /E /I /Y "%TEMP%\sbocr\scoreboard-ocr-main\*" "%DIR%" >nul
if not exist "%DIR%\install.bat" goto :die
echo   OK
echo.

:: ==========================================================
:: STEP 3 — PYTHON PACKAGES
:: ==========================================================
echo [3/4] Python packages...
cd /d "%DIR%"
if exist ".venv" rmdir /s /q ".venv" 2>nul
!PY! -m venv .venv >nul 2>&1
call .venv\Scripts\activate.bat >nul 2>&1

python -m pip install --upgrade pip --quiet 2>nul

echo   PyQt6...
pip install PyQt6 --quiet 2>nul || echo   WARNING: PyQt6 failed
echo   OpenCV + NumPy...
pip install opencv-python numpy --quiet 2>nul || echo   WARNING: OpenCV failed
echo   PaddleOCR (AI model, ~1 GB) — please wait...
pip install paddlepaddle paddleocr --quiet 2>nul || echo   WARNING: PaddleOCR failed
echo   Tesseract + platformdirs...
pip install pytesseract platformdirs --quiet 2>nul || echo   WARNING: pytesseract failed
echo   OK
echo.

:: ==========================================================
:: STEP 4 — LAUNCHER + SHORTCUT
:: ==========================================================
echo [4/4] Launcher...

(
echo @echo off
echo cd /d "%DIR%"
echo call .venv\Scripts\activate.bat
echo python -m scoreboard_ocr.app
echo if errorlevel 1 pause
) > "%DIR%\run.bat"

set "DSK=%USERPROFILE%\Desktop"
if exist "%USERPROFILE%\OneDrive\Desktop" set "DSK=%USERPROFILE%\OneDrive\Desktop"
powershell -NoProfile -Command ^
  "$w=New-Object -ComObject WScript.Shell;^
   $s=$w.CreateShortcut('%DSK%\ScoreboardOCR.lnk');^
   $s.TargetPath='%SystemRoot%\System32\cmd.exe';^
   $s.Arguments='/c \"\"%DIR%\run.bat\"\"';^
   $s.WorkingDirectory='%DIR%';^
   $ico='%DIR%\assets\icon.ico';^
   if(Test-Path $ico){$s.IconLocation=$ico};^
   $s.Save()"
echo   OK
echo.

:: ==========================================================
echo ==========================================================
echo   DONE! Launch from Desktop: ScoreboardOCR
echo   Or run: %DIR%\run.bat
echo ==========================================================
echo.
pause
exit /b 0

:die
echo.
echo ==========================================================
echo   ERROR — Installation failed.
echo   Check your internet connection and try again.
echo ==========================================================
echo.
pause
exit /b 1
