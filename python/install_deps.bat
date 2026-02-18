@echo off
echo ============================================
echo Virtual Design — Silk Screen Studio
echo Python Dependency Installer
echo ============================================
echo.

REM التحقق من وجود Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found!
    echo Please download Python 3.8+ from: https://python.org
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

echo [OK] Python found:
python --version
echo.

REM التحقق من pip
python -m pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] pip not found. Reinstall Python with pip included.
    pause
    exit /b 1
)

echo [OK] pip found.
echo.

REM ترقية pip
echo Upgrading pip...
python -m pip install --upgrade pip --quiet

REM تثبيت المكتبات
echo Installing dependencies...
python -m pip install -r requirements.txt

if %errorlevel% equ 0 (
    echo.
    echo ============================================
    echo [SUCCESS] All dependencies installed!
    echo You can now use Virtual Design Silk Screen Studio.
    echo ============================================
) else (
    echo.
    echo [ERROR] Some dependencies failed to install.
    echo Try running as Administrator or check your internet connection.
)

echo.
pause
