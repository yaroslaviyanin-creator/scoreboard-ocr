@echo off
setlocal enabledelayedexpansion
title Scoreboard OCR Tracker — Installation

:: Colors for console output (Windows 10+)
:: ============================================================
echo.
echo  ========================================================
echo    Scoreboard OCR Tracker v2
echo    Windows Installer
echo  ========================================================
echo.
echo  This will install:
echo    - Python 3.12 (if not found)
echo    - Git (if not found)
echo    - All Python packages (PyQt6, PaddleOCR, OpenCV, etc.)
echo    - Tesseract OCR (for Russian text recognition)
echo.
echo  Total size: ~2-3 GB
echo  Time: 5-15 minutes depending on internet speed
echo.
echo  Press any key to continue or Ctrl+C to cancel...
pause >nul
echo.

:: ============================================================
:: Step 1: Python
:: ============================================================
echo  [1/6] Checking Python...
set "PYTHON_EXE="

:: Try common locations
for %%p in (python python3 "C:\Python312\python.exe" "%ProgramFiles%\Python312\python.exe" "%LocalAppData%\Programs\Python\Python312\python.exe") do (
    if not defined PYTHON_EXE (
        %%p --version >nul 2>&1 && set "PYTHON_EXE=%%p"
    )
)

if defined PYTHON_EXE (
    %PYTHON_EXE% --version
    echo         OK - Python found
) else (
    echo         Python not found. Downloading Python 3.12.8...
    echo         This is a ~25 MB download.
    curl -L --progress-bar -o "%TEMP%\python312.exe" "https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe"
    if !errorlevel! neq 0 (
        echo.
        echo  ERROR: Cannot download Python. Check your internet connection.
        echo  Please install Python manually from: https://www.python.org/downloads/
        echo  Then run this installer again.
        echo.
        pause
        exit /b 1
    )
    echo         Installing Python (please wait)...
    "%TEMP%\python312.exe" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0 Include_pip=1
    if !errorlevel! neq 0 (
        echo         Python installer failed. Trying user-level install...
        "%TEMP%\python312.exe" /quiet InstallAllUsers=1 PrependPath=1 Include_test=0 Include_pip=1
    )
    :: Refresh PATH
    for /f "tokens=*" %%i in ('where python 2^>nul') do set "PYTHON_EXE=%%i"
    if not defined PYTHON_EXE (
        set "PYTHON_EXE=%LocalAppData%\Programs\Python\Python312\python.exe"
    )
    echo         Python installed: %PYTHON_EXE%
)
echo.

:: ============================================================
:: Step 2: Git
:: ============================================================
echo  [2/6] Checking Git...
git --version >nul 2>&1
if !errorlevel! neq 0 (
    echo         Git not found. Downloading...
    curl -L --progress-bar -o "%TEMP%\git-installer.exe" "https://github.com/git-for-windows/git/releases/download/v2.47.1.windows.2/Git-2.47.1.2-64-bit.exe"
    if !errorlevel! neq 0 (
        echo  WARNING: Cannot download Git. Trying to continue without it...
        echo  If installation fails, install Git from: https://git-scm.com/download/win
    ) else (
        echo         Installing Git silently...
        "%TEMP%\git-installer.exe" /VERYSILENT /NORESTART /NOCANCEL /SP- /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS
        echo         Git installed. Please restart this script if PATH is not updated.
    )
) else (
    git --version
    echo         OK
)
echo.

:: ============================================================
:: Step 3: Clone repository
:: ============================================================
echo  [3/6] Downloading Scoreboard OCR source code...
set "INSTALL_DIR=%USERPROFILE%\ScoreboardOCR"

if exist "%INSTALL_DIR%\.git" (
    echo         Updating existing installation...
    cd /d "%INSTALL_DIR%"
    git pull 2>nul
    if !errorlevel! neq 0 (
        echo         Pull failed, using existing files...
    ) else (
        echo         Updated to latest version.
    )
) else (
    if exist "%INSTALL_DIR%" (
        echo         Removing old installation folder...
        rmdir /s /q "%INSTALL_DIR%" 2>nul
    )
    echo         Cloning from GitHub...
    git clone --depth 1 https://github.com/yaroslaviyanin-creator/scoreboard-ocr.git "%INSTALL_DIR%"
    if !errorlevel! neq 0 (
        echo.
        echo  ERROR: Cannot clone repository. Download manually:
        echo  https://github.com/yaroslaviyanin-creator/scoreboard-ocr/archive/refs/heads/main.zip
        echo  Extract to: %INSTALL_DIR%
        echo.
        pause
        exit /b 1
    )
)
cd /d "%INSTALL_DIR%"
echo         OK - Source code at: %INSTALL_DIR%
echo.

:: ============================================================
:: Step 4: Python virtual environment
:: ============================================================
echo  [4/6] Creating Python virtual environment...
cd /d "%INSTALL_DIR%"
if exist ".venv" (
    echo         Virtual environment already exists, reusing...
) else (
    %PYTHON_EXE% -m venv .venv
    if !errorlevel! neq 0 (
        echo  ERROR: Cannot create virtual environment.
        pause
        exit /b 1
    )
)
echo         OK
echo.

:: ============================================================
:: Step 5: Install Python packages
:: ============================================================
echo  [5/6] Installing Python packages...
echo         This will download ~1 GB and may take 5-10 minutes...
echo         Progress:
echo.
call .venv\Scripts\activate.bat

:: Upgrade pip first
python -m pip install --upgrade pip --quiet

:: Install core packages one by one with progress
echo   - PyQt6 (GUI framework)...
pip install PyQt6 --quiet
echo   - OpenCV (camera)...
pip install opencv-python --quiet
echo   - NumPy (math)...
pip install numpy --quiet
echo   - PaddlePaddle + PaddleOCR (AI recognition)...
pip install paddlepaddle paddleocr --quiet
echo   - pytesseract (text names)...
pip install pytesseract --quiet
echo   - platformdirs (paths)...
pip install platformdirs --quiet
echo   - pytest (testing)...
pip install pytest --quiet
echo   - pyinstaller (build exe)...
pip install pyinstaller --quiet

echo.
echo         All packages installed.
echo.

:: ============================================================
:: Step 6: Tesseract OCR
:: ============================================================
echo  [6/6] Setting up Tesseract OCR...
set "TESS_DIR=%INSTALL_DIR%\Tesseract-OCR"

if exist "%TESS_DIR%\tesseract.exe" (
    echo         Tesseract already installed.
) else (
    echo         Downloading Tesseract (~50 MB)...
    curl -L --progress-bar -o "%TEMP%\tesseract-installer.exe" "https://github.com/UB-Mannheim/tesseract/releases/download/v5.5.0/tesseract-ocr-w64-setup-5.5.0.20241111.exe"
    if !errorlevel! neq 0 (
        echo         WARNING: Tesseract download failed.
        echo         Russian name recognition will need manual Tesseract install.
        echo         Download from: https://github.com/UB-Mannheim/tesseract/wiki
    ) else (
        echo         Installing Tesseract to project folder...
        "%TEMP%\tesseract-installer.exe" /VERYSILENT /NORESTART /DIR="%TESS_DIR%"
        if exist "%TESS_DIR%\tesseract.exe" (
            echo         OK - Tesseract installed.
        ) else (
            echo         WARNING: Tesseract install may have failed silently.
            echo         Trying to copy from system installation...
            if exist "%ProgramFiles%\Tesseract-OCR\tesseract.exe" (
                xcopy /E /I /Y "%ProgramFiles%\Tesseract-OCR" "%TESS_DIR%" >nul
                echo         OK - Copied from system.
            )
        )
    )
)
echo.

:: ============================================================
:: Create launcher
:: ============================================================
echo  Creating desktop shortcut...

:: Launcher batch file
(
echo @echo off
echo cd /d "%INSTALL_DIR%"
echo call .venv\Scripts\activate.bat
echo start "" pythonw -m scoreboard_ocr.app
) > "%INSTALL_DIR%\ScoreboardOCR.bat"

:: Desktop shortcut via PowerShell
set "DESKTOP=%USERPROFILE%\Desktop"
if not exist "%DESKTOP%" set "DESKTOP=%OneDriveConsumer%\Desktop"
if not exist "%DESKTOP%" set "DESKTOP=%OneDriveCommercial%\Desktop"

if exist "%DESKTOP%" (
    powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%DESKTOP%\ScoreboardOCR.lnk'); $s.TargetPath = '%INSTALL_DIR%\ScoreboardOCR.bat'; $s.WorkingDirectory = '%INSTALL_DIR%'; if (Test-Path '%INSTALL_DIR%\assets\icon.ico') { $s.IconLocation = '%INSTALL_DIR%\assets\icon.ico' }; $s.Save()"
    echo         Desktop shortcut created: ScoreboardOCR
) else (
    echo         WARNING: Desktop not found. Run from: %INSTALL_DIR%\ScoreboardOCR.bat
)
echo.

:: ============================================================
:: Done
:: ============================================================
echo  ========================================================
echo    INSTALLATION COMPLETE!
echo  ========================================================
echo.
echo    Launch: Double-click ScoreboardOCR on your desktop
echo    Or run: %INSTALL_DIR%\ScoreboardOCR.bat
echo.
echo    To update: run this installer again
echo.
pause
