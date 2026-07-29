@echo off
title Scoreboard OCR Tracker — Installation
color 0A

echo.
echo ==========================================================
echo   Scoreboard OCR Tracker v2  -  Windows Installer
echo ==========================================================
echo.
echo   This script will download and install everything needed.
echo   Total download: ~2 GB. Time: 5-15 minutes.
echo.
echo   Press any key to start...
pause >nul
cls

:: ==========================================================
:: WHERE IS PYTHON?
:: ==========================================================
echo [1/5] Looking for Python...
set "PYTHON="

:: Check PATH first
where python >nul 2>&1
if %errorlevel% equ 0 (
    for /f "delims=" %%i in ('where python 2^>nul') do set "PYTHON=%%i"
    goto :found_python
)

:: Check all common locations
for %%d in (
    "%LocalAppData%\Programs\Python\Python313"
    "%LocalAppData%\Programs\Python\Python312"
    "%LocalAppData%\Programs\Python\Python311"
    "%ProgramFiles%\Python313"
    "%ProgramFiles%\Python312"
    "%ProgramFiles%\Python311"
    "C:\Python313"
    "C:\Python312"
    "C:\Python311"
) do (
    if exist "%%d\python.exe" (
        set "PYTHON=%%d\python.exe"
        goto :found_python
    )
)

:: Python not found - ask user
echo.
echo   Python 3.11+ is required but was not found.
echo.
echo   Please install Python from:
echo   https://www.python.org/downloads/
echo.
echo   Make sure to check "Add Python to PATH" during install.
echo   Then run this installer again.
echo.
pause
exit /b 1

:found_python
echo   Found: %PYTHON%
%PYTHON% --version
echo   OK
echo.

:: ==========================================================
:: GET SOURCE CODE
:: ==========================================================
echo [2/5] Getting source code...
set "INSTALL_DIR=%USERPROFILE%\ScoreboardOCR"

:: Check if git is available
where git >nul 2>&1
if %errorlevel% equ 0 (
    echo   Using Git...
    if exist "%INSTALL_DIR%" (
        echo   Updating existing installation...
        cd /d "%INSTALL_DIR%"
        git pull 2>nul
        if %errorlevel% neq 0 (
            echo   Pull failed - will re-clone...
            cd /d "%USERPROFILE%"
            rmdir /s /q "%INSTALL_DIR%" 2>nul
            git clone https://github.com/yaroslaviyanin-creator/scoreboard-ocr.git "%INSTALL_DIR%"
        )
    ) else (
        echo   Cloning from GitHub...
        git clone https://github.com/yaroslaviyanin-creator/scoreboard-ocr.git "%INSTALL_DIR%"
    )
) else (
    echo   Git not found, downloading ZIP...
    if exist "%INSTALL_DIR%" rmdir /s /q "%INSTALL_DIR%" 2>nul
    mkdir "%INSTALL_DIR%" 2>nul
    
    :: Download main branch as ZIP
    powershell -NoProfile -Command "Invoke-WebRequest -Uri 'https://github.com/yaroslaviyanin-creator/scoreboard-ocr/archive/refs/heads/main.zip' -OutFile '%TEMP%\scoreboard-ocr.zip'"
    if %errorlevel% neq 0 (
        echo   ERROR: Cannot download source code.
        echo   Check internet connection.
        pause
        exit /b 1
    )
    echo   Extracting...
    powershell -NoProfile -Command "Expand-Archive -Path '%TEMP%\scoreboard-ocr.zip' -DestinationPath '%TEMP%\scoreboard-ocr' -Force"
    xcopy /E /I /Y "%TEMP%\scoreboard-ocr\scoreboard-ocr-main\*" "%INSTALL_DIR%" >nul
    if %errorlevel% neq 0 (
        echo   ERROR: Extract failed.
        pause
        exit /b 1
    )
)
echo   OK - Source at %INSTALL_DIR%
echo.

:: ==========================================================
:: CREATE VENV AND INSTALL DEPENDENCIES
:: ==========================================================
echo [3/5] Setting up Python environment...
cd /d "%INSTALL_DIR%"

if exist ".venv" (
    echo   Removing old venv...
    rmdir /s /q ".venv" 2>nul
)

echo   Creating virtual environment...
%PYTHON% -m venv .venv
if %errorlevel% neq 0 (
    echo   ERROR: Cannot create venv.
    pause
    exit /b 1
)

echo   Activating venv...
call .venv\Scripts\activate.bat

echo   Upgrading pip...
python -m pip install --upgrade pip --quiet 2>&1

echo.
echo   Installing packages (~1 GB download)...
echo   This will take 5-10 minutes...
echo.

echo     [1/5] PyQt6...
pip install PyQt6 --quiet 2>&1
if %errorlevel% neq 0 (
    echo     WARNING: PyQt6 install failed
)

echo     [2/5] OpenCV + NumPy...
pip install opencv-python numpy --quiet 2>&1
if %errorlevel% neq 0 (
    echo     WARNING: OpenCV install failed
)

echo     [3/5] PaddlePaddle + PaddleOCR (AI models)...
echo           Downloading AI models, this may take a while...
pip install paddlepaddle --quiet 2>&1
pip install paddleocr --quiet 2>&1
if %errorlevel% neq 0 (
    echo     WARNING: PaddleOCR install failed
)

echo     [4/5] Tesseract Python bindings...
pip install pytesseract platformdirs --quiet 2>&1

echo     [5/5] Additional tools...
pip install pytest --quiet 2>&1

echo.
echo   All packages installed.
echo.

:: ==========================================================
:: TESSERACT OCR
:: ==========================================================
echo [4/5] Setting up Tesseract OCR...
set "TESS_DIR=%INSTALL_DIR%\Tesseract-OCR"

if exist "%TESS_DIR%\tesseract.exe" (
    echo   Already installed.
) else (
    echo   Trying to find Tesseract on system...
    
    :: Check common Windows install locations
    set "TESS_FOUND="
    for %%d in (
        "%ProgramFiles%\Tesseract-OCR"
        "%ProgramFiles(x86)%\Tesseract-OCR"
        "%LocalAppData%\Tesseract-OCR"
    ) do (
        if exist "%%d\tesseract.exe" (
            echo   Found at %%d
            echo   Copying to project folder...
            xcopy /E /I /Y "%%d" "%TESS_DIR%" >nul
            set "TESS_FOUND=1"
        )
    )
    
    if not defined TESS_FOUND (
        echo.
        echo   Tesseract OCR not found on this PC.
        echo   Name mode (Russian text) will use fallback.
        echo.
        echo   To install Tesseract later:
        echo   https://github.com/UB-Mannheim/tesseract/wiki
        echo   Install to: %TESS_DIR%
        echo.
    )
)
echo   OK
echo.

:: ==========================================================
:: CREATE SHORTCUT
:: ==========================================================
echo [5/5] Creating shortcut...

:: Create launcher script
(
echo @echo off
echo title Scoreboard OCR Tracker
echo cd /d "%INSTALL_DIR%"
echo call .venv\Scripts\activate.bat
echo python -m scoreboard_ocr.app
echo if errorlevel 1 pause
) > "%INSTALL_DIR%\run_scoreboard.bat"

:: Desktop shortcut
set "DESKTOP=%USERPROFILE%\Desktop"
if exist "%USERPROFILE%\OneDrive\Desktop" set "DESKTOP=%USERPROFILE%\OneDrive\Desktop"

if exist "%DESKTOP%" (
    powershell -NoProfile -Command ^
        "$ws = New-Object -ComObject WScript.Shell; ^
         $sc = $ws.CreateShortcut('%DESKTOP%\ScoreboardOCR.lnk'); ^
         $sc.TargetPath = '%SystemRoot%\System32\cmd.exe'; ^
         $sc.Arguments = '/c \"%INSTALL_DIR%\run_scoreboard.bat\"'; ^
         $sc.WorkingDirectory = '%INSTALL_DIR%'; ^
         $sc.Description = 'Scoreboard OCR Tracker v2'; ^
         if (Test-Path '%INSTALL_DIR%\assets\icon.ico') { $sc.IconLocation = '%INSTALL_DIR%\assets\icon.ico' }; ^
         $sc.Save()"
    echo   Desktop shortcut created: ScoreboardOCR
) else (
    echo   Desktop not found. Run from: %INSTALL_DIR%\run_scoreboard.bat
)
echo   OK
echo.

:: ==========================================================
:: DONE
:: ==========================================================
echo ==========================================================
echo   INSTALLATION COMPLETE!
echo ==========================================================
echo.
echo   To launch: Double-click ScoreboardOCR on Desktop
echo   Or run: %INSTALL_DIR%\run_scoreboard.bat
echo.
echo   To update: run this installer again.
echo.
echo   Press any key to exit...
pause >nul
